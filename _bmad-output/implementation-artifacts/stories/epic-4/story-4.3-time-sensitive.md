# Story 4.3: Time-Sensitive Event Prioritization

## Description

As the system,
I want to prioritize real events with upcoming dates when generating suggestions,
So that time-sensitive opportunities are surfaced before they pass and the group does not miss out.

## Status

- **Epic:** Epic 4 - Plan Suggestions
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR28 (prioritize time-sensitive content)
- **NFRs Covered:** NFR5 (suggestion generation < 5s)

## Acceptance Criteria

**Given** a board has reels classified as `real_event` with dates in `extraction_data` that fall within the next 14 days
**When** the `suggest` Edge Function generates a suggestion
**Then** the Claude prompt explicitly instructs the model to strongly prefer suggesting those upcoming events
**And** the reel data passed to Claude includes a `days_until_event` field for each time-sensitive reel
**And** the resulting suggestion references one of the upcoming events (unless the events are clearly irrelevant to the group's taste)

**Given** a board has reels classified as `real_event` but all dates are more than 14 days away
**When** the `suggest` Edge Function generates a suggestion
**Then** the time-sensitive priority instruction is NOT included in the prompt
**And** Claude generates a suggestion based on overall taste profile as usual

**Given** a board has no reels classified as `real_event`
**When** the `suggest` Edge Function generates a suggestion
**Then** the time-sensitive priority instruction is NOT included in the prompt
**And** Claude generates a suggestion based on overall taste profile as usual

**Given** a board has multiple time-sensitive events within the next 14 days
**When** the `suggest` Edge Function generates a suggestion
**Then** the prompt lists all upcoming events with their dates and days remaining
**And** Claude chooses the most relevant one based on the group's taste profile

**Given** a time-sensitive event has already been suggested and the suggestion was archived (via regenerate in Story 4.4)
**When** a new suggestion is generated
**Then** the previously suggested event can still appear if it is the most relevant upcoming event (the regenerate flow handles avoiding duplicates separately)

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK -> boards,
  extraction_data jsonb,  -- May contain date fields: event_date, date, start_date
  classification text,    -- 'real_event' is the target classification
  created_at timestamptz
)
```

**Example extraction_data with event date:**

```json
{
  "venue_name": "Peckham Audio",
  "location": "133 Rye Lane, London SE15",
  "event_date": "2026-04-05",
  "price": "£12",
  "booking_url": "https://ra.co/events/...",
  "vibe": "underground, warehouse, techno",
  "activity": "club night"
}
```

Note: The date field name in `extraction_data` may vary depending on how the extraction pipeline (Epic 2) structures it. Common field names to check: `event_date`, `date`, `start_date`, `when`.

### Architecture References

- **This story modifies the `suggest` Edge Function** from Story 4.1 — it adds pre-processing logic to detect time-sensitive reels and augments the Claude prompt accordingly.
- **No new files are created** — this is purely a modification to the prompt construction logic in `supabase/functions/suggest/index.ts`.

### Dependencies

- **Story 4.1:** The `suggest` Edge Function must exist. This story modifies its prompt construction.
- **Epic 2 (Story 2.4):** Reels must be classified, including the `real_event` classification.
- **Epic 2 (Story 2.2):** Extraction data must include date information for event-type content.

## Implementation Notes

### Pre-Processing: Detect Time-Sensitive Reels

Before building the Claude prompt, scan all reels for time-sensitive events:

```typescript
interface TimeSensitiveReel {
  index: number;
  reelId: string;
  eventDate: string;
  daysUntil: number;
  extractionData: Record<string, any>;
  platform: string;
}

function findTimeSensitiveReels(reels: any[]): TimeSensitiveReel[] {
  const now = new Date();
  const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
  const timeSensitive: TimeSensitiveReel[] = [];

  reels.forEach((reel, index) => {
    if (reel.classification !== 'real_event') return;

    // Check multiple possible date field names in extraction_data
    const dateFields = ['event_date', 'date', 'start_date', 'when'];
    let eventDateStr: string | null = null;

    for (const field of dateFields) {
      if (reel.extraction_data?.[field]) {
        eventDateStr = reel.extraction_data[field];
        break;
      }
    }

    if (!eventDateStr) return;

    try {
      const eventDate = new Date(eventDateStr);
      if (isNaN(eventDate.getTime())) return;

      if (eventDate >= now && eventDate <= fourteenDaysFromNow) {
        const daysUntil = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        timeSensitive.push({
          index,
          reelId: reel.id,
          eventDate: eventDateStr,
          daysUntil,
          extractionData: reel.extraction_data,
          platform: reel.platform,
        });
      }
    } catch {
      // Skip reels with unparseable dates
    }
  });

  // Sort by soonest first
  timeSensitive.sort((a, b) => a.daysUntil - b.daysUntil);
  return timeSensitive;
}
```

### Augmented Claude Prompt

When time-sensitive reels are found, add a priority section to the user prompt:

```typescript
function buildSuggestionPrompt(
  tasteProfile: any,
  reels: any[],
  freeWindows: string[] | null,
  timeSensitiveReels: TimeSensitiveReel[]
): string {
  let prompt = `Here is a friend group's taste profile and the reels they've shared. Generate ONE specific plan suggestion.

GROUP TASTE PROFILE:
${JSON.stringify(tasteProfile.profile_data, null, 2)}

GROUP IDENTITY: ${tasteProfile.identity_label || 'Not yet generated'}

REELS SHARED (${reels.length} total):
${reels.map((r, i) => `[${i}] Platform: ${r.platform}, Classification: ${r.classification}, Extraction: ${JSON.stringify(r.extraction_data)}`).join('\n')}`;

  // Add time-sensitive priority section
  if (timeSensitiveReels.length > 0) {
    prompt += `\n\n⚡ TIME-SENSITIVE EVENTS (PRIORITY):
The following reels are classified as real events with dates in the NEXT 14 DAYS. You should STRONGLY prefer suggesting one of these events, as they are time-sensitive and will be missed if not acted on soon.

${timeSensitiveReels.map(ts => `- Reel [${ts.index}]: ${ts.extractionData.venue_name || 'Event'} on ${ts.eventDate} (${ts.daysUntil} days from now) — ${JSON.stringify(ts.extractionData)}`).join('\n')}

PRIORITY INSTRUCTION: If any of these upcoming events align with the group's taste profile, suggest that event. Only suggest something else if none of the upcoming events are a good fit for the group.`;
  }

  // Add calendar windows if available
  if (freeWindows && freeWindows.length > 0) {
    prompt += `\n\nMUTUAL FREE WINDOWS (the group is available during these times):
${freeWindows.join('\n')}

The suggested "when" MUST fall within one of these free windows.`;
  }

  prompt += `\n\nGenerate a suggestion as JSON with: what, why, where, when, cost_per_person, booking_url, influenced_by (array of reel indices from the list above).`;

  return prompt;
}
```

### Updated System Prompt Addition

Add to the existing system prompt from Story 4.1:

```typescript
// Append to SUGGESTION_SYSTEM_PROMPT:
const TIME_SENSITIVE_ADDENDUM = `
PRIORITY RULES FOR TIME-SENSITIVE EVENTS:
- If the user prompt includes a "TIME-SENSITIVE EVENTS" section, these events are happening soon and should be prioritized
- A time-sensitive event that aligns with even 2 of the group's taste dimensions should be suggested over a non-time-sensitive option that aligns with all dimensions
- When suggesting a time-sensitive event, make the urgency clear in the "why" field (e.g., "This is happening in 3 days and matches your group's love of underground music")
- If multiple time-sensitive events exist, choose the one that best matches the group's taste profile
- If no time-sensitive events are relevant, ignore the priority section and suggest based on overall taste`;
```

### Integration into `suggest/index.ts`

The modification to the Edge Function is minimal — add the time-sensitive detection before prompt construction:

```typescript
// In the main handler, after fetching reels:
const timeSensitiveReels = findTimeSensitiveReels(reels);

// Build the prompt with time-sensitive context
const userPrompt = buildSuggestionPrompt(
  tasteProfile,
  reels,
  freeWindows,  // from calendar masks (may be null)
  timeSensitiveReels
);

// Use the augmented system prompt
const systemPrompt = SUGGESTION_SYSTEM_PROMPT + TIME_SENSITIVE_ADDENDUM;

// Call Claude as before
const response = await callClaudeWithRetry(userPrompt, systemPrompt);
```

### Edge Case: Expired Events

Reels with event dates that have already passed should be excluded from the time-sensitive list. The `findTimeSensitiveReels` function handles this with the `eventDate >= now` check.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Modify** | `supabase/functions/suggest/index.ts` | Add `findTimeSensitiveReels()` function, augment Claude prompt with time-sensitive priority section, add time-sensitive addendum to system prompt |

## Definition of Done

- [ ] `findTimeSensitiveReels()` function scans reels for `real_event` classification with dates within 14 days
- [ ] Function handles multiple date field names in extraction_data (`event_date`, `date`, `start_date`, `when`)
- [ ] Function skips reels with unparseable or past dates
- [ ] Time-sensitive reels are sorted by soonest first
- [ ] When time-sensitive reels exist, the Claude prompt includes a priority section listing them with `days_until_event`
- [ ] System prompt includes the time-sensitive priority addendum
- [ ] When no time-sensitive reels exist, the prompt is unchanged from Story 4.1
- [ ] The resulting suggestion for boards with upcoming events references the event in its `what` and `why` fields
- [ ] The `why` field mentions the time urgency when suggesting a time-sensitive event
- [ ] Manual test: board with a `real_event` reel dated 5 days from now produces a suggestion for that event
- [ ] Manual test: board with only `vibe_inspiration` reels produces a normal taste-based suggestion (no time-sensitive section in prompt)
