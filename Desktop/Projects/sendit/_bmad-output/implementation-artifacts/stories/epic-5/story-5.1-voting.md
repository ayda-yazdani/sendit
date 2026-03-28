# Story 5.1: In/Maybe/Out Voting with Live Tally

## Description

As a board member,
I want to mark myself as In, Maybe, or Out on a suggestion,
So that the group can see who's committed and social pressure drives follow-through.

## Status

- **Epic:** Commitment & Social Pressure
- **Priority:** P0
- **Branch:** `feature/commitment`
- **Assignee:** Person A

## Acceptance Criteria

**Given** a suggestion is active on the board (status = 'active')
**When** the user views the suggestion screen
**Then** three buttons are displayed: "In" (green), "Maybe" (yellow), "Out" (grey)
**And** the user's current vote (if any) is visually highlighted

**Given** the user taps one of the commitment buttons
**When** the button is pressed
**Then** a commitment row is upserted into the `commitments` table with the user's `member_id`, the `suggestion_id`, and the selected `status` ('in', 'maybe', or 'out')
**And** the button state updates immediately (optimistic UI)
**And** the user can change their vote at any time by tapping a different button

**Given** multiple members have voted on a suggestion
**When** any member views the suggestion screen
**Then** a live tally is displayed showing the count for each status (e.g., "3 In / 1 Maybe / 1 Out")
**And** each board member's avatar is displayed in a row with color-coded status:
  - Green ring = "in"
  - Yellow ring = "maybe"
  - Grey ring = "out" or no vote yet (pending)

**Given** a member changes their vote
**When** the commitment row is updated in Supabase
**Then** all other connected members see the tally and avatar status update within 1 second via Realtime subscription (NFR18)

## Technical Context

### Relevant Schema

```sql
commitments (
  id uuid PK DEFAULT gen_random_uuid(),
  suggestion_id uuid FK REFERENCES suggestions(id),
  member_id uuid FK REFERENCES members(id),
  status text CHECK (status IN ('in', 'maybe', 'out')),
  receipt_url text,
  updated_at timestamptz DEFAULT now(),
  UNIQUE(suggestion_id, member_id)
)
```

The `UNIQUE(suggestion_id, member_id)` constraint enables upsert behavior -- a member can only have one commitment per suggestion, and changing their vote updates the existing row.

### Architecture References

- **Screen:** `app/(tabs)/suggestion/[id].tsx` -- Suggestion detail screen where voting occurs
- **Store:** `lib/stores/board-store.ts` -- May need extension for commitment state, or create a new `commitment-store.ts`
- **Realtime Hook:** `lib/hooks/use-realtime.ts` -- Subscribe to `commitments` table changes filtered by `suggestion_id`
- **Components:** `components/commitment/VoteButtons.tsx`, `components/commitment/CommitmentTally.tsx`, `components/commitment/MemberAvatarRow.tsx`

### Dependencies

- **Requires:** Active suggestions exist in the `suggestions` table (Epic 4 complete)
- **Requires:** Member data available (Epic 1 -- board membership)
- **Requires:** Supabase Realtime enabled on the `commitments` table
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

## Implementation Notes

### Upsert Logic

Use Supabase's `upsert` with the `onConflict` option targeting the unique constraint:

```typescript
const { data, error } = await supabase
  .from('commitments')
  .upsert(
    {
      suggestion_id: suggestionId,
      member_id: currentMemberId,
      status: selectedStatus, // 'in' | 'maybe' | 'out'
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'suggestion_id,member_id' }
  )
  .select()
  .single();
```

### Realtime Subscription

Subscribe to commitment changes for the active suggestion:

```typescript
const channel = supabase
  .channel(`commitments:${suggestionId}`)
  .on(
    'postgres_changes',
    {
      event: '*', // INSERT and UPDATE
      schema: 'public',
      table: 'commitments',
      filter: `suggestion_id=eq.${suggestionId}`,
    },
    (payload) => {
      // Update local state with new/changed commitment
      updateCommitment(payload.new as Commitment);
    }
  )
  .subscribe();
```

### Optimistic UI Pattern

1. When user taps a vote button, immediately update local Zustand state
2. Fire the Supabase upsert in the background
3. If the upsert fails, revert the local state and show an error toast
4. Realtime subscription will confirm the update for all other clients

### Avatar Status Colors

```typescript
const STATUS_COLORS = {
  in: '#22C55E',      // green-500
  maybe: '#EAB308',   // yellow-500
  out: '#9CA3AF',     // grey-400
  pending: '#D1D5DB', // grey-300 (no vote yet)
} as const;
```

### Zustand Store Extension

Create a commitment store or extend the board store:

```typescript
interface CommitmentState {
  commitments: Record<string, Commitment[]>; // keyed by suggestion_id
  myVote: (suggestionId: string) => 'in' | 'maybe' | 'out' | null;
  setVote: (suggestionId: string, status: string) => Promise<void>;
  subscribeToCommitments: (suggestionId: string) => () => void;
}
```

### Loading Members for Avatar Row

Fetch all board members and join with their commitment status:

```typescript
// Fetch all members of the board
const { data: members } = await supabase
  .from('members')
  .select('id, display_name, avatar_url')
  .eq('board_id', boardId);

// Fetch all commitments for this suggestion
const { data: commitments } = await supabase
  .from('commitments')
  .select('member_id, status')
  .eq('suggestion_id', suggestionId);

// Merge: each member gets their status or 'pending'
const memberStatuses = members.map((m) => ({
  ...m,
  commitmentStatus: commitments.find((c) => c.member_id === m.id)?.status ?? 'pending',
}));
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/commitment/VoteButtons.tsx` | Three-button voting UI (In/Maybe/Out) with active state highlighting |
| `components/commitment/CommitmentTally.tsx` | Displays count per status (e.g., "3 In / 1 Maybe / 1 Out") |
| `components/commitment/MemberAvatarRow.tsx` | Horizontal row of member avatars with color-coded rings |
| `lib/stores/commitment-store.ts` | Zustand store for commitment state, upsert logic, realtime subscription |
| `lib/hooks/use-commitments.ts` | Hook wrapping commitment store for use in suggestion screen |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/suggestion/[id].tsx` | Import and render VoteButtons, CommitmentTally, MemberAvatarRow below the suggestion card |
| `lib/supabase.ts` | Ensure Realtime is enabled for commitments table (may already be configured) |

## Definition of Done

- [ ] User can tap In, Maybe, or Out on an active suggestion
- [ ] Vote is persisted via upsert to the `commitments` table
- [ ] Changing vote updates the existing row (does not create duplicates)
- [ ] Live tally displays correct counts for each status
- [ ] Member avatars display with correct color-coded rings (green/yellow/grey)
- [ ] Members without a vote show as "pending" (grey)
- [ ] Realtime subscription updates all connected clients within 1 second of a vote change
- [ ] Optimistic UI updates the local user's vote instantly before server confirmation
- [ ] Error state: if upsert fails, local state reverts and error toast is shown
- [ ] Component renders correctly with 1 member and with 10+ members
- [ ] No duplicate Realtime subscriptions (cleanup on unmount)
