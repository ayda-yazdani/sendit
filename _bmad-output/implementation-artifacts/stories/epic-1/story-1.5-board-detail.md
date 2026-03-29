# Story 1.5: Board Detail Screen

## Description
As a user, I want to view a board's details including its name and a live list of members with their avatars and display names, so that I can see who is in my board and know when new members join in real time.

## Status
- Epic: Epic 1 - Board Creation & Onboarding
- Priority: P0
- Branch: feature/board-creation
- Assignee: TBD (pick up from sprint board)

## Acceptance Criteria

### AC 1: Board detail loads on navigation
- **Given** the user taps a board card on the board list screen
- **When** the board detail screen (`app/(tabs)/board/[id].tsx`) mounts
- **Then** the board name is shown in the header/title
- **And** the full member list for that board is fetched from Supabase
- **And** the member list is stored in the board store's `activeBoardMembers` array

### AC 2: Member list displays correctly
- **Given** the board's members have been fetched
- **When** the data is available
- **Then** each member is shown in a list with:
  - An avatar circle (image if `avatar_url` exists, else first letter of `display_name` on colored background)
  - Their `display_name`
  - A "(You)" label next to the current user's own member entry
- **And** members are ordered alphabetically by `display_name`

### AC 3: Real-time member updates via Supabase Realtime
- **Given** the user is viewing the board detail screen
- **When** a new member joins the board (another user joins via code or deep link)
- **Then** the new member appears in the member list automatically without a manual refresh
- **And** when a member is removed, they disappear from the list automatically

### AC 4: Board metadata section
- **Given** the board detail screen is loaded
- **When** the data is available
- **Then** the screen displays:
  - Board name as the screen title
  - Join code with a copy button (tap copies to clipboard)
  - Member count (e.g., "4 members")
  - A "Share Invite" button that shares the deep link via the native share sheet

### AC 5: Loading state
- **Given** the board detail screen is navigated to
- **When** the member list is being fetched
- **Then** a loading indicator is shown in the member list area
- **And** the board name from the store's `activeBoard` is displayed immediately (already available from the board list)

### AC 6: Error state
- **Given** the member fetch or Realtime subscription fails
- **When** the error is caught
- **Then** an error message is shown with a "Retry" button
- **And** the Realtime subscription attempts to reconnect

### AC 7: Realtime subscription cleanup
- **Given** the user navigates away from the board detail screen
- **When** the screen unmounts
- **Then** the Supabase Realtime channel subscription is unsubscribed and removed
- **And** no memory leaks occur from dangling subscriptions

### AC 8: Placeholder sections for future epics
- **Given** the board detail screen is loaded
- **When** the user scrolls
- **Then** placeholder sections are visible for:
  - "Taste Profile" (Epic 3) - shows a locked/coming-soon card
  - "Suggestions" (Epic 4) - shows a locked/coming-soon card
  - "Reels" (Epic 2) - shows a locked/coming-soon card
- **And** these placeholders communicate that more features are coming

## Technical Context

### Relevant Schema

```sql
boards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  join_code text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now()
)

members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id uuid REFERENCES boards(id) ON DELETE CASCADE NOT NULL,
  display_name text NOT NULL,
  device_id text NOT NULL,
  google_id text,
  avatar_url text,
  push_token text,
  UNIQUE(board_id, device_id)
)
```

### Architecture References

**Files involved:**
```
lib/
  stores/
    board-store.ts                  # MODIFY - add fetchBoardMembers, update activeBoardMembers
  hooks/
    use-realtime.ts                 # MODIFY - implement Realtime subscription hook
    use-board.ts                    # MODIFY - add useBoardDetail hook
components/
  board/
    BoardHeader.tsx                 # NEW - board name, join code, share invite, member count
    MemberList.tsx                  # NEW - full member list with avatars and names
    MemberRow.tsx                   # NEW - single member row component
    ComingSoonCard.tsx              # NEW - placeholder for future feature sections
app/
  (tabs)/
    board/
      [id].tsx                      # MODIFY - replace placeholder with full board detail UI
```

**Patterns to follow:**
- Realtime hook wraps `supabase.channel()` and cleans up on unmount
- Board detail screen uses the `useLocalSearchParams()` hook to get the board `id`
- Member list uses `FlatList` for performance
- The "(You)" label is determined by matching `member.device_id` against the auth store's `deviceId`

### Dependencies

- Story 1.1 must be complete (auth store, Supabase client)
- Story 1.2 must be complete (board store with types, shared components)
- Story 1.4 must be complete (board list navigation, `setActiveBoard`, `MemberAvatars`)
- Supabase Realtime must be enabled on the `members` table (it is enabled by default for all tables)

## Implementation Notes

### Realtime hook (`lib/hooks/use-realtime.ts`)
This is a general-purpose hook for subscribing to Supabase Realtime Postgres changes:

```typescript
import { useEffect, useRef } from 'react';
import { supabase } from '../supabase';
import type { RealtimeChannel, RealtimePostgresChangesPayload } from '@supabase/supabase-js';

interface UseRealtimeOptions {
  table: string;
  schema?: string;
  event?: 'INSERT' | 'UPDATE' | 'DELETE' | '*';
  filter?: string;
  onInsert?: (payload: RealtimePostgresChangesPayload<any>) => void;
  onUpdate?: (payload: RealtimePostgresChangesPayload<any>) => void;
  onDelete?: (payload: RealtimePostgresChangesPayload<any>) => void;
  enabled?: boolean;
}

export function useRealtime({
  table,
  schema = 'public',
  event = '*',
  filter,
  onInsert,
  onUpdate,
  onDelete,
  enabled = true,
}: UseRealtimeOptions) {
  const channelRef = useRef<RealtimeChannel | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const channelName = `${table}-${filter || 'all'}-${Date.now()}`;

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event,
          schema,
          table,
          filter,
        },
        (payload) => {
          if (payload.eventType === 'INSERT' && onInsert) {
            onInsert(payload);
          } else if (payload.eventType === 'UPDATE' && onUpdate) {
            onUpdate(payload);
          } else if (payload.eventType === 'DELETE' && onDelete) {
            onDelete(payload);
          }
        }
      )
      .subscribe((status) => {
        if (status === 'CHANNEL_ERROR') {
          console.error(`Realtime subscription error for ${table}`);
        }
      });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [table, filter, enabled]);
}
```

**Key details:**
- Uses `useRef` to hold the channel reference for cleanup
- The `filter` parameter uses PostgREST syntax, e.g., `board_id=eq.${boardId}`
- `supabase.removeChannel()` is used for cleanup (not just `unsubscribe()`) to fully clean up the channel
- The channel name includes a timestamp to avoid name collisions when re-subscribing
- The `enabled` flag allows the hook to be conditionally activated

### Board store additions
Add to `lib/stores/board-store.ts`:

```typescript
// Add to BoardState interface:
fetchBoardMembers: (boardId: string) => Promise<void>;
addMember: (member: Member) => void;
removeMember: (memberId: string) => void;
updateMember: (member: Member) => void;

// Implementations:
fetchBoardMembers: async (boardId: string) => {
  const { data: members, error } = await supabase
    .from('members')
    .select('*')
    .eq('board_id', boardId)
    .order('display_name', { ascending: true });

  if (error) {
    console.error('Failed to fetch board members:', error);
    set({ error: error.message });
    return;
  }

  set({ activeBoardMembers: members || [] });
},

addMember: (member: Member) => {
  set((state) => {
    // Avoid duplicates
    if (state.activeBoardMembers.some((m) => m.id === member.id)) {
      return state;
    }
    const updated = [...state.activeBoardMembers, member].sort((a, b) =>
      a.display_name.localeCompare(b.display_name)
    );
    return { activeBoardMembers: updated };
  });
},

removeMember: (memberId: string) => {
  set((state) => ({
    activeBoardMembers: state.activeBoardMembers.filter((m) => m.id !== memberId),
  }));
},

updateMember: (member: Member) => {
  set((state) => ({
    activeBoardMembers: state.activeBoardMembers.map((m) =>
      m.id === member.id ? { ...m, ...member } : m
    ),
  }));
},
```

### useBoardDetail hook (`lib/hooks/use-board.ts`)
Add alongside the existing `useBoardList`:

```typescript
import { useRealtime } from './use-realtime';

export function useBoardDetail(boardId: string) {
  const { activeBoard, activeBoardMembers, fetchBoardMembers, addMember, removeMember, updateMember } =
    useBoardStore();
  const { deviceId } = useAuthStore();

  // Fetch members on mount
  useEffect(() => {
    if (boardId) {
      fetchBoardMembers(boardId);
    }
  }, [boardId]);

  // Subscribe to realtime member changes
  useRealtime({
    table: 'members',
    filter: `board_id=eq.${boardId}`,
    enabled: !!boardId,
    onInsert: (payload) => {
      addMember(payload.new as Member);
    },
    onDelete: (payload) => {
      removeMember(payload.old.id);
    },
    onUpdate: (payload) => {
      updateMember(payload.new as Member);
    },
  });

  return {
    board: activeBoard,
    members: activeBoardMembers,
    currentMember: activeBoardMembers.find((m) => m.device_id === deviceId),
    memberCount: activeBoardMembers.length,
    isLoading: useBoardStore((s) => s.isLoading),
    error: useBoardStore((s) => s.error),
  };
}
```

### Board detail screen (`app/(tabs)/board/[id].tsx`)
```typescript
import { useLocalSearchParams } from 'expo-router';
import { View, ScrollView, StyleSheet } from 'react-native';
import { BoardHeader } from '../../../components/board/BoardHeader';
import { MemberList } from '../../../components/board/MemberList';
import { ComingSoonCard } from '../../../components/board/ComingSoonCard';
import { useBoardDetail } from '../../../lib/hooks/use-board';

export default function BoardDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { board, members, currentMember, memberCount, isLoading, error } = useBoardDetail(id);

  return (
    <ScrollView style={styles.container}>
      <BoardHeader
        board={board}
        memberCount={memberCount}
      />
      <MemberList
        members={members}
        currentDeviceId={currentMember?.device_id}
        isLoading={isLoading}
      />
      <ComingSoonCard title="Reels" description="Share and rate Instagram Reels together" icon="play-circle-outline" />
      <ComingSoonCard title="Taste Profile" description="See how your tastes compare" icon="analytics-outline" />
      <ComingSoonCard title="Suggestions" description="Get personalized content suggestions" icon="bulb-outline" />
    </ScrollView>
  );
}
```

### BoardHeader component (`components/board/BoardHeader.tsx`)
**Props:**
```typescript
interface BoardHeaderProps {
  board: Board | null;
  memberCount: number;
}
```

**Layout:**
```
+----------------------------------------------+
|  Board Name                                  |
|  4 members                                   |
|                                              |
|  Invite Code: ABC123  [Copy] [Share]         |
+----------------------------------------------+
```

**Features:**
- Board name: large text (24px), bold
- Member count: secondary text (16px), gray
- Join code: monospace, with tap-to-copy via `expo-clipboard`
- "Share Invite" button: uses `Share.share()` from React Native:
  ```typescript
  import { Share } from 'react-native';
  const shareInvite = () => {
    Share.share({
      message: `Join my board "${board.name}" on Sendit! Use code ${board.join_code} or tap: senditapp://join/${board.join_code}`,
    });
  };
  ```

### MemberList component (`components/board/MemberList.tsx`)
**Props:**
```typescript
interface MemberListProps {
  members: Member[];
  currentDeviceId: string | undefined;
  isLoading: boolean;
}
```

- Section header: "Members" with count
- Uses `FlatList` with `scrollEnabled={false}` (nested inside ScrollView)
- Each item renders a `MemberRow`

### MemberRow component (`components/board/MemberRow.tsx`)
**Props:**
```typescript
interface MemberRowProps {
  member: Member;
  isCurrentUser: boolean;
}
```

**Layout:**
```
+----------------------------------------------+
|  [Avatar]  Display Name            (You)     |
+----------------------------------------------+
```

- Avatar: 40px circle. If `avatar_url` is set, use `Image`. Otherwise, show colored circle with initial.
- Use the same deterministic color palette from `MemberAvatars` (Story 1.4).
- Display name: 16px, medium weight
- "(You)" label: small, colored badge/text, only shown when `isCurrentUser` is true

### ComingSoonCard component (`components/board/ComingSoonCard.tsx`)
**Props:**
```typescript
interface ComingSoonCardProps {
  title: string;
  description: string;
  icon: string; // Ionicons name
}
```

**Layout:**
```
+----------------------------------------------+
|  [Icon]  Title                               |
|          Description text here               |
|          Coming Soon                         |
+----------------------------------------------+
```

- Card with dashed border or muted/semi-transparent styling to indicate it's not active yet
- Uses `Ionicons` from `@expo/vector-icons`
- "Coming Soon" label in a subtle chip/badge

### Supabase Realtime requirements
Supabase Realtime is enabled by default for all tables. However, you must ensure:
1. The Supabase project has Realtime enabled (it should be by default)
2. The `members` table has Realtime enabled in the Supabase dashboard (Table Editor > members > enable Realtime, or it may already be on)
3. The filter syntax `board_id=eq.${boardId}` is correct PostgREST filter format for Realtime

If Realtime is not receiving events, check:
- Supabase dashboard > Database > Replication > ensure `members` table is in the publication
- The Realtime filter must match exactly one column with `eq` operator

### Navigation configuration
The route `app/(tabs)/board/[id].tsx` is inside the tabs group. Expo Router will:
- Show the tab bar at the bottom
- The board detail screen replaces the content area

If you want the board detail to hide the tab bar, you could move it outside `(tabs)` as a stack screen. For MVP, keeping it inside tabs is fine since users may want to switch between boards and profile.

Alternatively, configure the tab bar to hide on the board detail screen:
```typescript
// In app/(tabs)/_layout.tsx, use the tabBarStyle to conditionally hide
// Or in board/[id].tsx, use the options to hide the tab bar:
import { Stack } from 'expo-router';
// This requires the route to be a Stack screen, not just a tab content
```

For simplicity in this story, keep the tab bar visible. This can be refined in a polish pass.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| MODIFY | `sendit-app/lib/stores/board-store.ts` | Add `fetchBoardMembers`, `addMember`, `removeMember`, `updateMember` methods |
| MODIFY | `sendit-app/lib/hooks/use-realtime.ts` | Replace placeholder with full Realtime subscription hook |
| MODIFY | `sendit-app/lib/hooks/use-board.ts` | Add `useBoardDetail` hook alongside `useBoardList` |
| CREATE | `sendit-app/components/board/BoardHeader.tsx` | Board name, join code, share invite, member count |
| CREATE | `sendit-app/components/board/MemberList.tsx` | FlatList of member rows |
| CREATE | `sendit-app/components/board/MemberRow.tsx` | Single member row with avatar and name |
| CREATE | `sendit-app/components/board/ComingSoonCard.tsx` | Placeholder card for future features |
| MODIFY | `sendit-app/app/(tabs)/board/[id].tsx` | Replace placeholder with full board detail screen |

## Definition of Done

- [ ] Navigating to a board from the board list shows the board detail screen with the correct board name
- [ ] The full member list is fetched from Supabase and displayed with avatars and display names
- [ ] Members are sorted alphabetically by display name
- [ ] The current user's entry shows a "(You)" label
- [ ] Avatar circles show the member's image (if `avatar_url` exists) or their initial on a colored background
- [ ] The join code is displayed with a working copy-to-clipboard button
- [ ] The "Share Invite" button opens the native share sheet with the deep link
- [ ] Member count is displayed and accurate
- [ ] Realtime subscription is active: when a new member joins on another device, they appear in the list automatically
- [ ] Realtime subscription is cleaned up when navigating away (no console errors, no memory leaks)
- [ ] Realtime handles INSERT, DELETE, and UPDATE events on the members table
- [ ] Loading state is shown while members are being fetched
- [ ] Error state is shown if the fetch fails, with a retry option
- [ ] Placeholder "Coming Soon" cards are shown for Reels, Taste Profile, and Suggestions
- [ ] `useRealtime` hook is generic and reusable for any table/filter combination
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Manually tested: board detail loads correctly with 1, 3, and 10+ members
- [ ] Manually tested: open board detail on two devices, join from one, see update on the other
- [ ] Manually tested: navigate away and back, verify no duplicate subscriptions or stale data
- [ ] Manually tested: copy join code and share invite buttons work correctly
