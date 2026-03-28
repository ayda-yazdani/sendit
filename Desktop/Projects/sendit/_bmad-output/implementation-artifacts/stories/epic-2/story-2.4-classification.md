# Story 2.4: Content Classification

## Description

As the system,
I want to classify each piece of content into one of five types,
So that the taste profile and suggestions can differentiate between event content and identity content.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person C (backend — prompt engineering)
- **FRs Covered:** FR17
- **Depends On:** Story 2.2 (extraction_data must exist on reel row)

## Acceptance Criteria

**Given** a reel has `extraction_data` populated (non-null, no error)
**When** the `classify` Edge Function is invoked with the extraction_data
**Then** Claude API returns exactly one of these five classification types:
  - `real_event` — a specific event with date, venue, tickets (e.g., a club night, festival, pop-up)
  - `real_venue` — a real place without a specific event date (e.g., a restaurant review, bar recommendation)
  - `vibe_inspiration` — aesthetic/mood content not tied to a real place (e.g., travel inspo, outfit ideas, aesthetic compilation)
  - `recipe_food` — food or drink content with recipe/cooking focus (e.g., cooking tutorial, cocktail recipe)
  - `humour_identity` — memes, dark humour, political satire, group identity content (e.g., brainrot, relatable content)
**And** the classification is stored on the `reels.classification` column
**And** the classification is returned to the calling client

**Given** the extraction_data is ambiguous (could be multiple types)
**When** Claude classifies it
**Then** exactly one type is returned — Claude must choose the most dominant signal
**And** the classification prompt includes tie-breaking rules

**Given** the classify Edge Function is called with malformed or empty extraction_data
**When** the input validation fails
**Then** the function returns `{ error: "Invalid extraction data" }` with HTTP 400

**Given** the extract Edge Function has already produced extraction_data
**When** the classification step runs
**Then** classification can optionally be merged into the `extract` Edge Function for a single round-trip
**And** the reel row is updated with both `extraction_data` and `classification` in one operation

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  ...
  extraction_data jsonb,     -- INPUT: populated by Story 2.2/2.3
  classification text,       -- OUTPUT: one of 5 types, set by this story
  ...
)
```

### The Five Classification Types

| Type | Signal Indicators | Example Content |
|------|-------------------|-----------------|
| `real_event` | Has date + venue + tickets/booking | "Peckham Audio club night, April 5, £12" |
| `real_venue` | Has venue name + location, no specific date | "Best ramen in Soho — Bone Daddies review" |
| `vibe_inspiration` | Aesthetic, travel, lifestyle — no specific real place | "Italian summer aesthetic compilation" |
| `recipe_food` | Cooking instructions, ingredients, food preparation | "Easy 15-minute carbonara recipe" |
| `humour_identity` | Memes, satire, commentary, relatable content | "POV: your friend group planning anything" |

### Architecture References

- **Edge Function option A (separate):** `supabase/functions/classify/index.ts` — standalone function
- **Edge Function option B (merged):** Add classification step to `supabase/functions/extract/index.ts` — runs after extraction, before response
- **Client calling pattern (if separate):** `supabase.functions.invoke('classify', { body: { extraction_data, reel_id } })`
- **Client calling pattern (if merged):** Classification happens automatically inside `extract` — no separate client call

### Dependencies

- Story 2.2 must be complete — extraction_data must be available
- `CLAUDE_API_KEY` configured as Supabase secret

## Implementation Notes

### Architecture Decision: Merged vs Separate

**Recommended: Merge into the `extract` Edge Function.** Rationale:
- Saves a network round-trip (client makes one call, not two)
- Classification depends directly on extraction_data — no reason to separate
- Simpler client code
- Still create `supabase/functions/classify/index.ts` as a standalone function for cases where re-classification is needed (e.g., after extraction_data is updated by Story 2.5 web verification)

### 1. Classification Prompt

This is the core of the story. The prompt must be highly specific to avoid ambiguous results.

```typescript
async function classifyWithClaude(
  extractionData: Record<string, unknown>
): Promise<string> {
  const claudeApiKey = Deno.env.get('CLAUDE_API_KEY');

  const systemPrompt = `You are a content classifier for Sendit, an app that categorises shared social media content to build a group taste profile.

Your job: Given structured extraction data from a social media video, classify it into EXACTLY ONE of five types. Return ONLY the type string, nothing else.

THE FIVE TYPES:

1. real_event — A specific event happening at a specific time.
   REQUIRED SIGNALS: Must have EITHER a specific date OR mention of "this weekend", "tonight", "next Saturday", etc. AND a venue or location.
   Examples: club night, festival, pop-up dinner, comedy show, sports match, gig, exhibition opening.
   Key indicator: You could buy a ticket or mark a calendar date.

2. real_venue — A real, visitable place without a specific event date.
   REQUIRED SIGNALS: Must have a venue name that is a real business/place AND a location.
   Examples: restaurant review, bar recommendation, cafe, park, museum, attraction, hotel.
   Key indicator: You could Google Maps it and go there any day.

3. vibe_inspiration — Aesthetic or lifestyle content not tied to a specific real place.
   SIGNALS: Travel aesthetic compilations, outfit inspo, "places to visit" lists without specific venues, mood boards, lifestyle content, activity ideas without specific venues.
   Key indicator: It inspires a type of experience, not a specific destination.

4. recipe_food — Food or drink content focused on preparation/cooking.
   SIGNALS: Recipe steps, ingredient lists, cooking tutorials, cocktail making, baking.
   Key indicator: The content teaches you how to MAKE something, not where to EAT it.

5. humour_identity — Memes, satire, commentary, or identity-signalling content.
   SIGNALS: Memes, dark humour, political satire, relatable POV content, commentary, opinions, "brainrot", group identity content.
   Key indicator: This content reveals personality and taste, but doesn't suggest an activity or place.

TIE-BREAKING RULES (in order):
- If content has a date AND venue: real_event (even if it's also funny)
- If content has a venue name but no date: real_venue (even if it's aesthetic)
- If content is about food and includes a recipe: recipe_food (even if it mentions a restaurant)
- If content is about food at a restaurant (no recipe): real_venue
- If content is purely aesthetic/mood with no specific place: vibe_inspiration
- Default for ambiguous content: humour_identity

RESPOND WITH ONLY ONE OF: real_event, real_venue, vibe_inspiration, recipe_food, humour_identity
No explanation. No punctuation. Just the type string.`;

  const userPrompt = `Classify this content:

${JSON.stringify(extractionData, null, 2)}`;

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': claudeApiKey!,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 50,
      system: systemPrompt,
      messages: [
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`Claude API error: ${response.status}`);
  }

  const result = await response.json();
  const classification = result.content[0]?.text?.trim().toLowerCase();

  // Validate the classification is one of the expected types
  const validTypes = ['real_event', 'real_venue', 'vibe_inspiration', 'recipe_food', 'humour_identity'];
  if (!validTypes.includes(classification)) {
    console.warn(`Invalid classification from Claude: "${classification}", defaulting to humour_identity`);
    return 'humour_identity';
  }

  return classification;
}
```

### 2. Merging into Extract Edge Function

Add classification as the final step in `supabase/functions/extract/index.ts`:

```typescript
// After extraction completes successfully:
const extractionData = await callWithRetry(() =>
  extractWithClaude(rawMetadata, url, platform, transcript, visionDescription)
);

// Classify the extraction data
const classification = await callWithRetry(() =>
  classifyWithClaude(extractionData)
);

// Add classification type to extraction_data for convenience
extractionData.type = classification;

// Update reel row with BOTH extraction_data and classification
await supabaseAdmin
  .from('reels')
  .update({
    extraction_data: extractionData,
    classification: classification,
  })
  .eq('id', reel_id);

// Return both to client
return new Response(JSON.stringify({ extraction_data: extractionData, classification }), {
  headers: { 'Content-Type': 'application/json' },
});
```

### 3. Standalone Classify Edge Function

Also create the standalone function for re-classification scenarios:

**File:** `supabase/functions/classify/index.ts`

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    });
  }

  try {
    const { extraction_data, reel_id } = await req.json();

    if (!extraction_data || !reel_id) {
      return new Response(
        JSON.stringify({ error: 'extraction_data and reel_id are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const classification = await classifyWithClaude(extraction_data);

    // Update reel row
    const supabaseAdmin = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );

    await supabaseAdmin
      .from('reels')
      .update({ classification })
      .eq('id', reel_id);

    return new Response(JSON.stringify({ classification }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});

// Include the classifyWithClaude function here (same as above)
```

### 4. Client-Side Classification Service

**File:** `lib/ai/classification.ts`

```typescript
import { supabase } from '@/lib/supabase';

export type Classification =
  | 'real_event'
  | 'real_venue'
  | 'vibe_inspiration'
  | 'recipe_food'
  | 'humour_identity';

export const CLASSIFICATION_LABELS: Record<Classification, string> = {
  real_event: 'Event',
  real_venue: 'Venue',
  vibe_inspiration: 'Vibe',
  recipe_food: 'Recipe',
  humour_identity: 'Mood',
};

export const CLASSIFICATION_COLORS: Record<Classification, string> = {
  real_event: '#FF6B35',   // Orange — urgency, time-sensitive
  real_venue: '#4ECDC4',   // Teal — places, maps
  vibe_inspiration: '#A78BFA', // Purple — aesthetic, mood
  recipe_food: '#34D399',  // Green — food, fresh
  humour_identity: '#F472B6', // Pink — personality, fun
};

/**
 * Re-classify a reel (standalone function call).
 * Normally classification happens inside the extract function.
 * Use this only when re-classification is needed.
 */
export async function invokeClassification(
  reelId: string,
  extractionData: Record<string, unknown>
): Promise<Classification | null> {
  try {
    const { data, error } = await supabase.functions.invoke('classify', {
      body: { extraction_data: extractionData, reel_id: reelId },
    });

    if (error) {
      console.warn('Classification failed:', error.message);
      return null;
    }

    return data.classification as Classification;
  } catch (err) {
    console.warn('Classification service unavailable:', err);
    return null;
  }
}
```

### 5. Classification Accuracy Validation

For the hackathon demo, prepare a set of test URLs with expected classifications to validate accuracy:

| URL Content | Expected Classification |
|-------------|------------------------|
| YouTube Shorts: creator recommends a specific club night with date and price | `real_event` |
| Instagram reel: restaurant review with venue name and location | `real_venue` |
| TikTok: "Italian summer aesthetic" compilation | `vibe_inspiration` |
| YouTube Shorts: "15-minute pasta recipe" | `recipe_food` |
| TikTok: "POV: your friend group trying to make plans" | `humour_identity` |
| Instagram reel: rooftop bar review (no specific event) | `real_venue` |
| YouTube Shorts: music festival lineup announcement with dates | `real_event` |
| TikTok: dark humour about London rent prices | `humour_identity` |

Target: >80% accuracy across these test cases (NFR target).

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/classify/index.ts` | Standalone classify Edge Function for re-classification |
| `lib/ai/classification.ts` | Client-side classification service + type definitions + color/label constants |

### Modify

| File | Change |
|------|--------|
| `supabase/functions/extract/index.ts` | Add `classifyWithClaude()` function and call it after extraction, update reel with both extraction_data and classification |

## Testing Guidance

### Prompt Testing

Before deploying, test the classification prompt directly with the Claude API or Claude web interface:

1. Paste the system prompt and user prompt
2. Submit extraction_data for each of the 8 test cases above
3. Verify the response is exactly one of the 5 valid types
4. Count accuracy: must be 7/8 or better

### Edge Function Testing

```bash
# Test standalone classify function
curl -X POST http://localhost:54321/functions/v1/classify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{
    "reel_id": "test-uuid",
    "extraction_data": {
      "venue_name": "Peckham Audio",
      "location": "Peckham, London",
      "price": "£12",
      "date": "2026-04-05",
      "activity": "club night",
      "mood": "high energy",
      "vibe": "underground, warehouse"
    }
  }'
# Expected: { "classification": "real_event" }
```

### Verification

```sql
SELECT classification, COUNT(*) as count
FROM reels
WHERE classification IS NOT NULL
GROUP BY classification;
```

## Definition of Done

- [ ] `classifyWithClaude()` function implemented with the full classification prompt
- [ ] Prompt includes all 5 classification types with clear signal indicators
- [ ] Prompt includes tie-breaking rules for ambiguous content
- [ ] Classification merged into `extract` Edge Function (runs after extraction, before response)
- [ ] Standalone `classify` Edge Function created for re-classification scenarios
- [ ] Client-side `lib/ai/classification.ts` created with type definitions, labels, and colors
- [ ] Claude returns exactly one of the 5 valid types (validated with fallback to `humour_identity`)
- [ ] `reels.classification` column populated after extraction completes
- [ ] Classification accuracy is >80% across 8+ test cases
- [ ] Both Edge Functions deployed to Supabase
- [ ] No additional latency budget exceeded — classification adds ~300ms (small prompt, max_tokens: 50)
