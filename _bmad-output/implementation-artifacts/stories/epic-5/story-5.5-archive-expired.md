# Story 5.5: Archive Expired Suggestions

## Description

As the system,
I want to archive suggestions that expire without sufficient commitment after 96 hours,
So that the board stays clean and focused on active plans, and dead suggestions feed the "plans you never took" archive.

## Status

- **Epic:** Commitment & Social Pressure
- **Priority:** P1
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B

## Acceptance Criteria

**Given** a suggestion has been active for 96+ hours (created_at + 96hr <= now)
**When** the system checks for expired suggestions
**Then** it evaluates whether the suggestion has sufficient commitment (3+ members with status = 'in')

**Given** a suggestion is 96+ hours old with fewer than 3 "in" commitments
**When** the archive threshold is reached
**Then** the suggestion's `status` is updated from 'active' to 'archived'
**And** the suggestion is removed from the active suggestion view on all connected clients
**And** the archived suggestion data is preserved for the "plans you never took" feature (Story 7.6)

**Given** a suggestion is 96+ hours old with 3+ "in" commitments
**When** the archive check runs
**Then** the suggestion is NOT archived (it has sufficient commitment)

**Given** a suggestion has already been archived
**When** the archive check runs again
**Then** no action is taken (idempotent)

**Given** a suggestion is archived
**When** a board member refreshes the suggestion screen
**Then** the archived suggestion is no longer displayed as the active suggestion
**And** the UI prompts to generate a new suggestion or shows the "plans you never took" link

## Technical Context

### Relevant Schema

```sql
suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb,   -- { what, why, where, when, cost_per_person, booking_url, influenced_by[] }
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
  created_at timestamptz DEFAULT now()
)

commitments (
  id uuid PK,
  suggestion_id uuid FK,
  member_id uuid FK,
  status text CHECK (status IN ('in', 'maybe', 'out')),
  receipt_url text,
  updated_at timestamptz
)
```

### Architecture References

- **Edge Function:** `supabase/functions/decay-check/index.ts` -- Archive logic is added to the existing decay-check function (same cron, additional step)
- **Screen:** `app/(tabs)/suggestion/[id].tsx` -- Needs to handle archived state
- **Store:** `lib/stores/board-store.ts` or `lib/stores/commitment-store.ts` -- Reactive to suggestion status changes
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 5.1 (voting) -- commitment data exists
- **Requires:** Story 5.3 (decay-check) -- the cron infrastructure and Edge Function where archive logic is added
- **Downstream:** Story 7.6 (Plans You Never Took) -- consumes archived suggestions

## Implementation Notes

### Adding Archive Logic to decay-check

Extend the existing `decay-check` Edge Function (from Story 5.3) to also handle archiving. This avoids creating a separate cron job.

```typescript
// Add to supabase/functions/decay-check/index.ts

// --- ARCHIVE CHECK (96 hours) ---
const ninetySixHoursAgo = new Date(Date.now() - 96 * 60 * 60 * 1000).toISOString();

// Find active suggestions older than 96 hours
const { data: expiredSuggestions, error: expError } = await supabase
  .from('suggestions')
  .select('id, board_id, suggestion_data')
  .eq('status', 'active')
  .lt('created_at', ninetySixHoursAgo);

if (expiredSuggestions?.length) {
  for (const suggestion of expiredSuggestions) {
    // Count "in" commitments
    const { count: inCount } = await supabase
      .from('commitments')
      .select('*', { count: 'exact', head: true })
      .eq('suggestion_id', suggestion.id)
      .eq('status', 'in');

    // If fewer than 3 "in" commitments, archive it
    if (!inCount || inCount < 3) {
      await supabase
        .from('suggestions')
        .update({
          status: 'archived',
          suggestion_data: {
            ...suggestion.suggestion_data,
            _archived_at: new Date().toISOString(),
            _archived_reason: 'insufficient_commitment',
            _final_in_count: inCount ?? 0,
          },
        })
        .eq('id', suggestion.id);
    }
  }
}
```

### Threshold: Why 3?

The threshold of 3 "in" commitments for survival matches the event creation threshold in Story 7.1. If a suggestion reaches 3 "in" votes, it's viable enough to survive. If it doesn't reach 3 in 96 hours, it's archived.

### Client-Side: Handling Archived Suggestions

The suggestion screen should react to status changes via Realtime subscription:

```typescript
// Subscribe to suggestion status changes
const channel = supabase
  .channel(`suggestion:${suggestionId}`)
  .on(
    'postgres_changes',
    {
      event: 'UPDATE',
      schema: 'public',
      table: 'suggestions',
      filter: `id=eq.${suggestionId}`,
    },
    (payload) => {
      if (payload.new.status === 'archived') {
        // Show archived state UI
        setIsArchived(true);
      }
    }
  )
  .subscribe();
```

### Archived State UI

When a suggestion is archived, the suggestion screen should show:

```typescript
const ArchivedBanner = ({ suggestionWhat }: { suggestionWhat: string }) => (
  <View style={styles.archivedBanner}>
    <Text style={styles.archivedText}>
      "{suggestionWhat}" expired without enough commitment.
    </Text>
    <TouchableOpacity onPress={regenerateSuggestion}>
      <Text style={styles.regenerateLink}>Generate a new suggestion</Text>
    </TouchableOpacity>
    <TouchableOpacity onPress={viewArchive}>
      <Text style={styles.archiveLink}>View plans you never took</Text>
    </TouchableOpacity>
  </View>
);
```

### Timeline of Suggestion Lifecycle

```
T+0h     Suggestion created (status: 'active')
T+72h    Decay check: if 0 "in" votes, send reminder notification (Story 5.3)
T+96h    Archive check: if <3 "in" votes, archive (this story)
```

### Querying Archived Suggestions (for Story 7.6)

Archived suggestions are preserved with their full `suggestion_data`, including the `_archived_at` timestamp and `_final_in_count`. Story 7.6 will query:

```typescript
const { data: archivedSuggestions } = await supabase
  .from('suggestions')
  .select('*')
  .eq('board_id', boardId)
  .eq('status', 'archived')
  .order('created_at', { ascending: false });
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/suggestion/ArchivedBanner.tsx` | UI banner displayed when a suggestion has been archived, with regenerate and archive links |

### Modify

| File | Change |
|------|--------|
| `supabase/functions/decay-check/index.ts` | Add archive logic for suggestions older than 96 hours with <3 "in" commitments |
| `app/(tabs)/suggestion/[id].tsx` | Handle archived suggestion status -- show ArchivedBanner, hide vote buttons |
| `lib/stores/commitment-store.ts` or `lib/stores/board-store.ts` | Subscribe to suggestion status updates via Realtime |

## Definition of Done

- [ ] Suggestions active for 96+ hours with fewer than 3 "in" commitments are archived
- [ ] Suggestion `status` updated from 'active' to 'archived' in the database
- [ ] Archived suggestions retain all `suggestion_data` for future revival (Story 7.6)
- [ ] `_archived_at`, `_archived_reason`, and `_final_in_count` metadata added to suggestion_data
- [ ] Suggestions with 3+ "in" commitments are NOT archived regardless of age
- [ ] Already-archived suggestions are not processed again (idempotent)
- [ ] Client UI reacts to archived status -- hides vote buttons, shows ArchivedBanner
- [ ] ArchivedBanner shows "Generate new suggestion" and "View plans you never took" links
- [ ] Realtime subscription on suggestion status updates works correctly
- [ ] Archive check runs as part of the decay-check cron (no separate cron needed)
- [ ] Edge Function handles edge cases: suggestion with no commitments at all, board with 0 members
