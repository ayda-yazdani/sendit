# Story 6.3: Mutual Availability Computation

## Description

As the system,
I want to compute when all calendar-connected board members are simultaneously free,
So that plan suggestions land on times everyone can actually make.

## Status

- **Epic:** Calendar Integration & Progressive Auth
- **Priority:** P1
- **Branch:** `feature/calendar-auth`
- **Assignee:** Whoever finishes P0 first

## Acceptance Criteria

**Given** 2+ members on a board have calendar masks with busy_slots
**When** the suggest Edge Function runs
**Then** it reads all `calendar_masks` for the board's members
**And** computes overlapping free windows (times when ALL connected members are free)
**And** passes the top free windows to the Claude prompt as available times

**Given** the computed free windows exist
**When** Claude generates a suggestion
**Then** the suggestion's `when` field is set to a specific date and time within a mutual free window
**And** the suggestion_data includes a `_calendar_aware: true` flag

**Given** only 1 member has a calendar mask
**When** the suggest Edge Function runs
**Then** that member's availability is still considered, but the suggestion notes "limited calendar data"
**And** other members' availability is assumed to be open

**Given** no members have calendar masks
**When** the suggest Edge Function runs
**Then** the suggestion generation proceeds without calendar constraints (same as before Story 6.3)
**And** the suggestion's `when` field uses best-guess timing from Claude

**Given** all connected members are busy for the entire next 14 days
**When** availability is computed
**Then** the system returns "no mutual availability found"
**And** Claude is instructed to suggest a plan further out or with a flexible time

**Given** calendar data is older than 24 hours
**When** the suggest Edge Function needs availability
**Then** it still uses the stale data but includes a note that availability may be outdated

## Technical Context

### Relevant Schema

```sql
calendar_masks (
  id uuid PK,
  member_id uuid FK UNIQUE,
  busy_slots jsonb DEFAULT '[]',   -- Array of { start: ISO string, end: ISO string }
  synced_at timestamptz
)

members (
  id uuid PK,
  board_id uuid FK,
  display_name text,
  device_id text,
  google_id text nullable
)

suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb,   -- { what, why, where, when, cost_per_person, booking_url, influenced_by[], _calendar_aware }
  status text DEFAULT 'active',
  created_at timestamptz
)
```

### Architecture References

- **Edge Function:** `supabase/functions/suggest/index.ts` -- Extended to include availability computation
- **Calendar Data:** `calendar_masks` table -- read by the suggest function
- **Claude API:** Availability windows passed as context in the suggestion prompt
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 6.1 (Google OAuth) -- members have google_id
- **Requires:** Story 6.2 (calendar sync) -- calendar_masks populated with busy_slots
- **Requires:** Epic 4 (suggest Edge Function exists) -- this story extends it
- **Downstream:** Suggestion quality improves with calendar data

## Implementation Notes

### Availability Computation Algorithm

The algorithm computes free windows by:
1. Defining the search range (next 14 days, reasonable hours only: 10:00-23:00)
2. Merging all busy slots from all connected members
3. Finding gaps in the merged busy timeline

```typescript
// supabase/functions/suggest/availability.ts

interface TimeSlot {
  start: Date;
  end: Date;
}

interface FreeWindow {
  start: string; // ISO string
  end: string;   // ISO string
  durationHours: number;
}

/**
 * Compute mutual free windows from all members' busy slots.
 * Only considers "reasonable" hours (10:00 - 23:00 local time) on each day.
 */
export function computeMutualAvailability(
  allBusySlots: TimeSlot[][],  // Array of each member's busy slots
  searchDays: number = 14,
  reasonableStartHour: number = 10,
  reasonableEndHour: number = 23
): FreeWindow[] {
  // Merge all busy slots into a single sorted list
  const allSlots: TimeSlot[] = allBusySlots
    .flat()
    .sort((a, b) => a.start.getTime() - b.start.getTime());

  // Merge overlapping busy slots
  const merged: TimeSlot[] = [];
  for (const slot of allSlots) {
    if (merged.length === 0 || merged[merged.length - 1].end < slot.start) {
      merged.push({ ...slot });
    } else {
      merged[merged.length - 1].end = new Date(
        Math.max(merged[merged.length - 1].end.getTime(), slot.end.getTime())
      );
    }
  }

  // Generate free windows for each day within reasonable hours
  const freeWindows: FreeWindow[] = [];
  const now = new Date();

  for (let dayOffset = 0; dayOffset < searchDays; dayOffset++) {
    const day = new Date(now);
    day.setDate(day.getDate() + dayOffset);

    const dayStart = new Date(day);
    dayStart.setHours(reasonableStartHour, 0, 0, 0);

    const dayEnd = new Date(day);
    dayEnd.setHours(reasonableEndHour, 0, 0, 0);

    // Skip if day start is in the past
    const effectiveStart = dayStart > now ? dayStart : now;
    if (effectiveStart >= dayEnd) continue;

    // Find free gaps within this day's reasonable hours
    let cursor = effectiveStart;

    for (const busy of merged) {
      if (busy.end <= cursor) continue;     // Busy slot already passed
      if (busy.start >= dayEnd) break;       // Busy slot is after today's window

      const freeEnd = busy.start < dayEnd ? busy.start : dayEnd;
      if (freeEnd > cursor) {
        const durationHours = (freeEnd.getTime() - cursor.getTime()) / (1000 * 60 * 60);
        if (durationHours >= 1) {  // Minimum 1-hour window
          freeWindows.push({
            start: cursor.toISOString(),
            end: freeEnd.toISOString(),
            durationHours: Math.round(durationHours * 10) / 10,
          });
        }
      }
      cursor = new Date(Math.max(cursor.getTime(), busy.end.getTime()));
    }

    // Remaining time after last busy slot
    if (cursor < dayEnd) {
      const durationHours = (dayEnd.getTime() - cursor.getTime()) / (1000 * 60 * 60);
      if (durationHours >= 1) {
        freeWindows.push({
          start: cursor.toISOString(),
          end: dayEnd.toISOString(),
          durationHours: Math.round(durationHours * 10) / 10,
        });
      }
    }
  }

  return freeWindows;
}
```

### Integration into Suggest Edge Function

```typescript
// In supabase/functions/suggest/index.ts -- extend existing function

// 1. Get all members for this board
const { data: boardMembers } = await supabase
  .from('members')
  .select('id, google_id')
  .eq('board_id', boardId);

// 2. Get calendar masks for members who have connected Google
const connectedMemberIds = boardMembers
  ?.filter((m) => m.google_id)
  .map((m) => m.id) ?? [];

let availabilityContext = '';
let calendarAware = false;

if (connectedMemberIds.length >= 2) {
  const { data: masks } = await supabase
    .from('calendar_masks')
    .select('member_id, busy_slots, synced_at')
    .in('member_id', connectedMemberIds);

  if (masks && masks.length >= 2) {
    const allBusySlots = masks.map((m) =>
      (m.busy_slots as { start: string; end: string }[]).map((s) => ({
        start: new Date(s.start),
        end: new Date(s.end),
      }))
    );

    const freeWindows = computeMutualAvailability(allBusySlots);

    // Take top 5 free windows for the prompt
    const topWindows = freeWindows.slice(0, 5);

    if (topWindows.length > 0) {
      calendarAware = true;
      availabilityContext = `
CALENDAR AVAILABILITY (${connectedMemberIds.length} of ${boardMembers?.length} members have synced calendars):
The group is mutually free during these windows:
${topWindows.map((w) =>
  `- ${new Date(w.start).toLocaleDateString('en-GB', { weekday: 'long', month: 'short', day: 'numeric' })} ${new Date(w.start).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} - ${new Date(w.end).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} (${w.durationHours}h free)`
).join('\n')}

IMPORTANT: Suggest a specific time within one of these free windows. Prefer evening/weekend slots for social activities.`;
    } else {
      availabilityContext = `
CALENDAR: ${connectedMemberIds.length} members have synced calendars but no mutual free windows found in the next 14 days. Suggest a flexible time or a date further out.`;
    }
  }
} else if (connectedMemberIds.length === 1) {
  availabilityContext = `
CALENDAR: Only 1 member has synced their calendar. Limited availability data -- suggest a common evening/weekend time.`;
}

// 3. Include in Claude prompt
const prompt = `
${existingPromptContent}

${availabilityContext}

Generate a suggestion with a specific "when" that fits the group's availability.
`;
```

### Claude Prompt Addition for Calendar-Aware Suggestions

The availability context is injected into the existing suggestion prompt. When calendar data is available, the prompt explicitly instructs Claude to:

1. Pick a specific date and time from the free windows
2. Prefer evening/weekend slots for social plans
3. Consider the activity type (dinner = evening, brunch = morning, etc.)

### Marking Calendar-Aware Suggestions

When saving the suggestion, include a flag so the UI can indicate calendar-awareness:

```typescript
const suggestionData = {
  ...generatedSuggestion,
  _calendar_aware: calendarAware,
  _calendar_members_count: connectedMemberIds.length,
  _total_members_count: boardMembers?.length ?? 0,
};
```

### UI Indicator

On the suggestion card (Story 4.2), show a small calendar icon badge when `_calendar_aware: true`:

```
"Saturday 29 March, 7:30 PM" 📅 (Based on 3/5 members' availability)
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/suggest/availability.ts` | Pure function: computeMutualAvailability algorithm |

### Modify

| File | Change |
|------|--------|
| `supabase/functions/suggest/index.ts` | Read calendar_masks, compute availability, inject into Claude prompt |
| `components/suggestion/SuggestionCard.tsx` | Show calendar-aware indicator when `_calendar_aware: true` |

## Definition of Done

- [ ] Suggest Edge Function reads `calendar_masks` for all board members with `google_id`
- [ ] Mutual free windows computed correctly from overlapping busy slots
- [ ] Only "reasonable hours" (10:00-23:00) considered for social plans
- [ ] Minimum 1-hour free window threshold applied
- [ ] Top 5 free windows passed to Claude prompt as availability context
- [ ] Claude uses free windows to set a specific `when` in the suggestion
- [ ] Suggestion marked with `_calendar_aware: true` when calendar data was used
- [ ] Graceful fallback: 0 calendars = no constraint, 1 calendar = partial data noted
- [ ] Edge case: no mutual availability = Claude instructed to suggest flexible time
- [ ] No calendar event details exposed (only busy block start/end used)
- [ ] Stale calendar data (>24hr) still used with a note in the prompt
- [ ] UI shows calendar badge on calendar-aware suggestions
