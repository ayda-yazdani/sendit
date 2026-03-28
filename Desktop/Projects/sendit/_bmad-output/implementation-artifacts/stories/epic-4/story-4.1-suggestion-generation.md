# Story 4.1: Suggestion Generation Edge Function

## Description

As a board member,
I want the app to generate one specific, actionable plan suggestion based on our group's taste profile,
So that our shared interests turn into a concrete plan with a venue, time, cost, and booking link.

## Status

- **Epic:** Epic 4 - Plan Suggestions
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR26 (generate plan suggestion), FR27 (what/why/where/when/cost/booking), FR29 (calendar-aware)
- **NFRs Covered:** NFR5 (suggestion generation < 5s), NFR13 (Claude retry logic)

## Acceptance Criteria

**Given** a board has a taste profile with populated `profile_data`
**When** the `suggest` Edge Function is invoked with `{ board_id }`
**Then** the taste profile is read from `taste_profiles`
**And** all reels with extraction data are read from `reels` (to populate `influenced_by`)
**And** calendar masks are read from `calendar_masks` for all board members (if any exist)
**And** Claude API generates one specific suggestion as JSON with: `what`, `why`, `where`, `when`, `cost_per_person`, `booking_url`, `influenced_by`
**And** the suggestion is inserted into the `suggestions` table with `status: 'active'`
**And** the response returns the new suggestion data
**And** generation completes within 5 seconds (NFR5)

**Given** a board does not have a taste profile
**When** the `suggest` Edge Function is invoked
**Then** the function returns `{ data: null, message: "No taste profile exists for this board. Share more reels first." }` with status 200

**Given** calendar masks exist for some board members
**When** Claude generates the suggestion
**Then** the prompt includes the mutual free windows computed from calendar masks
**And** the suggested `when` field falls within a mutual free window

**Given** no calendar masks exist for any board members
**When** Claude generates the suggestion
**Then** the prompt does not reference calendar availability
**And** Claude suggests a reasonable time based on the activity type (e.g., club nights on weekend evenings, brunch on weekend mornings)

**Given** the Claude API call fails after retry
**When** the function returns an error
**Then** the response is `{ error: "Suggestion generation failed", fallback: true }` with status 502
**And** no suggestion row is created

**Given** there is already an active suggestion for the board
**When** a new suggestion is generated
**Then** the new suggestion is inserted alongside the existing one (the `suggest` function does not archive old suggestions — that is handled by Story 4.4's regenerate flow)

## Technical Context

### Relevant Schema

```sql
-- Input: taste profile
taste_profiles (
  id uuid PK,
  board_id uuid FK -> boards UNIQUE,
  profile_data jsonb DEFAULT '{}',
  identity_label text,
  updated_at timestamptz
)

-- Input: reels (for influenced_by references)
reels (
  id uuid PK,
  board_id uuid FK -> boards,
  url text,
  platform text,
  extraction_data jsonb,
  classification text,
  created_at timestamptz
)

-- Input: calendar availability (optional)
calendar_masks (
  id uuid PK,
  member_id uuid FK -> members UNIQUE,
  busy_slots jsonb DEFAULT '[]',  -- Array of { start: ISO string, end: ISO string }
  synced_at timestamptz
)

-- Input: board members (to find calendar masks)
members (
  id uuid PK,
  board_id uuid FK -> boards,
  display_name text,
  device_id text
)

-- Output: suggestion
suggestions (
  id uuid PK,
  board_id uuid FK -> boards,
  suggestion_data jsonb NOT NULL,
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
  created_at timestamptz
)
```

**suggestion_data jsonb structure:**

```json
{
  "what": "Club night at Peckham Audio",
  "why": "3 of you have been sending underground music reels for 2 weeks",
  "where": "Peckham Audio, 133 Rye Lane, London SE15",
  "when": "Saturday 5 April, 10pm",
  "cost_per_person": "£12",
  "booking_url": "https://ra.co/events/...",
  "influenced_by": ["reel-uuid-1", "reel-uuid-2", "reel-uuid-3"]
}
```

### Architecture References

- **Edge Function:** `supabase/functions/suggest/index.ts` — Deno-based, same pattern as `taste-update`
- **Supabase URL:** `https://ubhbeqnagxbuoikzftht.supabase.co`
- **Secrets:** `CLAUDE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- **Client calling pattern:**
  ```typescript
  const { data } = await supabase.functions.invoke('suggest', { body: { board_id } });
  ```

### Dependencies

- **Story 3.1 + 3.4:** Taste profile must exist with `profile_data` and `identity_label`
- **Epic 2:** Reels must exist with `extraction_data` and `classification`
- **Epic 6 (optional):** Calendar masks may or may not exist. The function must handle both cases.
- **External:** Claude API (Anthropic) — model `claude-sonnet-4-20250514`

## Implementation Notes

### Edge Function: `supabase/functions/suggest/index.ts`

**Step-by-step logic:**

1. Parse `board_id` from request body
2. Fetch taste profile for the board
3. If no taste profile, return early with message
4. Fetch all reels for the board with non-null `extraction_data`
5. Fetch all members of the board
6. Fetch calendar masks for those members (may be empty)
7. If calendar masks exist, compute mutual free windows
8. Build Claude prompt with taste profile, reel summaries, and (optionally) free windows
9. Call Claude API with retry logic
10. Parse the suggestion JSON from Claude's response
11. Map `influenced_by` reel references to actual reel UUIDs
12. Insert suggestion into `suggestions` table
13. Return the new suggestion

### Mutual Free Window Computation

```typescript
interface BusySlot {
  start: string; // ISO 8601
  end: string;   // ISO 8601
}

function computeFreeWindows(calendarMasks: { busy_slots: BusySlot[] }[], daysAhead: number = 14): string[] {
  // Merge all busy slots across all members
  const allBusy: BusySlot[] = calendarMasks.flatMap(m => m.busy_slots);

  // Sort by start time
  allBusy.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());

  // Merge overlapping slots
  const merged: BusySlot[] = [];
  for (const slot of allBusy) {
    if (merged.length === 0 || new Date(slot.start) > new Date(merged[merged.length - 1].end)) {
      merged.push({ ...slot });
    } else {
      merged[merged.length - 1].end = new Date(Math.max(
        new Date(merged[merged.length - 1].end).getTime(),
        new Date(slot.end).getTime()
      )).toISOString();
    }
  }

  // Find gaps (free windows) in the next N days
  const now = new Date();
  const end = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);
  const freeWindows: string[] = [];

  let cursor = now;
  for (const slot of merged) {
    const slotStart = new Date(slot.start);
    if (slotStart > cursor) {
      freeWindows.push(`${cursor.toISOString()} to ${slotStart.toISOString()}`);
    }
    cursor = new Date(Math.max(cursor.getTime(), new Date(slot.end).getTime()));
  }
  if (cursor < end) {
    freeWindows.push(`${cursor.toISOString()} to ${end.toISOString()}`);
  }

  return freeWindows;
}
```

### Claude API Prompt Template

**System Prompt:**

```typescript
const SUGGESTION_SYSTEM_PROMPT = `You are a plan-making assistant for a friend group app called Sendit. You generate ONE specific, actionable plan suggestion for a friend group based on their taste profile and the content they've shared.

Your suggestion must be a REAL, specific plan — not a vague idea. Include a real venue name, a specific date/time, an estimated cost, and a booking URL if the venue/event has one.

RULES:
- "what": A concise description of the plan (1 sentence, e.g., "Club night at Peckham Audio" or "Dinner at Koya, Soho")
- "why": A 1-2 sentence explanation of WHY this suggestion fits the group, referencing their shared content patterns (e.g., "3 of you have been sending underground music reels for 2 weeks" or "Your board is heavy on Japanese food and intimate dinner spots")
- "where": Full venue name and address (e.g., "Peckham Audio, 133 Rye Lane, London SE15")
- "when": A specific date and time suggestion (e.g., "Saturday 5 April, 10pm"). Choose a time that makes sense for the activity type.
- "cost_per_person": Estimated cost per person as a string (e.g., "£12", "£25-35", "Free")
- "booking_url": A plausible booking URL for the venue or event. If you know the venue exists on a booking platform (RA for clubs, OpenTable for restaurants, Eventbrite for events), construct a plausible URL. If unknown, use an empty string "".
- "influenced_by": An array of 2-4 reel indices (0-based) from the provided reel list that most strongly influenced this suggestion. These will be mapped to reel UUIDs by the system.

IMPORTANT:
- The suggestion must feel personally tailored to THIS group based on their taste profile
- Prefer specific, well-known venues in the group's location patterns
- The "why" must reference actual patterns visible in their taste profile or reels
- If suggesting a time-sensitive event, note urgency in the "why"
- Cost should be realistic for the venue and activity type

Return ONLY valid JSON matching this exact structure. No markdown, no explanation, no wrapping.`;
```

**User Prompt (without calendar):**

```typescript
const userPromptNoCalendar = `Here is a friend group's taste profile and the reels they've shared. Generate ONE specific plan suggestion.

GROUP TASTE PROFILE:
${JSON.stringify(tasteProfile.profile_data, null, 2)}

GROUP IDENTITY: ${tasteProfile.identity_label || 'Not yet generated'}

REELS SHARED (${reels.length} total):
${reels.map((r, i) => `[${i}] Platform: ${r.platform}, Classification: ${r.classification}, Extraction: ${JSON.stringify(r.extraction_data)}`).join('\n')}

Generate a suggestion as JSON with: what, why, where, when, cost_per_person, booking_url, influenced_by (array of reel indices from the list above).`;
```

**User Prompt (with calendar availability):**

```typescript
const userPromptWithCalendar = `Here is a friend group's taste profile, shared reels, and their mutual availability windows. Generate ONE specific plan suggestion that fits within their free time.

GROUP TASTE PROFILE:
${JSON.stringify(tasteProfile.profile_data, null, 2)}

GROUP IDENTITY: ${tasteProfile.identity_label || 'Not yet generated'}

REELS SHARED (${reels.length} total):
${reels.map((r, i) => `[${i}] Platform: ${r.platform}, Classification: ${r.classification}, Extraction: ${JSON.stringify(r.extraction_data)}`).join('\n')}

MUTUAL FREE WINDOWS (the group is available during these times):
${freeWindows.join('\n')}

Generate a suggestion as JSON with: what, why, where, when (MUST be within one of the free windows above), cost_per_person, booking_url, influenced_by (array of reel indices from the list above).`;
```

### Post-Processing: Map Reel Indices to UUIDs

Claude returns `influenced_by` as an array of reel indices. Map these to actual reel UUIDs before inserting:

```typescript
const suggestionJson = JSON.parse(claudeResponse);

// Map influenced_by indices to reel UUIDs
const influencedByUuids = (suggestionJson.influenced_by || [])
  .filter((i: number) => i >= 0 && i < reels.length)
  .map((i: number) => reels[i].id);

const suggestionData = {
  ...suggestionJson,
  influenced_by: influencedByUuids,
};

// Insert into suggestions table
const { data, error } = await supabaseAdmin
  .from('suggestions')
  .insert({
    board_id: boardId,
    suggestion_data: suggestionData,
    status: 'active',
  })
  .select()
  .single();
```

### Client-Side Wrapper: `lib/ai/suggestion-engine.ts`

```typescript
import { supabase } from '../supabase';

export async function generateSuggestion(boardId: string) {
  const { data, error } = await supabase.functions.invoke('suggest', {
    body: { board_id: boardId },
  });

  if (error) throw new Error(`Suggestion generation failed: ${error.message}`);
  return data;
}
```

### Retry Logic

Same pattern as Story 3.1 — 1 retry with 2-second exponential backoff. Use `claude-sonnet-4-20250514` with `max_tokens: 1024` and `temperature: 0.5` (slightly higher creativity than taste profile since we want varied, interesting suggestions).

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Create** | `supabase/functions/suggest/index.ts` | Edge Function: reads taste profile + reels + calendar masks, calls Claude, inserts suggestion |
| **Create** | `lib/ai/suggestion-engine.ts` | Client wrapper to invoke the suggest Edge Function |

## Definition of Done

- [ ] `suggest` Edge Function is deployed to Supabase and responds to POST requests
- [ ] Function reads taste profile for the board and returns early if none exists
- [ ] Function reads all reels with extraction data for the board
- [ ] Function reads calendar masks for all board members (handles empty case)
- [ ] If calendar masks exist, mutual free windows are computed and included in the prompt
- [ ] Claude API is called with the documented system and user prompts
- [ ] Claude response is parsed as JSON and validated for expected keys (`what`, `why`, `where`, `when`, `cost_per_person`, `booking_url`, `influenced_by`)
- [ ] Reel indices in `influenced_by` are mapped to actual reel UUIDs
- [ ] Suggestion is inserted into `suggestions` table with `status: 'active'`
- [ ] Retry logic handles one transient Claude API failure with 2-second backoff
- [ ] Error responses are structured as `{ error: string, fallback: boolean }`
- [ ] `lib/ai/suggestion-engine.ts` client wrapper exists and correctly invokes the Edge Function
- [ ] Function completes within 5 seconds (NFR5)
- [ ] Manual test: invoke with a board that has a taste profile and 5+ reels, verify a suggestion is created with realistic venue/time/cost data
