# Story 1.3: Join Board

## Description
As a user, I want to join an existing board by entering a join code or tapping a deep link, so that I can participate in a friend's board without needing to create my own.

## Status
- Epic: Epic 1 - Board Creation & Onboarding
- Priority: P0
- Branch: feature/board-creation
- Assignee: TBD (pick up from sprint board)

## Acceptance Criteria

### AC 1: Manual code entry on board list screen
- **Given** the user is on the board list screen (`app/(tabs)/index.tsx`)
- **When** the user taps the "Join Board" button
- **Then** a modal appears with a text input for the 6-character join code
- **And** the input auto-capitalizes and limits to 6 characters
- **And** the input strips any non-alphanumeric characters

### AC 2: Deep link handling via `senditapp://join/[code]`
- **Given** the user taps a deep link with format `senditapp://join/ABC123`
- **When** the app opens (or is already open)
- **Then** the app navigates to `app/join/[code].tsx`
- **And** the join code is extracted from the route parameter
- **And** the join flow begins automatically (skipping manual code entry)

### AC 3: Board lookup by join code
- **Given** a join code has been entered (manually or via deep link)
- **When** the join flow executes
- **Then** the app queries the `boards` table for a row where `join_code` matches (case-insensitive)
- **And** if no board is found, an error message is shown: "No board found with that code. Check the code and try again."
- **And** if a board is found, the board name is displayed for confirmation

### AC 4: Display name prompt
- **Given** a board has been found by join code
- **When** the user is about to join
- **Then** the user is prompted to enter a display name
- **And** the display name must be between 1 and 30 characters (trimmed)
- **And** a "Join" button is shown that is disabled until a valid name is entered

### AC 5: Member row is created
- **Given** the user has entered a valid display name and confirmed
- **When** the user taps "Join"
- **Then** a new row is inserted into the `members` table with:
  - `board_id`: the found board's `id`
  - `display_name`: the trimmed display name
  - `device_id`: from the auth store
  - `google_id`: from the auth store (null if not Google-authed)
- **And** a loading indicator is shown during the request

### AC 6: Duplicate membership prevention
- **Given** the user's `device_id` already has a member row for this board
- **When** the user tries to join
- **Then** the app detects the `UNIQUE(board_id, device_id)` constraint violation
- **And** shows a message: "You're already a member of this board!"
- **And** navigates the user to the board detail screen instead of creating a duplicate

### AC 7: Successful join navigates to board
- **Given** the member row has been created successfully
- **When** the join is complete
- **Then** the board store's `boards` array is updated to include the joined board
- **And** the app navigates to the board detail screen (`/board/[id]`)

### AC 8: Error handling
- **Given** any step in the join flow fails (network error, Supabase error)
- **When** the error is caught
- **Then** an appropriate error message is shown to the user
- **And** the join button is re-enabled for retry

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
    board-store.ts              # MODIFY - implement joinBoard method
app/
  (tabs)/
    index.tsx                   # MODIFY - add "Join Board" button and JoinBoardModal
  join/
    [code].tsx                  # MODIFY - replace placeholder with deep link join flow
components/
  board/
    JoinBoardModal.tsx          # NEW - manual code entry modal
    JoinBoardFlow.tsx           # NEW - shared join flow UI (lookup, name prompt, confirm)
```

**Patterns to follow:**
- Deep link route `app/join/[code].tsx` uses `useLocalSearchParams()` from Expo Router to get the `code` param
- The join flow UI is shared between the manual modal and the deep link route via `JoinBoardFlow` component
- Board store `joinBoard` method handles the Supabase logic; UI components call it

### Dependencies

- Story 1.1 must be complete (auth store with `deviceId`, Supabase client)
- Story 1.2 must be complete (board store exists with type definitions, shared Button/Input components)
- `boards` and `members` tables must exist in Supabase (already live)
- `app.json` has `"scheme": "senditapp"` configured (already done)

## Implementation Notes

### Board store `joinBoard` method
Add to the existing `useBoardStore` in `lib/stores/board-store.ts`:

```typescript
joinBoard: async (code: string, displayName: string): Promise<Board> => {
  set({ isLoading: true, error: null });

  const { deviceId, googleId } = useAuthStore.getState();
  if (!deviceId) throw new Error('Device not initialized');

  // Look up board by join code (case-insensitive)
  const { data: board, error: lookupError } = await supabase
    .from('boards')
    .select()
    .ilike('join_code', code.trim().toUpperCase())
    .single();

  if (lookupError || !board) {
    set({ isLoading: false, error: 'No board found with that code' });
    throw new Error('No board found with that code. Check the code and try again.');
  }

  // Check if user is already a member
  const { data: existingMember } = await supabase
    .from('members')
    .select()
    .eq('board_id', board.id)
    .eq('device_id', deviceId)
    .single();

  if (existingMember) {
    // Already a member, just return the board
    set((state) => ({
      isLoading: false,
      boards: state.boards.some((b) => b.id === board.id)
        ? state.boards
        : [board, ...state.boards],
    }));
    return { ...board, alreadyMember: true } as Board & { alreadyMember: boolean };
  }

  // Create member row
  const { error: memberError } = await supabase
    .from('members')
    .insert({
      board_id: board.id,
      display_name: displayName.trim(),
      device_id: deviceId,
      google_id: googleId,
    });

  if (memberError) {
    // Handle unique constraint violation (race condition)
    if (memberError.code === '23505') {
      set((state) => ({
        isLoading: false,
        boards: state.boards.some((b) => b.id === board.id)
          ? state.boards
          : [board, ...state.boards],
      }));
      return board;
    }
    set({ isLoading: false, error: memberError.message });
    throw new Error(memberError.message);
  }

  set((state) => ({
    boards: [board, ...state.boards],
    isLoading: false,
  }));

  return board;
},
```

### Deep link route (`app/join/[code].tsx`)
This route handles `senditapp://join/ABC123`:

```typescript
import { useLocalSearchParams, router } from 'expo-router';
import { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { JoinBoardFlow } from '../../components/board/JoinBoardFlow';

export default function JoinByCodeScreen() {
  const { code } = useLocalSearchParams<{ code: string }>();

  if (!code) {
    // Invalid deep link, go to board list
    router.replace('/');
    return null;
  }

  return <JoinBoardFlow code={code} onComplete={(boardId) => router.replace(`/board/${boardId}`)} />;
}
```

### JoinBoardFlow component (`components/board/JoinBoardFlow.tsx`)
This is the shared UI used by both the deep link route and the manual join modal:

**Props:**
- `code: string` - the join code (pre-filled for deep link, entered by user for manual)
- `onComplete: (boardId: string) => void` - callback after successful join
- `onCancel?: () => void` - callback to close the flow

**Flow states (use a state machine):**
1. `lookingUp` - Looking up the board by code, show spinner
2. `found` - Board found, show board name and display name input
3. `joining` - Inserting member row, show spinner
4. `alreadyMember` - User already in this board, show message with "Go to Board" button
5. `error` - Show error with retry option
6. `success` - Join complete, auto-navigate

**Implementation:**
- On mount (or when code changes), call `supabase.from('boards').select().ilike('join_code', code).single()` to look up the board
- If found, show board name and prompt for display name
- On "Join" tap, call `useBoardStore.getState().joinBoard(code, displayName)`
- Handle the `alreadyMember` case gracefully with navigation to the board

### JoinBoardModal component (`components/board/JoinBoardModal.tsx`)
Wraps the manual code entry step before handing off to `JoinBoardFlow`:

**Two-step approach:**
1. First screen: 6-character code input with "Look Up" button
2. After code is entered, transitions to `JoinBoardFlow` with the code

**Code input behavior:**
- `autoCapitalize="characters"` on the TextInput
- `maxLength={6}`
- Strip non-alphanumeric characters on change: `text.replace(/[^A-Z0-9]/gi, '').toUpperCase()`
- Show character count: "3/6"
- Disable "Look Up" button until 6 characters are entered

### Updating the board list screen (`app/(tabs)/index.tsx`)
Add a "Join Board" button alongside the "Create Board" button. Options:
- Two buttons in the header: "Create" (left) and "Join" (right)
- Or a FAB with a speed dial showing both options
- Simplest: two prominent buttons at the top of the board list

The modal state should be managed with `useState<'none' | 'create' | 'join'>('none')`.

### Testing deep links
To test deep links locally:
```bash
# iOS Simulator
npx uri-scheme open senditapp://join/ABC123 --ios

# Android Emulator
adb shell am start -a android.intent.action.VIEW -d "senditapp://join/ABC123" com.senditapp
```

### Expo Router deep link configuration
Expo Router automatically handles deep links based on the file structure. The route `app/join/[code].tsx` will match `senditapp://join/ABC123` with `code = "ABC123"`. No additional linking configuration is needed beyond the `scheme` in `app.json`.

However, the `app/join/[code].tsx` route is outside the `(tabs)` group, so it renders as a full-screen route without tab navigation. This is the desired behavior for the join flow.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| MODIFY | `sendit-app/lib/stores/board-store.ts` | Add `joinBoard` method implementation |
| CREATE | `sendit-app/components/board/JoinBoardFlow.tsx` | Shared join flow UI (lookup, name prompt, confirm) |
| CREATE | `sendit-app/components/board/JoinBoardModal.tsx` | Manual code entry modal for board list screen |
| MODIFY | `sendit-app/app/join/[code].tsx` | Replace placeholder with deep link join handler |
| MODIFY | `sendit-app/app/(tabs)/index.tsx` | Add "Join Board" button and wire up JoinBoardModal |

## Definition of Done

- [ ] "Join Board" button is visible on the board list screen
- [ ] Tapping "Join Board" opens a modal with a 6-character code input
- [ ] Code input auto-capitalizes, strips invalid characters, limits to 6 characters
- [ ] Entering a valid code and tapping "Look Up" finds the board and shows its name
- [ ] Entering an invalid code shows "No board found with that code"
- [ ] User is prompted for a display name (1-30 chars, trimmed)
- [ ] Tapping "Join" creates a member row in Supabase with correct `board_id`, `device_id`, and `display_name`
- [ ] If the user is already a member, a friendly message is shown and they can navigate to the board
- [ ] Deep link `senditapp://join/[code]` opens the app and navigates to the join flow
- [ ] Deep link join flow auto-populates the code and begins lookup immediately
- [ ] After successful join, the user is navigated to the board detail screen
- [ ] The board list updates to include the newly joined board
- [ ] Loading indicators are shown during async operations
- [ ] All error states are handled with user-friendly messages
- [ ] `JoinBoardFlow` component is shared between the modal and the deep link route
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Manually tested: join board via code entry on iOS/Android simulator
- [ ] Manually tested: join board via deep link on iOS/Android simulator
- [ ] Manually tested: attempt to join a board you're already a member of
- [ ] Verified member row in Supabase dashboard after successful join
