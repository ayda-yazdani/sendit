# Story 3.1: Taste Profile Generation

## Description

As the system,
I want to analyze all reels on a board and generate a group taste profile,
So that the group's collective preferences are captured as structured data that powers identity labels and plan suggestions.

## Status

- **Epic:** Epic 3 - Group Taste Intelligence
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR20, FR25
- **NFRs Covered:** NFR4 (taste recalculation < 2s), NFR13 (Claude retry logic)

## Acceptance Criteria

**Given** a board has 3 or more reels with non-null `extraction_data`
**When** the `taste-update` Edge Function is invoked with `{ board_id }`
**Then** all reels for that board are fetched from the `reels` table
**And** all `extraction_data` and `platform` values are collected into a single payload
**And** the payload is sent to the Claude API with the taste profile generation prompt
**And** Claude returns a JSON object matching the `profile_data` schema
**And** the `taste_profiles` row for the board is upserted (insert if new, update if exists)
**And** `updated_at` is set to the current timestamp
**And** the response is returned to the caller with the new profile data

**Given** a board has fewer than 3 reels with extraction data
**When** the `taste-update` Edge Function is invoked
**Then** the function returns `{ data: null, message: "Need at least 3 reels to generate taste profile" }` with status 200
**And** no taste_profiles row is created or modified

**Given** the Claude API call fails
**When** the function retries once with exponential backoff (1 retry, 2s delay)
**And** the retry also fails
**Then** the function returns `{ error: "Taste profile generation failed", fallback: true }` with status 502
**And** any existing taste_profiles row is left unchanged

**Given** the Claude API returns malformed JSON
**When** the response cannot be parsed into the expected schema
**Then** the function returns `{ error: "Invalid profile format", fallback: true }` with status 500
**And** the malformed response is logged for debugging

## Technical Context

### Relevant Schema

```sql
-- Source data
reels (
  id uuid PK,
  board_id uuid FK -> boards,
  added_by uuid FK -> members,
  url text,
  platform text,          -- 'youtube' | 'instagram' | 'tiktok' | 'x' | 'other'
  extraction_data jsonb,  -- structured extraction from AI pipeline
  classification text,    -- 'real_event' | 'real_venue' | 'vibe_inspiration' | 'recipe_food' | 'humour_identity'
  created_at timestamptz
)

-- Output
taste_profiles (
  id uuid PK,
  board_id uuid FK -> boards UNIQUE,
  profile_data jsonb DEFAULT '{}',
  identity_label text,
  updated_at timestamptz
)
```

**profile_data jsonb structure:**

```json
{
  "activity_types": ["club nights", "rooftop bars", "dinner"],
  "aesthetic": "underground, intimate",
  "food_preferences": ["Japanese", "street food"],
  "location_patterns": ["east London", "Shoreditch"],
  "price_range": "~£15/head",
  "humour_style": "dark, absurdist",
  "platform_mix": { "tiktok": 5, "instagram": 3, "youtube": 2 }
}
```

### Architecture References

- **Edge Function pattern:** Supabase Edge Functions run on Deno. They receive a JSON body via `req.json()`, interact with Supabase via the service role client, call external APIs, and return JSON responses.
- **Supabase URL:** `https://ubhbeqnagxbuoikzftht.supabase.co`
- **Secrets required:** `CLAUDE_API_KEY` (stored as Supabase Edge Function secret), `SUPABASE_SERVICE_ROLE_KEY` (available automatically in Edge Functions)
- **Client calling pattern:**
  ```typescript
  const { data } = await supabase.functions.invoke('taste-update', { body: { board_id } });
  ```

### Dependencies

- **Upstream:** Epic 2 must be complete — reels must exist in the database with `extraction_data` populated by the `extract` Edge Function and `classification` populated by the `classify` Edge Function.
- **Downstream:** Story 3.2 (display), Story 3.3 (auto-trigger), Story 3.4 (identity label), Story 4.1 (suggestion generation) all depend on this function existing and returning valid profile data.
- **External:** Claude API (Anthropic) — model `claude-sonnet-4-20250514` for speed within NFR4 constraints.

## Implementation Notes

### Edge Function: `supabase/functions/taste-update/index.ts`

This is a Deno-based Supabase Edge Function. Use the `Anthropic` SDK for Deno or make direct HTTP calls to the Claude API.

**Claude API Prompt Template:**

```typescript
const TASTE_PROFILE_SYSTEM_PROMPT = `You are a cultural analyst for a friend group app called Sendit. You analyze shared video content extractions from a friend group and produce a structured taste profile that captures the group's collective personality.

You will receive an array of extraction objects from videos the group has shared. Each extraction contains metadata like venue names, locations, vibes, food references, activity types, humour signals, and the platform it was shared from.

Your job is to synthesize ALL extractions into a single group taste profile. Look for patterns, recurring themes, and collective preferences — not individual outliers.

RULES:
- activity_types: Array of 3-7 activity categories the group gravitates toward (e.g., "club nights", "rooftop bars", "dinner spots", "comedy shows", "galleries", "day trips")
- aesthetic: A short phrase (2-5 words) describing the group's overall vibe/aesthetic register (e.g., "underground, intimate", "bougie brunch energy", "chaotic and spontaneous")
- food_preferences: Array of 2-5 cuisine types or food styles (e.g., "Japanese", "street food", "brunch", "late-night kebabs")
- location_patterns: Array of 1-4 geographic areas or neighbourhoods the group's content clusters around (e.g., "east London", "Shoreditch", "Peckham")
- price_range: A human-readable string indicating the group's typical spend per person (e.g., "~£15/head", "£20-40/head", "budget-friendly")
- humour_style: A short phrase capturing the group's humour based on humour/identity content (e.g., "dark, absurdist", "wholesome chaos", "politically unhinged"). If no humour content exists, use "not enough data yet"
- platform_mix: An object counting how many reels came from each platform (e.g., { "tiktok": 5, "instagram": 3, "youtube": 2 })

Return ONLY valid JSON matching this exact structure. No markdown, no explanation, no wrapping.`;

const userPrompt = `Here are ${reels.length} video extractions shared by a friend group. Analyze them and produce the group taste profile.

EXTRACTIONS:
${JSON.stringify(reelData, null, 2)}

Return the taste profile as JSON with keys: activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix.`;
```

**Key implementation details:**

1. **Fetch reels:** Query all reels for the board where `extraction_data` is not null. Include `platform` and `classification` fields.
2. **Build reel data array:** For each reel, create an object with `{ platform, classification, extraction_data }` to give Claude full context.
3. **Count platform mix:** Calculate `platform_mix` on the server side (count reels per platform) and pass it to Claude as context, but also ask Claude to include it in the output for consistency.
4. **Call Claude API:** Use `claude-sonnet-4-20250514` model with `max_tokens: 1024` and `temperature: 0.3` (low creativity, high consistency for structured output).
5. **Parse response:** Extract the JSON from Claude's response. Use `JSON.parse()` with try/catch. Validate that all expected keys exist.
6. **Upsert:** Use Supabase's `.upsert()` on `taste_profiles` with `onConflict: 'board_id'`.
7. **Retry logic:** Wrap the Claude API call in a retry function — 1 retry with 2-second delay on failure (NFR13).

**Error handling:**

```typescript
// Retry wrapper
async function callClaudeWithRetry(prompt: string, systemPrompt: string, maxRetries = 1): Promise<string> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': Deno.env.get('CLAUDE_API_KEY')!,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1024,
          temperature: 0.3,
          system: systemPrompt,
          messages: [{ role: 'user', content: prompt }],
        }),
      });
      if (!response.ok) throw new Error(`Claude API ${response.status}`);
      const data = await response.json();
      return data.content[0].text;
    } catch (error) {
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
        continue;
      }
      throw error;
    }
  }
  throw new Error('Exhausted retries');
}
```

### Client-Side Wrapper: `lib/ai/taste-engine.ts`

```typescript
import { supabase } from '../supabase';

export async function updateTasteProfile(boardId: string) {
  const { data, error } = await supabase.functions.invoke('taste-update', {
    body: { board_id: boardId },
  });

  if (error) throw new Error(`Taste update failed: ${error.message}`);
  return data;
}
```

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Create** | `supabase/functions/taste-update/index.ts` | Edge Function: reads reels, calls Claude, upserts taste profile |
| **Create** | `lib/ai/taste-engine.ts` | Client wrapper to invoke the taste-update Edge Function |

## Definition of Done

- [ ] `taste-update` Edge Function is deployed to Supabase and responds to POST requests
- [ ] Function reads all reels with `extraction_data` for the given `board_id`
- [ ] Function returns early with a message if fewer than 3 reels have extraction data
- [ ] Claude API is called with the documented system and user prompts
- [ ] Claude response is parsed as JSON and validated for expected keys (`activity_types`, `aesthetic`, `food_preferences`, `location_patterns`, `price_range`, `humour_style`, `platform_mix`)
- [ ] `taste_profiles` row is upserted with the new `profile_data` and current timestamp
- [ ] Retry logic handles one transient Claude API failure with 2-second backoff
- [ ] Error responses are structured as `{ error: string, fallback: boolean }`
- [ ] `lib/ai/taste-engine.ts` client wrapper exists and correctly invokes the Edge Function
- [ ] Function completes within 2 seconds (NFR4) for boards with up to 20 reels
- [ ] Manual test: invoke with a board that has 3+ reels, verify taste_profiles row is created with valid JSON
