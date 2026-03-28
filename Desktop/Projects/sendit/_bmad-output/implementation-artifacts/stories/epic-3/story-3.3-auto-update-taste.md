# Story 3.3: Auto-Update Taste Profile on New Reel

## Description

As the system,
I want to recalculate the taste profile automatically whenever a new reel is added and its extraction completes,
So that the profile stays current and responsive, updating live as the group shares more content.

## Status

- **Epic:** Epic 3 - Group Taste Intelligence
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR21 (real-time taste updates)
- **NFRs Covered:** NFR4 (recalculation < 2s), NFR2 (propagation < 1s)

## Acceptance Criteria

**Given** a member adds a reel to a board and the extraction pipeline completes (extraction_data is populated)
**When** the reel's `extraction_data` is saved to the database
**Then** the `taste-update` Edge Function is automatically invoked with the board's `board_id`
**And** the taste profile is recalculated using all reels (including the new one)
**And** all connected board members see the updated taste profile in real-time

**Given** a board has fewer than 3 reels with extraction data after the new reel is added
**When** the auto-update trigger fires
**Then** the `taste-update` function returns early with the "need 3+ reels" message
**And** no taste profile is created or displayed

**Given** the taste-update call fails (Claude API error)
**When** the auto-trigger fires after a new reel
**Then** the failure is logged but does not affect the reel addition
**And** the user does not see an error (the reel still appears on the board)
**And** the previous taste profile remains unchanged

**Given** multiple reels are added in rapid succession (e.g., a user pastes 3 URLs within 10 seconds)
**When** each reel's extraction completes
**Then** taste-update calls are debounced so that only one call is made after the final extraction settles
**And** the debounce window is 3 seconds after the last extraction completion

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK -> boards,
  extraction_data jsonb,  -- populated by extract Edge Function
  classification text,
  created_at timestamptz
)

taste_profiles (
  id uuid PK,
  board_id uuid FK -> boards UNIQUE,
  profile_data jsonb DEFAULT '{}',
  identity_label text,
  updated_at timestamptz
)
```

### Architecture References

- **Trigger approach:** Client-side trigger. After the reel extraction completes and `extraction_data` is saved, the client calls `taste-update`. This is simpler and more controllable than a Supabase database trigger for the hackathon.
- **Alternative (not recommended for hackathon):** A Supabase database trigger (pg_notify or a webhook trigger on reel UPDATE where extraction_data changes from null to non-null) could invoke the Edge Function server-side. This is more robust but harder to debug and set up in 24 hours.
- **Client pattern:** The extraction flow currently ends with the reel being updated in Supabase with `extraction_data`. The auto-trigger should be added at the end of this flow.
- **Debounce:** Use a module-level debounce in the client code that wraps the taste-update call. This prevents hammering the Edge Function when multiple reels are processed simultaneously.

### Dependencies

- **Story 3.1:** `taste-update` Edge Function must exist and be deployed
- **Story 3.2:** `taste-store.ts` and Realtime subscription must exist so that the updated profile propagates to all clients
- **Epic 2 (Story 2.1/2.2):** The reel addition and extraction flow must exist. This story modifies the end of that flow.
- **Library:** No new dependencies. Debounce can be implemented inline (no lodash needed).

## Implementation Notes

### Approach: Client-Side Trigger with Debounce

The cleanest approach for the hackathon is a client-side trigger. After the extraction Edge Function returns successfully and the reel's `extraction_data` is saved, the client also fires the `taste-update` call.

**Where to add the trigger:** In the reel submission flow. After the extraction completes, call `updateTasteProfile(boardId)` from `lib/ai/taste-engine.ts`.

### Debounce Implementation

Create a debounced version of the taste update call to handle rapid reel additions:

```typescript
// lib/ai/taste-engine.ts

import { supabase } from '../supabase';

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export async function updateTasteProfile(boardId: string) {
  const { data, error } = await supabase.functions.invoke('taste-update', {
    body: { board_id: boardId },
  });

  if (error) throw new Error(`Taste update failed: ${error.message}`);
  return data;
}

export function triggerTasteUpdateDebounced(boardId: string) {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(async () => {
    debounceTimer = null;
    try {
      await updateTasteProfile(boardId);
    } catch (error) {
      // Log but don't throw — taste update failure should not block reel flow
      console.warn('[taste-engine] Auto-update failed:', error);
    }
  }, 3000); // 3-second debounce window
}
```

### Integration Point: After Reel Extraction

The reel submission flow (from Epic 2) should be modified to call the debounced taste update after extraction completes. The typical flow is:

1. User pastes URL or shares via share sheet
2. Reel row is created in Supabase with `url`, `platform`, `board_id`, `added_by`
3. `extract` Edge Function is invoked, returns `extraction_data`
4. Reel row is updated with `extraction_data` and `classification`
5. **NEW: Call `triggerTasteUpdateDebounced(boardId)`**

```typescript
// In the reel submission handler (wherever it lives in the codebase)
// After extraction completes:

import { triggerTasteUpdateDebounced } from '@/lib/ai/taste-engine';

// ... after extraction_data is saved to the reel ...
triggerTasteUpdateDebounced(boardId);
```

### Why Client-Side, Not Database Trigger

For a hackathon, the client-side approach is better because:

1. **Debuggability:** You can see console logs, add breakpoints, catch errors
2. **No extra infrastructure:** No need to set up pg_net, pg_cron, or webhook targets
3. **Debounce control:** Easy to debounce on the client; database triggers fire on every row change
4. **Failure isolation:** If taste-update fails, the client handles it silently; a database trigger failure could be harder to diagnose

**Post-hackathon improvement:** Move to a Supabase database trigger or a pg_notify listener that calls the Edge Function server-side. This ensures taste profiles update even if the client disconnects after saving the reel.

### Realtime Propagation

No additional work needed here beyond what Story 3.2 implements. When the `taste-update` Edge Function upserts the `taste_profiles` row, Supabase Realtime fires a change event. All connected clients with the Realtime subscription (from Story 3.2) receive the update and render the new profile.

The flow:
1. Member A adds reel -> extraction completes -> client calls `taste-update`
2. `taste-update` upserts `taste_profiles` row
3. Supabase Realtime broadcasts the change
4. Member B's client receives the event -> `taste-store` updates -> `TasteProfile.tsx` re-renders

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Modify** | `lib/ai/taste-engine.ts` | Add `triggerTasteUpdateDebounced()` function with 3-second debounce |
| **Modify** | Reel submission handler (location TBD based on Epic 2 implementation — likely in a component or hook that handles URL paste/share) | Add call to `triggerTasteUpdateDebounced(boardId)` after extraction completes |

## Definition of Done

- [ ] `triggerTasteUpdateDebounced()` function exists in `lib/ai/taste-engine.ts` with 3-second debounce
- [ ] After a reel's extraction completes, the debounced taste update is automatically triggered
- [ ] The taste profile updates on all connected clients via Realtime (no manual refresh)
- [ ] Rapid reel additions (3 reels in 10 seconds) result in only one taste-update call after the final extraction
- [ ] Taste update failures are caught and logged but do not block or disrupt the reel addition flow
- [ ] Boards with fewer than 3 extracted reels do not trigger an error — the function returns early gracefully
- [ ] Manual test: add a 4th reel to a board with 3 existing reels, verify the taste profile appears/updates within 5 seconds (3s debounce + 2s function execution)
