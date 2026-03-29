# Story 1.4: Board List Screen

## Description
As a user, I want to see a list of all boards I belong to with their names and member counts, so that I can quickly navigate to any of my boards.

## Status
- Epic: Epic 1 - Board Creation & Onboarding
- Priority: P0
- Branch: feature/board-creation
- Assignee: TBD (pick up from sprint board)

## Acceptance Criteria

### AC 1: Boards are fetched on screen load
- **Given** the user opens the app and lands on the board list screen (`app/(tabs)/index.tsx`)
- **When** the screen mounts and the auth store has an initialized `deviceId`
- **Then** the app queries all boards where the user's `device_id` exists in the `members` table
- **And** each board includes a count of its members
- **And** the results are stored in the board store's `boards` array

### AC 2: Boards display as cards
- **Given** the board list has been fetched
- **When** the data is available
- **Then** each board is rendered as a card showing:
  - Board name (primary text, bold)
  - Member count (secondary text, e.g., "4 members")
  - A row of up to 3 member avatar circles (with initials as fallback)
  - The join code displayed subtly (small text, e.g., "Code: ABC123")

### AC 3: Empty state
- **Given** the user has no boards
- **When** the board list screen loads
- **Then** an empty state is displayed with:
  - An illustration or icon
  - Text: "No boards yet"
  - Subtext: "Create a board or join one with a code"
  - Prominent "Create Board" and "Join Board" buttons

### AC 4: Loading state
- **Given** the board list is being fetched
- **When** the request is in progress
- **Then** a loading skeleton or activity indicator is shown
- **And** the loading state is managed via the board store's `isLoading` flag

### AC 5: Pull-to-refresh
- **Given** the user is on the board list screen
- **When** the user pulls down on the list
- **Then** the board list is re-fetched from Supabase
- **And** a refresh indicator is shown during the fetch

### AC 6: Tap navigates to board detail
- **Given** the board list is displayed
- **When** the user taps on a board card
- **Then** the board store's `activeBoard` is set to the tapped board
- **And** the app navigates to `app/(tabs)/board/[id]`

### AC 7: Board list stays current
- **Given** the user creates or joins a board (from Stories 1.2/1.3)
- **When** the user returns to the board list screen
- **Then** the new board appears in the list without requiring a manual refresh
- **And** boards are ordered by most recently created (newest first)

### AC 8: Error state
- **Given** the board list fetch fails (network error, Supabase error)
- **When** the error is caught
- **Then** an error message is displayed with a "Retry" button
- **And** the error state is managed via the board store's `error` flag

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

**Query pattern:** The fetch query must join `boards` through `members` to find boards the current user belongs to. Supabase's PostgREST API supports this via a filtered relation query.

### Architecture References

**Files involved:**
```
lib/
  stores/
    board-store.ts              # MODIFY - implement fetchBoards method
  hooks/
    use-board.ts                # MODIFY - implement useBoard hook for board list data
components/
  board/
    BoardCard.tsx               # NEW - single board card component
    BoardList.tsx               # NEW - FlatList of board cards
    EmptyBoardState.tsx         # NEW - empty state when no boards
    MemberAvatars.tsx           # NEW - row of avatar circles
app/
  (tabs)/
    index.tsx                   # MODIFY - replace placeholder with full board list UI
    _layout.tsx                 # MODIFY - configure tab bar appearance
```

**Patterns to follow:**
- Use `FlatList` for the board list (not `ScrollView`) for performance
- Board cards use `TouchableOpacity` or `Pressable` for tap handling
- Pull-to-refresh uses `FlatList`'s `refreshing` and `onRefresh` props
- Avatar circles show the first letter of each member's display name as fallback
- The tab layout file configures the bottom tab bar icon and title

### Dependencies

- Story 1.1 must be complete (auth store with `deviceId`, Supabase client)
- Story 1.2 must be complete (board store types, `createBoard` method, shared Button/Input)
- Story 1.3 should be complete (joinBoard method populates the boards array)
- `boards` and `members` tables must exist in Supabase (already live)

## Implementation Notes

### Board store `fetchBoards` method
Replace the placeholder `fetchBoards` in `lib/stores/board-store.ts`:

```typescript
fetchBoards: async () => {
  set({ isLoading: true, error: null });

  const { deviceId } = useAuthStore.getState();
  if (!deviceId) {
    set({ isLoading: false, error: 'Device not initialized' });
    return;
  }

  try {
    // Step 1: Get all board_ids where this device is a member
    const { data: memberRows, error: memberError } = await supabase
      .from('members')
      .select('board_id')
      .eq('device_id', deviceId);

    if (memberError) throw memberError;
    if (!memberRows || memberRows.length === 0) {
      set({ boards: [], isLoading: false });
      return;
    }

    const boardIds = memberRows.map((m) => m.board_id);

    // Step 2: Fetch those boards
    const { data: boards, error: boardError } = await supabase
      .from('boards')
      .select('*')
      .in('id', boardIds)
      .order('created_at', { ascending: false });

    if (boardError) throw boardError;

    // Step 3: Fetch member counts and preview members for each board
    const boardsWithMeta = await Promise.all(
      (boards || []).map(async (board) => {
        const { count } = await supabase
          .from('members')
          .select('*', { count: 'exact', head: true })
          .eq('board_id', board.id);

        const { data: previewMembers } = await supabase
          .from('members')
          .select('id, display_name, avatar_url')
          .eq('board_id', board.id)
          .limit(3);

        return {
          ...board,
          memberCount: count || 0,
          previewMembers: previewMembers || [],
        };
      })
    );

    set({ boards: boardsWithMeta, isLoading: false });
  } catch (error: any) {
    set({ isLoading: false, error: error.message || 'Failed to fetch boards' });
  }
},
```

**Note on types:** Extend the `Board` interface to include optional display-only fields:
```typescript
interface Board {
  id: string;
  name: string;
  join_code: string;
  created_at: string;
  memberCount?: number;
  previewMembers?: { id: string; display_name: string; avatar_url: string | null }[];
}
```

### useBoard hook (`lib/hooks/use-board.ts`)
This hook wraps the board store for convenient use in components:

```typescript
import { useEffect } from 'react';
import { useBoardStore } from '../stores/board-store';
import { useAuthStore } from '../stores/auth-store';

export function useBoardList() {
  const { boards, isLoading, error, fetchBoards } = useBoardStore();
  const { isInitialized, deviceId } = useAuthStore();

  useEffect(() => {
    if (isInitialized && deviceId) {
      fetchBoards();
    }
  }, [isInitialized, deviceId]);

  return { boards, isLoading, error, refetch: fetchBoards };
}
```

### BoardCard component (`components/board/BoardCard.tsx`)
**Props:**
```typescript
interface BoardCardProps {
  board: Board;
  onPress: (board: Board) => void;
}
```

**Layout:**
```
+----------------------------------------------+
|  Board Name                        ABC123    |
|  4 members                                   |
|  [A] [B] [C]                                |
+----------------------------------------------+
```

**Styling guidelines:**
- Card: white background, rounded corners (12px), subtle shadow, padding 16px
- Board name: 18px bold, dark text
- Member count: 14px, gray text
- Join code: 12px, light gray, monospace
- Card margin: 8px horizontal, 6px vertical
- Use `Pressable` with opacity feedback on press

### MemberAvatars component (`components/board/MemberAvatars.tsx`)
**Props:**
```typescript
interface MemberAvatarsProps {
  members: { id: string; display_name: string; avatar_url: string | null }[];
  size?: number; // default 32
}
```

**Behavior:**
- Render up to 3 circular avatars, overlapping slightly (negative margin -8px)
- If `avatar_url` exists, show the image
- If no `avatar_url`, show a colored circle with the first letter of `display_name`
- Color is deterministic based on the member `id` (hash the first chars to pick from a palette)
- Palette: `['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']`

### EmptyBoardState component (`components/board/EmptyBoardState.tsx`)
**Props:**
```typescript
interface EmptyBoardStateProps {
  onCreateBoard: () => void;
  onJoinBoard: () => void;
}
```

- Centered layout with an icon (use Expo's built-in icon set via `@expo/vector-icons`)
- Suggested icon: `Ionicons` name `"people-outline"` at size 64
- Text and subtext below the icon
- Two buttons: "Create Board" (primary) and "Join Board" (secondary)

### Board list screen (`app/(tabs)/index.tsx`)
The full implementation bringing everything together:

```typescript
import { useState, useCallback } from 'react';
import { View, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { BoardList } from '../../components/board/BoardList';
import { EmptyBoardState } from '../../components/board/EmptyBoardState';
import { CreateBoardModal } from '../../components/board/CreateBoardModal';
import { JoinBoardModal } from '../../components/board/JoinBoardModal';
import { useBoardList } from '../../lib/hooks/use-board';
import { useBoardStore } from '../../lib/stores/board-store';

export default function BoardListScreen() {
  const { boards, isLoading, error, refetch } = useBoardList();
  const setActiveBoard = useBoardStore((s) => s.setActiveBoard);
  const [modal, setModal] = useState<'none' | 'create' | 'join'>('none');

  const handleBoardPress = useCallback((board) => {
    setActiveBoard(board);
    router.push(`/board/${board.id}`);
  }, []);

  // Render empty state, loading, error, or board list
  // Pull-to-refresh on FlatList
  // FAB or header buttons for Create/Join
}
```

### Tab bar configuration (`app/(tabs)/_layout.tsx`)
Update the existing tab layout to include the board list tab and profile tab:
- Tab 1: Board list (`index.tsx`) - icon: `Ionicons` "grid-outline" - title: "Boards"
- Tab 2: Profile (`profile.tsx`) - icon: `Ionicons` "person-outline" - title: "Profile"
- Remove any default tabs from the template (Explore, etc.)

### setActiveBoard implementation
Add to `lib/stores/board-store.ts`:
```typescript
setActiveBoard: (board: Board) => {
  set({ activeBoard: board });
},
```

### Performance considerations
- The `fetchBoards` method makes N+1 queries (one per board for member count). For MVP this is acceptable since users will have few boards (< 20). In a future optimization, this could be replaced with a Supabase RPC function or a view.
- Use `FlatList` with `keyExtractor={(item) => item.id}` for efficient list rendering.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| MODIFY | `sendit-app/lib/stores/board-store.ts` | Implement `fetchBoards` and `setActiveBoard` methods, extend Board type |
| MODIFY | `sendit-app/lib/hooks/use-board.ts` | Implement `useBoardList` hook |
| CREATE | `sendit-app/components/board/BoardCard.tsx` | Board card component with name, member count, avatars, join code |
| CREATE | `sendit-app/components/board/BoardList.tsx` | FlatList wrapper for board cards with pull-to-refresh |
| CREATE | `sendit-app/components/board/EmptyBoardState.tsx` | Empty state with create/join CTAs |
| CREATE | `sendit-app/components/board/MemberAvatars.tsx` | Row of overlapping avatar circles |
| MODIFY | `sendit-app/app/(tabs)/index.tsx` | Full board list screen implementation |
| MODIFY | `sendit-app/app/(tabs)/_layout.tsx` | Configure tab bar with Boards and Profile tabs |

## Definition of Done

- [ ] On app launch, boards are fetched from Supabase based on the user's `device_id`
- [ ] Each board card shows the board name, member count, preview avatars, and join code
- [ ] Tapping a board card sets `activeBoard` in the store and navigates to `/board/[id]`
- [ ] Empty state is shown when the user has no boards, with "Create Board" and "Join Board" buttons
- [ ] Loading state (skeleton or spinner) is shown while boards are being fetched
- [ ] Pull-to-refresh re-fetches the board list
- [ ] Error state is shown with a retry button when the fetch fails
- [ ] Boards are ordered newest first
- [ ] After creating or joining a board (Stories 1.2/1.3), the new board appears in the list
- [ ] `MemberAvatars` shows up to 3 overlapping circles with initials as fallback
- [ ] Avatar circle colors are deterministic based on member ID
- [ ] Tab bar shows "Boards" and "Profile" tabs with appropriate icons
- [ ] `useBoardList` hook auto-fetches on mount when auth is initialized
- [ ] `fetchBoards` correctly queries boards via the members table join
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Manually tested: board list displays correctly with 0, 1, and 5+ boards
- [ ] Manually tested: pull-to-refresh works
- [ ] Manually tested: tapping a board card navigates to the board detail screen
- [ ] Manually tested: empty state buttons trigger create/join modals
