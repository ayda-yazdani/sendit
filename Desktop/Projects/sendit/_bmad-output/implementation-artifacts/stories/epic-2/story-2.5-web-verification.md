# Story 2.5: Web Verification for Venues & Events

## Description

As the system,
I want to verify real venues and events against external databases (Google Places),
So that suggestions include confirmed locations with accurate addresses, ratings, and booking links.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B (backend/Edge Functions)
- **FRs Covered:** FR16
- **Depends On:** Story 2.2 (extraction), Story 2.4 (classification — must know if content is `real_event` or `real_venue`)

## Acceptance Criteria

**Given** a reel is classified as `real_event` or `real_venue`
**When** the extraction_data contains a `venue_name` (non-null)
**Then** Google Places API (Text Search) is called with the venue name and location
**And** the top result's verified data is appended to `extraction_data` under a `verified` key
**And** the verified data includes: `place_id`, `formatted_address`, `rating`, `opening_hours`, `website`, `maps_url`

**Given** a reel is classified as `real_event` and has a venue name
**When** Google Places returns a match
**Then** a Google Maps URL is generated: `https://www.google.com/maps/place/?q=place_id:PLACE_ID`
**And** the `verified.maps_url` field is populated for use in the extraction card UI

**Given** a reel is classified as `vibe_inspiration`, `recipe_food`, or `humour_identity`
**When** the verification step runs
**Then** Google Places API is NOT called (skip verification for non-venue content)
**And** no additional latency is added

**Given** the extraction_data has no `venue_name` or `venue_name` is null
**When** the verification step runs
**Then** Google Places API is NOT called
**And** `extraction_data.verified` remains absent

**Given** Google Places API returns no results for the venue name
**When** the search fails to match
**Then** `extraction_data.verified` is set to `{ "status": "not_found" }`
**And** extraction still completes successfully (no error thrown)

**Given** Google Places API is unavailable or rate-limited
**When** the API call fails
**Then** extraction still completes without verified data (graceful degradation)
**And** a warning is logged

## Technical Context

### Relevant Schema

The `verified` object is stored inside the existing `extraction_data` jsonb column:

```json
{
  "venue_name": "Peckham Audio",
  "location": "Peckham, London",
  "price": "£12",
  "date": "2026-04-05",
  "type": "real_event",
  ...
  "verified": {
    "status": "found",
    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
    "formatted_address": "133 Rye Ln, London SE15 4ST, UK",
    "rating": 4.3,
    "total_ratings": 287,
    "opening_hours": ["Mon-Thu: Closed", "Fri: 22:00-04:00", "Sat: 22:00-06:00", "Sun: Closed"],
    "website": "https://www.peckhamaudio.com",
    "phone": "+44 20 7635 0808",
    "maps_url": "https://www.google.com/maps/place/?q=place_id:ChIJN1t_tDeuEmsRUsoyG83frY4",
    "price_level": 2
  }
}
```

### Architecture References

- **Edge Function:** `supabase/functions/extract/index.ts` — add verification as the final step after extraction + classification
- **Google Places API:** Uses the Places API (New) Text Search endpoint
- **API endpoint:** `https://places.googleapis.com/v1/places:searchText`
- **Supabase secret:** `GOOGLE_PLACES_API_KEY` — must be set before deployment

### Dependencies

- Story 2.2 (extraction) and Story 2.4 (classification) must be complete
- Classification must run before verification (we only verify `real_event` and `real_venue`)
- `GOOGLE_PLACES_API_KEY` must be set as a Supabase secret
- Google Cloud project must have Places API (New) enabled

## Implementation Notes

### 1. Google Places API Setup

The Places API (New) uses a different authentication model than the legacy Places API. It uses API key + field masks.

```bash
# Set the secret
supabase secrets set GOOGLE_PLACES_API_KEY=AIza... --project-ref ubhbeqnagxbuoikzftht
```

### 2. Venue Verification Function

Add to `supabase/functions/extract/index.ts`:

```typescript
interface VerifiedVenueData {
  status: 'found' | 'not_found';
  place_id?: string;
  formatted_address?: string;
  rating?: number;
  total_ratings?: number;
  opening_hours?: string[];
  website?: string;
  phone?: string;
  maps_url?: string;
  price_level?: number;
}

async function verifyVenueWithGooglePlaces(
  venueName: string,
  location: string | null
): Promise<VerifiedVenueData> {
  const apiKey = Deno.env.get('GOOGLE_PLACES_API_KEY');
  if (!apiKey) {
    console.warn('GOOGLE_PLACES_API_KEY not set, skipping verification');
    return { status: 'not_found' };
  }

  try {
    // Construct search query: venue name + location for better results
    const searchQuery = location ? `${venueName} ${location}` : venueName;

    const response = await fetch(
      'https://places.googleapis.com/v1/places:searchText',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': apiKey,
          'X-Goog-FieldMask': [
            'places.id',
            'places.displayName',
            'places.formattedAddress',
            'places.rating',
            'places.userRatingCount',
            'places.regularOpeningHours',
            'places.websiteUri',
            'places.nationalPhoneNumber',
            'places.priceLevel',
            'places.googleMapsUri',
          ].join(','),
        },
        body: JSON.stringify({
          textQuery: searchQuery,
          maxResultCount: 1,
        }),
      }
    );

    if (!response.ok) {
      console.warn(`Google Places API error: ${response.status} ${response.statusText}`);
      return { status: 'not_found' };
    }

    const data = await response.json();

    if (!data.places || data.places.length === 0) {
      return { status: 'not_found' };
    }

    const place = data.places[0];

    // Format opening hours into readable strings
    const openingHours: string[] = [];
    if (place.regularOpeningHours?.weekdayDescriptions) {
      openingHours.push(...place.regularOpeningHours.weekdayDescriptions);
    }

    return {
      status: 'found',
      place_id: place.id,
      formatted_address: place.formattedAddress,
      rating: place.rating,
      total_ratings: place.userRatingCount,
      opening_hours: openingHours.length > 0 ? openingHours : undefined,
      website: place.websiteUri,
      phone: place.nationalPhoneNumber,
      maps_url: place.googleMapsUri || `https://www.google.com/maps/place/?q=place_id:${place.id}`,
      price_level: place.priceLevel ? parsePriceLevel(place.priceLevel) : undefined,
    };
  } catch (err) {
    console.warn('Google Places verification failed:', err);
    return { status: 'not_found' };
  }
}

function parsePriceLevel(level: string): number {
  // Google Places API (New) returns price level as a string enum
  const levels: Record<string, number> = {
    PRICE_LEVEL_FREE: 0,
    PRICE_LEVEL_INEXPENSIVE: 1,
    PRICE_LEVEL_MODERATE: 2,
    PRICE_LEVEL_EXPENSIVE: 3,
    PRICE_LEVEL_VERY_EXPENSIVE: 4,
  };
  return levels[level] ?? 2;
}
```

### 3. Integration into Extract Pipeline

Add verification as the final step in the `extract` Edge Function, after extraction and classification:

```typescript
// Inside the main handler, after classification:

// Verify venue if classification warrants it
const shouldVerify =
  classification === 'real_event' || classification === 'real_venue';
const hasVenue = extractionData.venue_name && extractionData.venue_name !== null;

if (shouldVerify && hasVenue) {
  const verified = await verifyVenueWithGooglePlaces(
    extractionData.venue_name as string,
    extractionData.location as string | null
  );
  extractionData.verified = verified;

  // If Google Places found a website and we don't have a booking_url, use the website
  if (verified.status === 'found' && !extractionData.booking_url && verified.website) {
    extractionData.booking_url = verified.website;
  }

  // If Google Places found an address and our location is vague, upgrade it
  if (verified.status === 'found' && verified.formatted_address) {
    extractionData.verified_address = verified.formatted_address;
  }
}

// Update reel row with all data
await supabaseAdmin
  .from('reels')
  .update({
    extraction_data: extractionData,
    classification: classification,
  })
  .eq('id', reel_id);
```

### 4. Latency Considerations

Google Places Text Search typically responds in 200-400ms. Since this only runs for `real_event` and `real_venue` classifications (roughly 30-40% of content), the average latency impact is low.

Updated latency budget for the full pipeline:

| Step | Latency | Conditional |
|------|---------|-------------|
| YouTube Data API v3 | ~300ms | Always (YouTube) |
| Transcript + Vision (parallel) | ~1000ms | Always (YouTube) |
| Claude extraction | ~1200ms | Always |
| Claude classification | ~300ms | Always |
| Google Places verification | ~350ms | Only for real_event/real_venue |
| Supabase update | ~100ms | Always |
| **Total (venue content)** | **~3250ms** | Tight on NFR1 |
| **Total (non-venue content)** | **~2900ms** | Within NFR1 |

If the 3-second budget is too tight for venue content, run Google Places in parallel with classification (both depend on extraction_data, not on each other). This requires speculative execution — verify even before knowing the classification, then discard the result if classification is not `real_event`/`real_venue`.

```typescript
// Parallel: classify + verify simultaneously
const [classification, verifiedData] = await Promise.all([
  classifyWithClaude(extractionData),
  extractionData.venue_name
    ? verifyVenueWithGooglePlaces(
        extractionData.venue_name as string,
        extractionData.location as string | null
      )
    : Promise.resolve(null),
]);

// Only attach verified data if classification warrants it
if (
  verifiedData &&
  verifiedData.status === 'found' &&
  (classification === 'real_event' || classification === 'real_venue')
) {
  extractionData.verified = verifiedData;
}
```

This saves ~350ms for venue content at the cost of occasional wasted Google Places API calls for non-venue content that happens to mention a place name.

### 5. Event-Specific Verification (Stretch)

For `real_event` classification, if a booking URL is not found via Google Places, attempt to construct a search URL for event discovery platforms:

```typescript
function generateEventSearchUrls(venueName: string, date: string | null): Record<string, string> {
  const encodedVenue = encodeURIComponent(venueName);
  const urls: Record<string, string> = {
    resident_advisor: `https://ra.co/search/?query=${encodedVenue}`,
    eventbrite: `https://www.eventbrite.com/d/united-kingdom/events/?q=${encodedVenue}`,
  };
  return urls;
}
```

Note: Full scraping of RA or Eventbrite is out of scope for the hackathon. Providing search URLs is a practical alternative that still adds value to the extraction card.

## Files to Create/Modify

### Modify

| File | Change |
|------|--------|
| `supabase/functions/extract/index.ts` | Add `verifyVenueWithGooglePlaces()` function, integrate verification after classification, parallel execution optimization |

### No New Files

Verification is integrated into the existing `extract` Edge Function. No separate Edge Function needed.

## Testing Guidance

### Test Cases

1. **Known venue (real_event):** Submit a YouTube Shorts URL about a specific club night at Peckham Audio. Verify `extraction_data.verified.status` is `"found"` and `formatted_address` is populated.

2. **Known restaurant (real_venue):** Submit a reel reviewing a well-known restaurant (e.g., "Dishoom Shoreditch"). Verify Google Places returns the correct address and rating.

3. **Unknown venue:** Submit a reel mentioning a made-up or very obscure venue name. Verify `verified.status` is `"not_found"` and extraction still completes.

4. **Non-venue content (vibe_inspiration):** Submit an aesthetic compilation reel. Verify Google Places API is NOT called (check logs or absence of `verified` key).

5. **Missing venue name:** Submit a reel where extraction produces `venue_name: null`. Verify verification is skipped.

6. **API key missing:** Temporarily remove `GOOGLE_PLACES_API_KEY`. Verify extraction still completes (graceful degradation).

### Verification Query

```sql
SELECT
  url,
  classification,
  extraction_data->>'venue_name' as venue,
  extraction_data->'verified'->>'status' as verified_status,
  extraction_data->'verified'->>'formatted_address' as address,
  extraction_data->'verified'->>'rating' as rating,
  extraction_data->'verified'->>'maps_url' as maps_url
FROM reels
WHERE classification IN ('real_event', 'real_venue')
ORDER BY created_at DESC
LIMIT 10;
```

### Local Testing

```bash
supabase functions serve extract --env-file .env.local

# Test with a venue URL
curl -X POST http://localhost:54321/functions/v1/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"url": "https://youtube.com/shorts/VENUE_VIDEO_ID", "reel_id": "test-uuid"}'

# Check the response includes verified data
```

## Definition of Done

- [ ] `verifyVenueWithGooglePlaces()` function implemented in extract Edge Function
- [ ] Google Places API (New) Text Search integration working with correct field masks
- [ ] Verification only runs for `real_event` and `real_venue` classifications
- [ ] Verification only runs when `venue_name` is non-null
- [ ] `extraction_data.verified` populated with place_id, formatted_address, rating, opening_hours, website, maps_url
- [ ] `extraction_data.verified.status` is `"found"` or `"not_found"`
- [ ] Booking URL auto-populated from Google Places website if not found in extraction
- [ ] Graceful degradation: extraction completes without verified data on API failure
- [ ] `GOOGLE_PLACES_API_KEY` set as Supabase secret
- [ ] Parallel execution implemented (classification + verification run simultaneously)
- [ ] Tested with at least 2 known venues (verified found) and 1 non-venue reel (verification skipped)
- [ ] Edge Function re-deployed with verification integrated
