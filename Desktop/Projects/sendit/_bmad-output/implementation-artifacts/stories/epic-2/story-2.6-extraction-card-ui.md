# Story 2.6: Extraction Card UI

## Description

As a board member,
I want to see a rich extraction card for each shared URL,
So that I can instantly see what the content is about without watching the video.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/ai-extraction`
- **Assignee:** Person C (client/UI/prompts)
- **FRs Covered:** FR18, FR19
- **Depends On:** Story 2.1 (reel creation), Story 2.2 (extraction_data), Story 2.4 (classification)

## Acceptance Criteria

**Given** a reel has `extraction_data` and `classification` populated
**When** it is displayed on the board detail screen
**Then** an extraction card component renders showing:
  - Platform icon (YouTube/Instagram/TikTok/X) in the top-left corner
  - Classification badge (color-coded) in the top-right corner
  - Thumbnail image (if available)
  - Title (1-2 lines, truncated)
  - Venue name and location (if applicable)
  - Price tag (if available)
  - Date (formatted, if available)
  - Vibe tags (pill-shaped tags)
  - Creator handle
  - Booking link / "Tickets" button (if available)

**Given** a reel is classified as `real_event`
**When** the extraction card renders
**Then** a prominent "Tickets" or "Book" button is shown if `booking_url` exists
**And** the date is displayed with visual emphasis (bold, highlighted)
**And** if `verified` data exists, a green checkmark icon appears next to the venue name
**And** the card border/accent uses the `real_event` color (#FF6B35, orange)

**Given** a reel is classified as `real_venue`
**When** the extraction card renders
**Then** a "View on Maps" link is shown if `verified.maps_url` exists
**And** rating stars are displayed if `verified.rating` exists
**And** the card border/accent uses the `real_venue` color (#4ECDC4, teal)

**Given** a reel is classified as `vibe_inspiration`
**When** the extraction card renders
**Then** the thumbnail is displayed larger (hero image style)
**And** vibe tags are prominently displayed
**And** the card border/accent uses the `vibe_inspiration` color (#A78BFA, purple)

**Given** a reel is classified as `recipe_food`
**When** the extraction card renders
**Then** the card emphasises the activity (recipe name) and thumbnail
**And** the card border/accent uses the `recipe_food` color (#34D399, green)

**Given** a reel is classified as `humour_identity`
**When** the extraction card renders
**Then** the card shows a compact layout — title, thumbnail, creator, hashtags
**And** the card border/accent uses the `humour_identity` color (#F472B6, pink)

**Given** a reel has `extraction_data` that is null or contains an error
**When** the card renders
**Then** a minimal fallback card is shown with just the URL, platform icon, and "Extracting..." or "Extraction failed" status

**Given** the user taps the booking URL / tickets button
**When** the link is opened
**Then** it opens in the device's default browser via `Linking.openURL()`

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK,
  added_by uuid FK,
  url text,
  platform text,
  extraction_data jsonb,    -- All the data that drives the card
  classification text,      -- Determines card visual treatment
  created_at timestamptz
)
```

### extraction_data Fields Used by the Card

```typescript
interface ExtractionData {
  venue_name: string | null;
  location: string | null;
  price: string | null;
  date: string | null;
  vibe: string | null;           // Comma-separated: "underground, warehouse"
  activity: string | null;
  mood: string | null;
  hashtags: string[] | null;
  booking_url: string | null;
  transcript_summary: string | null;
  creator: string | null;
  title: string | null;
  thumbnail_url: string | null;
  visual_context: string | null;
  verified?: {
    status: 'found' | 'not_found';
    formatted_address?: string;
    rating?: number;
    total_ratings?: number;
    website?: string;
    maps_url?: string;
    opening_hours?: string[];
  };
  platform_metadata?: {
    channel?: string;
    duration?: string;
    view_count?: string;
  };
}
```

### Architecture References

- **Components folder:** `components/extraction/` — all extraction card components live here
- **Classification constants:** `lib/ai/classification.ts` — provides `CLASSIFICATION_LABELS` and `CLASSIFICATION_COLORS` (created in Story 2.4)
- **Platform icons:** `lib/utils/platform-icons.ts` (created in Story 2.1)
- **Board detail screen:** `app/(tabs)/board/[id].tsx` — renders a `FlatList` of reels, each using the extraction card

### Dependencies

- Story 2.1 (reel creation and platform detection)
- Story 2.4 (classification types, labels, colors)
- Reels must have `extraction_data` and `classification` populated (from Stories 2.2-2.5)

## Implementation Notes

### 1. Component Architecture

Create a modular extraction card with sub-components:

```
components/
  extraction/
    ExtractionCard.tsx          # Main card container — routes to correct layout
    ExtractionCardSkeleton.tsx  # Loading skeleton while extraction is in progress
    ExtractionCardError.tsx     # Fallback for failed extraction
    ClassificationBadge.tsx     # Color-coded badge component
    VibeTags.tsx                # Pill-shaped vibe/hashtag tags
    VerifiedBadge.tsx           # Green checkmark for Google Places verified venues
    BookingButton.tsx           # "Tickets" / "Book" / "View on Maps" action button
    ThumbnailImage.tsx          # Thumbnail with fallback
```

### 2. Main ExtractionCard Component

**File:** `components/extraction/ExtractionCard.tsx`

```typescript
import React from 'react';
import { View, Text, StyleSheet, Pressable, Linking, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Classification, CLASSIFICATION_COLORS, CLASSIFICATION_LABELS } from '@/lib/ai/classification';
import { PLATFORM_ICONS } from '@/lib/utils/platform-icons';
import { ClassificationBadge } from './ClassificationBadge';
import { VibeTags } from './VibeTags';
import { VerifiedBadge } from './VerifiedBadge';
import { BookingButton } from './BookingButton';
import { ThumbnailImage } from './ThumbnailImage';

interface Reel {
  id: string;
  url: string;
  platform: string;
  extraction_data: ExtractionData | null;
  classification: Classification | null;
  created_at: string;
}

interface ExtractionCardProps {
  reel: Reel;
}

export function ExtractionCard({ reel }: ExtractionCardProps) {
  const { extraction_data, classification, platform } = reel;

  // Loading state — extraction not yet complete
  if (!extraction_data || extraction_data.error) {
    return <ExtractionCardSkeleton reel={reel} />;
  }

  const accentColor = classification
    ? CLASSIFICATION_COLORS[classification]
    : '#888888';

  const isVenue = classification === 'real_event' || classification === 'real_venue';
  const isEvent = classification === 'real_event';
  const isVibe = classification === 'vibe_inspiration';
  const isHumour = classification === 'humour_identity';

  // Parse vibe string into array
  const vibeArray = extraction_data.vibe
    ? extraction_data.vibe.split(',').map((v: string) => v.trim())
    : [];

  return (
    <View style={[styles.card, { borderLeftColor: accentColor, borderLeftWidth: 4 }]}>
      {/* Header Row: Platform Icon + Title + Classification Badge */}
      <View style={styles.headerRow}>
        <Ionicons
          name={PLATFORM_ICONS[platform]?.name || 'link'}
          size={18}
          color={PLATFORM_ICONS[platform]?.color || '#666'}
        />
        <Text style={styles.title} numberOfLines={2}>
          {extraction_data.title || reel.url}
        </Text>
        {classification && <ClassificationBadge type={classification} />}
      </View>

      {/* Thumbnail — larger for vibe_inspiration */}
      {extraction_data.thumbnail_url && (
        <ThumbnailImage
          url={extraction_data.thumbnail_url}
          isHero={isVibe}
        />
      )}

      {/* Venue + Location (real_event, real_venue) */}
      {isVenue && extraction_data.venue_name && (
        <View style={styles.venueRow}>
          <Text style={styles.venueName}>{extraction_data.venue_name}</Text>
          {extraction_data.verified?.status === 'found' && <VerifiedBadge />}
        </View>
      )}

      {extraction_data.location && (
        <Text style={styles.location}>{extraction_data.location}</Text>
      )}

      {/* Date + Price Row */}
      {(extraction_data.date || extraction_data.price) && (
        <View style={styles.metaRow}>
          {extraction_data.date && (
            <View style={styles.metaChip}>
              <Ionicons name="calendar-outline" size={14} color={accentColor} />
              <Text style={[styles.metaText, isEvent && styles.metaTextBold]}>
                {formatDate(extraction_data.date)}
              </Text>
            </View>
          )}
          {extraction_data.price && (
            <View style={styles.metaChip}>
              <Ionicons name="pricetag-outline" size={14} color={accentColor} />
              <Text style={styles.metaText}>{extraction_data.price}</Text>
            </View>
          )}
        </View>
      )}

      {/* Rating (verified venues) */}
      {extraction_data.verified?.rating && (
        <View style={styles.ratingRow}>
          <Ionicons name="star" size={14} color="#FFB800" />
          <Text style={styles.ratingText}>
            {extraction_data.verified.rating.toFixed(1)}
          </Text>
          {extraction_data.verified.total_ratings && (
            <Text style={styles.ratingCount}>
              ({extraction_data.verified.total_ratings})
            </Text>
          )}
        </View>
      )}

      {/* Activity / Mood */}
      {extraction_data.activity && !isHumour && (
        <Text style={styles.activity}>{extraction_data.activity}</Text>
      )}

      {/* Vibe Tags */}
      {vibeArray.length > 0 && <VibeTags tags={vibeArray} accentColor={accentColor} />}

      {/* Hashtags */}
      {extraction_data.hashtags && extraction_data.hashtags.length > 0 && (
        <Text style={styles.hashtags}>
          {extraction_data.hashtags.slice(0, 5).join(' ')}
        </Text>
      )}

      {/* Transcript Summary */}
      {extraction_data.transcript_summary && (
        <Text style={styles.transcriptSummary} numberOfLines={2}>
          {extraction_data.transcript_summary}
        </Text>
      )}

      {/* Creator */}
      {extraction_data.creator && (
        <Text style={styles.creator}>{extraction_data.creator}</Text>
      )}

      {/* Action Button */}
      {isEvent && extraction_data.booking_url && (
        <BookingButton
          url={extraction_data.booking_url}
          label="Get Tickets"
          color={accentColor}
        />
      )}

      {classification === 'real_venue' && extraction_data.verified?.maps_url && (
        <BookingButton
          url={extraction_data.verified.maps_url}
          label="View on Maps"
          color={accentColor}
        />
      )}
    </View>
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  } catch {
    return dateStr;
  }
}
```

### 3. Sub-Components

**ClassificationBadge.tsx:**

```typescript
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Classification, CLASSIFICATION_LABELS, CLASSIFICATION_COLORS } from '@/lib/ai/classification';

export function ClassificationBadge({ type }: { type: Classification }) {
  return (
    <View style={[styles.badge, { backgroundColor: CLASSIFICATION_COLORS[type] + '20' }]}>
      <Text style={[styles.badgeText, { color: CLASSIFICATION_COLORS[type] }]}>
        {CLASSIFICATION_LABELS[type]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
```

**VibeTags.tsx:**

```typescript
import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';

export function VibeTags({ tags, accentColor }: { tags: string[]; accentColor: string }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.container}>
      {tags.map((tag, i) => (
        <View key={i} style={[styles.tag, { borderColor: accentColor + '40' }]}>
          <Text style={[styles.tagText, { color: accentColor }]}>{tag}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexDirection: 'row', marginVertical: 6 },
  tag: {
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginRight: 6,
  },
  tagText: { fontSize: 12, fontWeight: '500' },
});
```

**BookingButton.tsx:**

```typescript
import React from 'react';
import { Pressable, Text, StyleSheet, Linking } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export function BookingButton({
  url,
  label,
  color,
}: {
  url: string;
  label: string;
  color: string;
}) {
  return (
    <Pressable
      style={[styles.button, { backgroundColor: color }]}
      onPress={() => Linking.openURL(url)}
    >
      <Ionicons name="arrow-forward-circle" size={18} color="#FFFFFF" />
      <Text style={styles.buttonText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginTop: 8,
    gap: 6,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
});
```

**VerifiedBadge.tsx:**

```typescript
import React from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export function VerifiedBadge() {
  return (
    <View style={{ marginLeft: 4 }}>
      <Ionicons name="checkmark-circle" size={16} color="#4ECDC4" />
    </View>
  );
}
```

**ThumbnailImage.tsx:**

```typescript
import React from 'react';
import { Image, StyleSheet, View } from 'react-native';

export function ThumbnailImage({ url, isHero }: { url: string; isHero?: boolean }) {
  return (
    <View style={styles.container}>
      <Image
        source={{ uri: url }}
        style={isHero ? styles.heroImage : styles.thumbnailImage}
        resizeMode="cover"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { borderRadius: 8, overflow: 'hidden', marginVertical: 6 },
  thumbnailImage: { width: '100%', height: 120, borderRadius: 8 },
  heroImage: { width: '100%', height: 200, borderRadius: 8 },
});
```

**ExtractionCardSkeleton.tsx:**

```typescript
import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { PLATFORM_ICONS } from '@/lib/utils/platform-icons';

export function ExtractionCardSkeleton({ reel }: { reel: { url: string; platform: string; extraction_data: any } }) {
  const isFailed = reel.extraction_data?.error;

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <Ionicons
          name={PLATFORM_ICONS[reel.platform]?.name || 'link'}
          size={18}
          color={PLATFORM_ICONS[reel.platform]?.color || '#666'}
        />
        <Text style={styles.url} numberOfLines={1}>{reel.url}</Text>
      </View>
      {isFailed ? (
        <View style={styles.statusRow}>
          <Ionicons name="alert-circle" size={16} color="#FF4444" />
          <Text style={styles.statusText}>Extraction failed</Text>
        </View>
      ) : (
        <View style={styles.statusRow}>
          <ActivityIndicator size="small" color="#888" />
          <Text style={styles.statusText}>Extracting...</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    padding: 12,
    marginVertical: 4,
    marginHorizontal: 16,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  url: { fontSize: 12, color: '#888', flex: 1 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  statusText: { fontSize: 12, color: '#888' },
});
```

### 4. Board Detail Screen Integration

In `app/(tabs)/board/[id].tsx`, render the reel list with extraction cards:

```typescript
import { FlatList } from 'react-native';
import { ExtractionCard } from '@/components/extraction/ExtractionCard';

// Inside the board detail screen component:
<FlatList
  data={reels}
  keyExtractor={(item) => item.id}
  renderItem={({ item }) => <ExtractionCard reel={item} />}
  contentContainerStyle={{ paddingBottom: 80 }}
  inverted={false}
/>
```

### 5. Card Styles

All cards share a base style with classification-specific accent:

```typescript
const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    marginVertical: 4,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A1A',
    flex: 1,
  },
  venueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  venueName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  location: {
    fontSize: 13,
    color: '#666666',
    marginTop: 2,
  },
  metaRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 6,
  },
  metaChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: 13,
    color: '#444444',
  },
  metaTextBold: {
    fontWeight: '700',
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  ratingText: { fontSize: 13, fontWeight: '600', color: '#1A1A1A' },
  ratingCount: { fontSize: 12, color: '#888888' },
  activity: {
    fontSize: 13,
    color: '#444444',
    marginTop: 4,
    fontStyle: 'italic',
  },
  hashtags: {
    fontSize: 12,
    color: '#888888',
    marginTop: 4,
  },
  transcriptSummary: {
    fontSize: 12,
    color: '#666666',
    marginTop: 6,
    fontStyle: 'italic',
    lineHeight: 18,
  },
  creator: {
    fontSize: 12,
    color: '#888888',
    marginTop: 4,
  },
});
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/extraction/ExtractionCard.tsx` | Main extraction card component with classification-aware layout |
| `components/extraction/ExtractionCardSkeleton.tsx` | Loading/error fallback card |
| `components/extraction/ClassificationBadge.tsx` | Color-coded classification badge |
| `components/extraction/VibeTags.tsx` | Pill-shaped vibe tag row |
| `components/extraction/VerifiedBadge.tsx` | Green checkmark for verified venues |
| `components/extraction/BookingButton.tsx` | "Tickets" / "View on Maps" action button |
| `components/extraction/ThumbnailImage.tsx` | Thumbnail image with hero mode |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Replace placeholder reel list with `FlatList` using `ExtractionCard` |

## Testing Guidance

### Visual Testing

Test each card variant by mocking different `extraction_data` + `classification` combinations:

1. **real_event card:** Mock data with venue_name, date, price, booking_url, verified data. Verify orange accent, "Get Tickets" button, date bold, verified checkmark.

2. **real_venue card:** Mock data with venue_name, location, rating, maps_url. Verify teal accent, "View on Maps" button, star rating.

3. **vibe_inspiration card:** Mock data with vibe tags, thumbnail, no venue. Verify purple accent, hero-sized thumbnail, prominent vibe tags.

4. **recipe_food card:** Mock data with activity "15-minute carbonara", thumbnail. Verify green accent.

5. **humour_identity card:** Mock data with title, hashtags, creator. Verify pink accent, compact layout.

6. **Loading state:** Mock reel with null extraction_data. Verify skeleton with ActivityIndicator.

7. **Error state:** Mock reel with `extraction_data: { error: "extraction_failed" }`. Verify error card with alert icon.

### Interactive Testing

- [ ] Tap "Get Tickets" button — opens booking URL in browser
- [ ] Tap "View on Maps" button — opens Google Maps
- [ ] Long-press on URL in skeleton card — URL is selectable
- [ ] Card scrolls smoothly in FlatList with 20+ reels

## Definition of Done

- [ ] All 7 extraction card sub-components created in `components/extraction/`
- [ ] `ExtractionCard` renders differently based on classification type (5 visual variants)
- [ ] Color-coded border accent for each classification type
- [ ] Classification badge shows correct label and color
- [ ] Platform icon renders for youtube, instagram, tiktok, x, and other
- [ ] Verified badge (green checkmark) appears for Google Places verified venues
- [ ] "Get Tickets" button appears for real_events with booking_url
- [ ] "View on Maps" button appears for real_venues with maps_url
- [ ] Buttons open URLs in device browser via `Linking.openURL()`
- [ ] Vibe tags render as scrollable pill-shaped tags
- [ ] Skeleton card shown while extraction is in progress
- [ ] Error card shown when extraction fails
- [ ] Board detail screen renders FlatList of ExtractionCards
- [ ] Cards render correctly on both iOS and Android
- [ ] No TypeScript errors
