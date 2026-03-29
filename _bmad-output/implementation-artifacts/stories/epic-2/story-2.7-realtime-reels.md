# Story 2.7: Real-Time Reel Updates

## Description

As a board member,
I want to see new reels appear on the board instantly when someone shares,
So that the board feels alive and collaborative.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/ai-extraction`
- **Assignee:** Person C (client/UI)
- **FRs Covered:** FR12
- **Depends On:** Story 2.1 (reel creation), Story 2.6 (extraction card UI), Epic 1 (Supabase Realtime enabled)

## Acceptance Criteria

**Given** the user is viewing a board detail screen
**When** another member adds a reel to the same board (via paste URL or share sheet)
**Then** the new reel row appears in the reel list within 1 second (NFR2)
**And** the reel initially shows as a skeleton card (extraction in progress)
**And** when extraction completes and `extraction_data` is updated, the card transitions to the full extraction card

**Given** a reel's `extraction_data` is updated by the Edge Function
**When** the Supabase Realtime subscription fires an UPDATE event
**Then** the extraction card re-renders with the new extraction_data and classification
**And** no full page refresh is needed

**Given** the user's WebSocket connection drops
**When** the connection is re-established
**Then** any reels added while disconnected are fetched and displayed (NFR17)
**And** the user does not see stale data

**Given** multiple members add reels simultaneously
**When** INSERT events arrive in rapid succession
**Then** all reels appear in the correct order (by created_at)
**And** no duplicates are displayed

**Given** the user navigates away from the board detail screen
**When** they leave the screen
**Then** the Realtime subscription is cleaned up (unsubscribed)
**And** no memory leaks from lingering subscriptions

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK -> boards(id),
  added_by uuid FK -> members(id),
  url text,
  platform text,
  extraction_data jsonb,
  classification text,
  created_at timestamptz,
  UNIQUE(board_id, url)
)
```

### Supabase Realtime Configuration

Supabase Realtime must be enabled on the `reels` table. This is configured in the Supabase dashboard under Database > Replication. The `reels` table must be added to the publication.

Realtime events supported:
- `INSERT` — new reel added to board
- `UPDATE` — extraction_data or classification updated on existing reel

### Architecture References

- **Realtime hook:** `lib/hooks/use-realtime.ts` — generic Realtime subscription hook
- **Board store:** `lib/stores/board-store.ts` — manages reel state for the active board
- **Board detail screen:** `app/(tabs)/board/[id].tsx` — subscribes to reels for the current board
- **Supabase client:** `lib/supabase.ts` — initialized with Realtime enabled by default

### Dependencies

- Story 2.1 (reel creation and board store)
- Story 2.6 (ExtractionCard and ExtractionCardSkeleton components)
- Supabase Realtime must be enabled on the `reels` table
- Epic 1 must be complete (Supabase client initialized)

## Implementation Notes

### 1. Generic Realtime Hook

Create a reusable hook for Supabase Realtime subscriptions. This hook will be used by multiple features (reels, commitments, taste profiles).

**File:** `lib/hooks/use-realtime.ts`

```typescript
import { useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import type { RealtimeChannel, RealtimePostgresChangesPayload } from '@supabase/supabase-js';

type PostgresChangeEvent = 'INSERT' | 'UPDATE' | 'DELETE';

interface UseRealtimeOptions<T extends Record<string, unknown>> {
  table: string;
  event?: PostgresChangeEvent | '*';
  filter?: string;  // e.g., 'board_id=eq.uuid-here'
  onInsert?: (payload: T) => void;
  onUpdate?: (payload: T) => void;
  onDelete?: (payload: { old_record: T }) => void;
  enabled?: boolean;
}

export function useRealtime<T extends Record<string, unknown>>({
  table,
  event = '*',
  filter,
  onInsert,
  onUpdate,
  onDelete,
  enabled = true,
}: UseRealtimeOptions<T>) {
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const channelName = `${table}:${filter || 'all'}:${Date.now()}`;

    const channelConfig: Record<string, unknown> = {
      event,
      schema: 'public',
      table,
    };

    if (filter) {
      channelConfig.filter = filter;
    }

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes' as any,
        channelConfig,
        (payload: RealtimePostgresChangesPayload<T>) => {
          switch (payload.eventType) {
            case 'INSERT':
              if (onInsert) onInsert(payload.new as T);
              break;
            case 'UPDATE':
              if (onUpdate) onUpdate(payload.new as T);
              break;
            case 'DELETE':
              if (onDelete) onDelete({ old_record: payload.old as T });
              break;
          }
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log(`Realtime subscribed: ${table} (${filter || 'all'})`);
        }
        if (status === 'CHANNEL_ERROR') {
          console.warn(`Realtime error on ${table}, will auto-reconnect`);
        }
      });

    channelRef.current = channel;

    // Cleanup on unmount or dependency change
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [table, event, filter, enabled]);
}
```

### 2. Board-Specific Reels Hook

Create a hook that manages reel state for a specific board, combining initial fetch + Realtime updates.

**File:** `lib/hooks/use-board-reels.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { useRealtime } from './use-realtime';

interface Reel {
  id: string;
  board_id: string;
  added_by: string;
  url: string;
  platform: string;
  extraction_data: Record<string, unknown> | null;
  classification: string | null;
  created_at: string;
}

export function useBoardReels(boardId: string | undefined) {
  const [reels, setReels] = useState<Reel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial fetch
  useEffect(() => {
    if (!boardId) return;

    async function fetchReels() {
      setLoading(true);
      const { data, error: fetchError } = await supabase
        .from('reels')
        .select('*')
        .eq('board_id', boardId)
        .order('created_at', { ascending: false });

      if (fetchError) {
        setError(fetchError.message);
      } else {
        setReels(data || []);
      }
      setLoading(false);
    }

    fetchReels();
  }, [boardId]);

  // Handle new reel inserted
  const handleInsert = useCallback((newReel: Reel) => {
    setReels((prev) => {
      // Prevent duplicates
      if (prev.some((r) => r.id === newReel.id)) return prev;
      // Add to the beginning (newest first)
      return [newReel, ...prev];
    });
  }, []);

  // Handle reel updated (extraction_data populated)
  const handleUpdate = useCallback((updatedReel: Reel) => {
    setReels((prev) =>
      prev.map((r) => (r.id === updatedReel.id ? updatedReel : r))
    );
  }, []);

  // Subscribe to Realtime changes
  useRealtime<Reel>({
    table: 'reels',
    filter: boardId ? `board_id=eq.${boardId}` : undefined,
    onInsert: handleInsert,
    onUpdate: handleUpdate,
    enabled: !!boardId,
  });

  return { reels, loading, error };
}
```

### 3. Board Detail Screen Integration

Update the board detail screen to use the `useBoardReels` hook:

**File:** `app/(tabs)/board/[id].tsx` (modifications)

```typescript
import { useBoardReels } from '@/lib/hooks/use-board-reels';
import { ExtractionCard } from '@/components/extraction/ExtractionCard';

export default function BoardDetailScreen() {
  const { id: boardId } = useLocalSearchParams<{ id: string }>();
  const { reels, loading, error } = useBoardReels(boardId);

  if (loading) {
    return <LoadingView />;
  }

  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={reels}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ExtractionCard reel={item} />}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: 100 }}
        ListEmptyComponent={
          <EmptyState message="No reels yet. Paste a link to get started!" />
        }
      />
      <UrlInput boardId={boardId} />
    </View>
  );
}
```

### 4. Reconnection and Missed Updates

Supabase Realtime automatically reconnects when the WebSocket connection drops. However, events that occurred during the disconnection are missed. To handle this:

```typescript
// In use-board-reels.ts, add reconnection logic:

useEffect(() => {
  if (!boardId) return;

  // Listen for app state changes (background -> foreground)
  const subscription = AppState.addEventListener('change', (nextState) => {
    if (nextState === 'active') {
      // Re-fetch reels when app returns to foreground
      refreshReels();
    }
  });

  return () => subscription.remove();
}, [boardId]);

const refreshReels = useCallback(async () => {
  if (!boardId) return;

  const { data } = await supabase
    .from('reels')
    .select('*')
    .eq('board_id', boardId)
    .order('created_at', { ascending: false });

  if (data) {
    setReels(data);
  }
}, [boardId]);
```

### 5. Optimistic Updates

When the current user submits a URL (Story 2.1), the reel should appear immediately without waiting for the Realtime event. This is an optimistic update:

```typescript
// In the URL submission handler (UrlInput or board-store):
async function handleSubmitUrl(url: string, boardId: string, memberId: string) {
  const platform = detectPlatform(url);

  // Optimistic: add a temporary reel to state immediately
  const tempReel: Reel = {
    id: `temp-${Date.now()}`,
    board_id: boardId,
    added_by: memberId,
    url: url.trim(),
    platform,
    extraction_data: null,
    classification: null,
    created_at: new Date().toISOString(),
  };

  // Add to local state immediately (shows skeleton card)
  setReels((prev) => [tempReel, ...prev]);

  // Insert into Supabase
  const { data: reel, error } = await supabase
    .from('reels')
    .insert({
      board_id: boardId,
      added_by: memberId,
      url: url.trim(),
      platform,
    })
    .select()
    .single();

  if (error) {
    // Remove optimistic reel on failure
    setReels((prev) => prev.filter((r) => r.id !== tempReel.id));
    throw error;
  }

  // Replace temp reel with real reel (will also be received via Realtime, deduped)
  setReels((prev) =>
    prev.map((r) => (r.id === tempReel.id ? reel : r))
  );

  // Trigger extraction
  invokeExtraction(reel.id, url).catch(console.error);
}
```

### 6. Supabase Realtime Configuration

Ensure the `reels` table is added to the Supabase Realtime publication. This can be done in the Supabase dashboard:

1. Go to Database > Replication
2. Under "Realtime" publication, add the `reels` table
3. Enable INSERT and UPDATE events

Or via SQL:

```sql
-- Enable Realtime on the reels table
ALTER PUBLICATION supabase_realtime ADD TABLE reels;
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `lib/hooks/use-realtime.ts` | Generic Supabase Realtime subscription hook |
| `lib/hooks/use-board-reels.ts` | Board-specific reels hook (fetch + Realtime + optimistic updates) |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Use `useBoardReels` hook, render FlatList with ExtractionCards, handle empty state |
| `components/board/UrlInput.tsx` | Add optimistic update logic when submitting a URL |

## Testing Guidance

### Multi-Device Testing

This story requires testing with two devices/simulators simultaneously:

1. **Setup:** Open the same board on two devices (or two simulator instances)
2. **Test INSERT:** On Device A, paste a URL. Verify the skeleton card appears on Device B within 1 second.
3. **Test UPDATE:** After extraction completes on Device A's reel, verify the full extraction card appears on Device B (replaces skeleton).
4. **Test rapid inserts:** On Device A, submit 3 URLs quickly. Verify all 3 appear on Device B in correct order.
5. **Test deduplication:** Verify no duplicate cards appear on either device.

### Reconnection Testing

1. On Device A, put the app in the background for 10 seconds
2. On Device B, add a reel during that time
3. Bring Device A back to foreground
4. Verify the new reel appears after reconnection

### Manual Verification

- [ ] Initial load: Board detail screen fetches and displays existing reels
- [ ] New reel INSERT: appears on all connected clients within 1 second
- [ ] Extraction UPDATE: skeleton card transitions to full extraction card on all clients
- [ ] Optimistic update: submitter sees skeleton card immediately (before Supabase insert completes)
- [ ] Duplicate prevention: same reel does not appear twice
- [ ] Cleanup: navigating away from board detail screen unsubscribes from Realtime channel
- [ ] Empty state: "No reels yet" message when board has no reels

### Supabase Dashboard Verification

Monitor Realtime connections in the Supabase dashboard:
1. Go to Database > Replication > Realtime
2. Verify active subscriptions for the reels table
3. Verify message count increases when reels are added

## Definition of Done

- [ ] `lib/hooks/use-realtime.ts` created — generic Realtime subscription hook
- [ ] `lib/hooks/use-board-reels.ts` created — combines initial fetch, Realtime INSERT/UPDATE, optimistic updates
- [ ] Board detail screen uses `useBoardReels` hook and renders FlatList of ExtractionCards
- [ ] New reel INSERTs from other members appear within 1 second (NFR2)
- [ ] Extraction UPDATE events cause skeleton cards to transition to full extraction cards
- [ ] Optimistic updates: submitter sees skeleton card immediately
- [ ] Duplicate prevention: same reel never appears twice in the list
- [ ] Realtime subscription is cleaned up when navigating away from the board screen
- [ ] App foreground recovery: re-fetches reels when app returns from background
- [ ] Empty state shown when board has no reels
- [ ] Supabase Realtime enabled on `reels` table (publication configured)
- [ ] Tested on two devices simultaneously with INSERT and UPDATE events
- [ ] No memory leaks from lingering subscriptions
