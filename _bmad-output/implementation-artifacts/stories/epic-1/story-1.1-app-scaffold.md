# Story 1.1: App Scaffold & Foundation Setup

## Description
As a developer, I want the Expo project scaffolded with the correct folder structure, Supabase client initialization, environment configuration, and device-based auth store, so that all subsequent stories have a stable foundation to build on.

## Status
- Epic: Epic 1 - Board Creation & Onboarding
- Priority: P0
- Branch: feature/board-creation
- Assignee: TBD (pick up from sprint board)

## Acceptance Criteria

### AC 1: Folder structure matches the architecture spec
- **Given** the Expo project exists at `sendit-app/` with the default tabs template
- **When** the scaffold story is complete
- **Then** the following directories and placeholder files exist:
  - `lib/supabase.ts`
  - `lib/stores/auth-store.ts`
  - `lib/stores/board-store.ts` (empty export, filled in Story 1.2)
  - `lib/hooks/use-realtime.ts` (empty export, filled in Story 1.5)
  - `lib/hooks/use-board.ts` (empty export, filled in Story 1.4/1.5)
  - `components/board/` directory exists
  - `components/shared/` directory exists
  - `app/(tabs)/index.tsx` exists (will become board list)
  - `app/(tabs)/board/[id].tsx` exists (placeholder)
  - `app/(tabs)/profile.tsx` exists (placeholder)
  - `app/join/[code].tsx` exists (placeholder)

### AC 2: Environment variables are configured
- **Given** the project has no `.env` file
- **When** the scaffold story is complete
- **Then** a `.env` file exists at the project root with:
  ```
  EXPO_PUBLIC_SUPABASE_URL=https://ubhbeqnagxbuoikzftht.supabase.co
  EXPO_PUBLIC_SUPABASE_ANON_KEY=<placeholder_for_anon_key>
  ```
- **And** `.env` is listed in `.gitignore`
- **And** a `.env.example` file exists with the same keys but empty values

### AC 3: Supabase client initializes correctly
- **Given** the environment variables are set
- **When** `lib/supabase.ts` is imported
- **Then** it exports a `supabase` client configured with:
  - `ExpoSecureStoreAdapter` for native platforms
  - `undefined` storage for web
  - `autoRefreshToken: true`
  - `persistSession: true`
  - `detectSessionInUrl: false`

### AC 4: Auth store generates and persists a device UUID
- **Given** the app is launched for the first time on a device
- **When** the auth store initializes
- **Then** a v4 UUID is generated via `expo-crypto`
- **And** the UUID is persisted in `expo-secure-store` under the key `sendit_device_id`
- **And** subsequent launches read the existing UUID instead of generating a new one

### AC 5: Auth store exposes required state
- **Given** the auth store is initialized
- **When** any component subscribes to it
- **Then** it provides: `deviceId: string | null`, `isLoading: boolean`, `isInitialized: boolean`, `googleId: string | null`, `initialize(): Promise<void>`

### AC 6: Dependencies are installed
- **Given** the project `package.json`
- **When** the scaffold story is complete
- **Then** `zustand` and `expo-crypto` are added to `dependencies`

### AC 7: Root layout initializes the auth store
- **Given** the app starts
- **When** `_layout.tsx` renders
- **Then** the auth store's `initialize()` method is called before any child routes render
- **And** a loading/splash screen is shown until `isInitialized` is `true`

## Technical Context

### Relevant Schema
No database tables are directly used in this story. This story sets up the client-side infrastructure that later stories use to interact with:

```sql
-- Referenced by auth-store for device_id matching
members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id uuid REFERENCES boards(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  device_id text NOT NULL,
  google_id text,
  avatar_url text,
  push_token text,
  UNIQUE(board_id, device_id)
)
```

### Architecture References

**Folder structure to create:**
```
sendit-app/
  .env                          # NEW - environment variables
  .env.example                  # NEW - template for env vars
  lib/
    supabase.ts                 # NEW - Supabase client singleton
    stores/
      auth-store.ts             # NEW - device auth state via Zustand
      board-store.ts            # NEW - empty placeholder
    hooks/
      use-realtime.ts           # NEW - empty placeholder
      use-board.ts              # NEW - empty placeholder
  components/
    board/
      .gitkeep                  # NEW - preserve empty dir
    shared/
      .gitkeep                  # NEW - preserve empty dir
  app/
    (tabs)/
      index.tsx                 # MODIFY - replace default content with placeholder board list
      board/
        [id].tsx                # NEW - placeholder board detail route
      profile.tsx               # NEW - placeholder profile/settings route
    join/
      [code].tsx                # NEW - placeholder deep link join route
    _layout.tsx                 # MODIFY - add auth store initialization
```

**Patterns to follow:**
- Zustand store pattern: `create<StateType>()((set, get) => ({ ... }))`
- All stores in `lib/stores/` export a named hook (e.g., `useAuthStore`)
- SecureStore keys prefixed with `sendit_` to avoid collisions

### Dependencies

- Expo project at `sendit-app/` must exist with tabs template (already done)
- `@supabase/supabase-js` must be installed (already done)
- `expo-secure-store` must be installed (already done)
- `zustand` must be installed (install in this story)
- `expo-crypto` must be installed (install in this story)

## Implementation Notes

### Installing missing dependencies
Run from `sendit-app/`:
```bash
npx expo install zustand expo-crypto
```
Use `npx expo install` instead of `npm install` to ensure Expo-compatible versions.

### Supabase client (`lib/supabase.ts`)
Use the exact implementation provided in the technical spec:
```typescript
import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!;

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: Platform.OS !== 'web' ? ExpoSecureStoreAdapter : undefined,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});
```

### Auth store (`lib/stores/auth-store.ts`)
Key implementation details:
- Use `expo-crypto` to generate UUID: `import * as Crypto from 'expo-crypto'; const id = Crypto.randomUUID();`
- Store/retrieve from SecureStore under key `sendit_device_id`
- The `initialize()` method should:
  1. Set `isLoading: true`
  2. Try to read `sendit_device_id` from SecureStore
  3. If not found, generate a new UUID and store it
  4. Set `deviceId` and `isInitialized: true`, `isLoading: false`
- Export the store as `useAuthStore`

```typescript
import { create } from 'zustand';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

const DEVICE_ID_KEY = 'sendit_device_id';

interface AuthState {
  deviceId: string | null;
  googleId: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  deviceId: null,
  googleId: null,
  isLoading: false,
  isInitialized: false,

  initialize: async () => {
    if (get().isInitialized) return;
    set({ isLoading: true });

    try {
      let deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
      if (!deviceId) {
        deviceId = Crypto.randomUUID();
        await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId);
      }
      set({ deviceId, isInitialized: true, isLoading: false });
    } catch (error) {
      console.error('Failed to initialize auth store:', error);
      set({ isLoading: false });
    }
  },
}));
```

### Root layout modification
Modify `app/_layout.tsx` to:
1. Import `useAuthStore`
2. Call `initialize()` in a `useEffect`
3. Show null (keep splash screen visible) until `isInitialized` is true
4. Add the new routes to the Stack navigator: `join/[code]`, `(tabs)/board/[id]`

### Placeholder files
All placeholder route files should export a minimal component:
```typescript
import { View, Text } from 'react-native';

export default function PlaceholderScreen() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Coming soon</Text>
    </View>
  );
}
```

Placeholder store/hook files should export an empty object or no-op:
```typescript
// board-store.ts placeholder
export {};

// use-realtime.ts placeholder
export {};

// use-board.ts placeholder
export {};
```

### .gitignore update
Add these lines if not already present:
```
.env
.env.local
```

### Deep link scheme
The `app.json` already has `"scheme": "senditapp"` configured. Deep links will use `senditapp://join/[code]`. No changes to `app.json` needed for this story.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| CREATE | `sendit-app/.env` | Environment variables with Supabase URL and anon key |
| CREATE | `sendit-app/.env.example` | Template with empty values |
| MODIFY | `sendit-app/.gitignore` | Add `.env` and `.env.local` entries |
| CREATE | `sendit-app/lib/supabase.ts` | Supabase client singleton |
| CREATE | `sendit-app/lib/stores/auth-store.ts` | Device auth Zustand store |
| CREATE | `sendit-app/lib/stores/board-store.ts` | Empty placeholder |
| CREATE | `sendit-app/lib/hooks/use-realtime.ts` | Empty placeholder |
| CREATE | `sendit-app/lib/hooks/use-board.ts` | Empty placeholder |
| CREATE | `sendit-app/components/board/.gitkeep` | Preserve directory |
| CREATE | `sendit-app/components/shared/.gitkeep` | Preserve directory |
| MODIFY | `sendit-app/app/_layout.tsx` | Add auth store initialization, keep splash until ready |
| MODIFY | `sendit-app/app/(tabs)/index.tsx` | Replace default Expo content with board list placeholder |
| CREATE | `sendit-app/app/(tabs)/board/[id].tsx` | Placeholder board detail screen |
| CREATE | `sendit-app/app/(tabs)/profile.tsx` | Placeholder profile/settings screen |
| CREATE | `sendit-app/app/join/[code].tsx` | Placeholder deep link join screen |
| MODIFY | `sendit-app/package.json` | Add zustand and expo-crypto via `npx expo install` |

## Definition of Done

- [ ] `npx expo install zustand expo-crypto` has been run and both packages appear in `package.json`
- [ ] `.env` file exists with `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` set
- [ ] `.env.example` exists with the same keys but empty values
- [ ] `.env` is in `.gitignore`
- [ ] `lib/supabase.ts` exports a configured `supabase` client
- [ ] `lib/stores/auth-store.ts` exports `useAuthStore` with `deviceId`, `isLoading`, `isInitialized`, `googleId`, and `initialize()`
- [ ] On first launch, a UUID is generated and persisted to SecureStore
- [ ] On subsequent launches, the same UUID is read from SecureStore
- [ ] `app/_layout.tsx` calls `initialize()` and blocks rendering until `isInitialized` is true
- [ ] All placeholder files exist and export valid React components or empty modules
- [ ] The app compiles and runs without errors on iOS and Android simulators via `npx expo start`
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Folder structure matches the architecture spec
