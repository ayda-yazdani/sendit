# Story 1.2: Create Board

## Description
As a user, I want to create a new board with a name and receive a unique join code, so that I can invite my friends to join the board and start sharing content together.

## Status
- Epic: Epic 1 - Board Creation & Onboarding
- Priority: P0
- Branch: feature/board-creation
- Assignee: TBD (pick up from sprint board)

## Acceptance Criteria

### AC 1: User can open the create board flow
- **Given** the user is on the board list screen (`app/(tabs)/index.tsx`)
- **When** the user taps the "Create Board" button (FAB or header button)
- **Then** a modal/bottom sheet appears with a text input for the board name

### AC 2: Board name validation
- **Given** the create board modal is open
- **When** the user enters a board name
- **Then** the name must be between 1 and 50 characters
- **And** leading/trailing whitespace is trimmed before submission
- **And** the "Create" button is disabled if the trimmed name is empty

### AC 3: Board is created with a unique join code
- **Given** the user has entered a valid board name
- **When** the user taps "Create"
- **Then** a new row is inserted into the `boards` table with:
  - `name`: the trimmed board name
  - `join_code`: a randomly generated 6-character uppercase alphanumeric code
  - `created_at`: auto-set by Supabase default
- **And** if the join code collides (unique constraint violation), a new code is generated and the insert is retried (up to 3 attempts)

### AC 4: Creator is automatically added as a member
- **Given** the board row has been successfully inserted
- **When** the board creation process continues
- **Then** a new row is inserted into the `members` table with:
  - `board_id`: the new board's `id`
  - `display_name`: prompted from the user (or defaults to "Board Creator")
  - `device_id`: from the auth store
  - `google_id`: from the auth store (null if not Google-authed)
- **And** if the member insert fails, the board row is deleted (cleanup)

### AC 5: Join code is displayed after creation
- **Given** the board and member have been created successfully
- **When** the creation process completes
- **Then** a success modal appears showing:
  - The board name
  - The join code in large, readable text (e.g., "ABC123")
  - A "Copy Code" button that copies the join code to the clipboard
  - A "Share" button that opens the native share sheet with the deep link `senditapp://join/[code]`
  - A "Done" button that navigates to the new board's detail screen

### AC 6: Board list updates after creation
- **Given** a board has been successfully created
- **When** the user dismisses the success modal
- **Then** the board list screen shows the newly created board
- **And** the board store's `boards` array includes the new board

### AC 7: Error handling
- **Given** the board creation request fails (network error, Supabase error)
- **When** the error is caught
- **Then** an error message is displayed to the user (Alert or inline error)
- **And** the create button is re-enabled
- **And** a loading indicator is shown during the request

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
    board-store.ts           # MODIFY - implement createBoard method
  utils/
    join-code.ts             # NEW - join code generation utility
components/
  board/
    CreateBoardModal.tsx     # NEW - create board form modal
    JoinCodeDisplay.tsx      # NEW - success modal with join code
  shared/
    Button.tsx               # NEW - reusable button component
    Input.tsx                # NEW - reusable text input component
app/
  (tabs)/
    index.tsx                # MODIFY - add create board trigger
```

**Patterns to follow:**
- Board store uses Zustand with async methods that call Supabase
- Modals use React Native `Modal` component or Expo Router modal routes
- All Supabase calls go through the `supabase` client from `lib/supabase.ts`
- Components use TypeScript interfaces for props

### Dependencies

- Story 1.1 must be complete (auth store with `deviceId`, Supabase client, folder structure)
- `boards` and `members` tables must exist in Supabase (already live)
- `expo-clipboard` for copy-to-clipboard functionality (install in this story)

## Implementation Notes

### Join code generation (`lib/utils/join-code.ts`)
```typescript
export function generateJoinCode(length: number = 6): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // Exclude 0/O, 1/I/L to avoid ambiguity
  let code = '';
  for (let i = 0; i < length; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}
```
- Exclude visually ambiguous characters: `0`, `O`, `1`, `I`, `L`
- This gives 30^6 = ~729 million possible codes, more than enough for the app's scale

### Board store `createBoard` method
Add to `lib/stores/board-store.ts`:
```typescript
import { create } from 'zustand';
import { supabase } from '../supabase';
import { generateJoinCode } from '../utils/join-code';
import { useAuthStore } from './auth-store';

interface Board {
  id: string;
  name: string;
  join_code: string;
  created_at: string;
}

interface Member {
  id: string;
  board_id: string;
  display_name: string;
  device_id: string;
  google_id: string | null;
  avatar_url: string | null;
  push_token: string | null;
}

interface BoardState {
  boards: Board[];
  activeBoard: Board | null;
  activeBoardMembers: Member[];
  isLoading: boolean;
  error: string | null;
  fetchBoards: () => Promise<void>;
  createBoard: (name: string, displayName: string) => Promise<Board>;
  joinBoard: (code: string, displayName: string) => Promise<Board>;
  setActiveBoard: (board: Board) => void;
}

export const useBoardStore = create<BoardState>()((set, get) => ({
  boards: [],
  activeBoard: null,
  activeBoardMembers: [],
  isLoading: false,
  error: null,

  createBoard: async (name: string, displayName: string): Promise<Board> => {
    set({ isLoading: true, error: null });

    const { deviceId, googleId } = useAuthStore.getState();
    if (!deviceId) throw new Error('Device not initialized');

    let board: Board | null = null;
    let attempts = 0;
    const maxAttempts = 3;

    // Insert board with retry for join code collisions
    while (attempts < maxAttempts) {
      const joinCode = generateJoinCode();
      const { data, error } = await supabase
        .from('boards')
        .insert({ name: name.trim(), join_code: joinCode })
        .select()
        .single();

      if (error) {
        if (error.code === '23505' && attempts < maxAttempts - 1) {
          // Unique constraint violation on join_code, retry
          attempts++;
          continue;
        }
        set({ isLoading: false, error: error.message });
        throw new Error(error.message);
      }

      board = data;
      break;
    }

    if (!board) {
      set({ isLoading: false, error: 'Failed to generate unique join code' });
      throw new Error('Failed to generate unique join code');
    }

    // Insert creator as member
    const { error: memberError } = await supabase
      .from('members')
      .insert({
        board_id: board.id,
        display_name: displayName.trim() || 'Board Creator',
        device_id: deviceId,
        google_id: googleId,
      });

    if (memberError) {
      // Cleanup: delete the board if member creation fails
      await supabase.from('boards').delete().eq('id', board.id);
      set({ isLoading: false, error: memberError.message });
      throw new Error(memberError.message);
    }

    set((state) => ({
      boards: [board!, ...state.boards],
      isLoading: false,
    }));

    return board;
  },

  // Placeholder methods (implemented in later stories)
  fetchBoards: async () => {},
  joinBoard: async () => { throw new Error('Not implemented'); },
  setActiveBoard: () => {},
}));
```

### CreateBoardModal component
- Use React Native `Modal` with `animationType="slide"` and `transparent={true}`
- State: `boardName`, `displayName`, `isSubmitting`
- On submit: call `useBoardStore.getState().createBoard(boardName, displayName)`
- On success: transition to `JoinCodeDisplay`
- On error: show `Alert.alert('Error', error.message)`

### JoinCodeDisplay component
- Shows the join code in a large monospace font
- "Copy Code" button uses `expo-clipboard`: `Clipboard.setStringAsync(joinCode)`
- "Share" button uses `expo-sharing` or React Native `Share.share()`:
  ```typescript
  import { Share } from 'react-native';
  Share.share({
    message: `Join my board on Sendit! Use code ${joinCode} or tap: senditapp://join/${joinCode}`,
  });
  ```
- "Done" button calls `router.push(`/board/${boardId}`)` and closes the modal

### Shared components
Create minimal reusable components that will be used across the app:

**`components/shared/Button.tsx`:**
- Props: `title`, `onPress`, `disabled`, `loading`, `variant` ('primary' | 'secondary' | 'ghost')
- Uses `TouchableOpacity` with `ActivityIndicator` when loading

**`components/shared/Input.tsx`:**
- Props: `label`, `value`, `onChangeText`, `placeholder`, `maxLength`, `error`
- Uses `TextInput` with label and error text

### Installing expo-clipboard
```bash
npx expo install expo-clipboard
```

### Display name prompt
In the CreateBoardModal, include a second text input for the user's display name. This is the name other board members will see. Pre-fill with empty string. If left empty, default to "Board Creator".

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| CREATE | `sendit-app/lib/utils/join-code.ts` | Join code generation utility |
| MODIFY | `sendit-app/lib/stores/board-store.ts` | Replace placeholder with full store including `createBoard` |
| CREATE | `sendit-app/components/board/CreateBoardModal.tsx` | Modal form for creating a board |
| CREATE | `sendit-app/components/board/JoinCodeDisplay.tsx` | Success modal showing join code with copy/share |
| CREATE | `sendit-app/components/shared/Button.tsx` | Reusable button component |
| CREATE | `sendit-app/components/shared/Input.tsx` | Reusable text input component |
| MODIFY | `sendit-app/app/(tabs)/index.tsx` | Add FAB or header button to trigger CreateBoardModal |
| MODIFY | `sendit-app/package.json` | Add expo-clipboard via `npx expo install` |

## Definition of Done

- [ ] `expo-clipboard` is installed and appears in `package.json`
- [ ] `lib/utils/join-code.ts` generates 6-character codes using only unambiguous alphanumeric characters
- [ ] `lib/stores/board-store.ts` exports `useBoardStore` with a working `createBoard` method
- [ ] `createBoard` inserts a row into `boards` with a unique `join_code`
- [ ] `createBoard` retries up to 3 times on join code collision
- [ ] `createBoard` inserts the creator into `members` with the correct `device_id`
- [ ] If member creation fails, the board row is cleaned up (deleted)
- [ ] `CreateBoardModal` validates board name (1-50 chars, trimmed, non-empty)
- [ ] `CreateBoardModal` collects a display name with sensible default
- [ ] `JoinCodeDisplay` shows the code in large readable text
- [ ] "Copy Code" copies the join code to the system clipboard
- [ ] "Share" opens the native share sheet with the deep link URL
- [ ] "Done" navigates to the board detail screen and closes the modal
- [ ] The board list updates to include the newly created board
- [ ] Loading states are shown during async operations
- [ ] Errors are displayed to the user via Alert
- [ ] Shared `Button` and `Input` components are created and used
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Manually tested: create board on iOS/Android simulator, verify row in Supabase dashboard
