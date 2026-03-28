# Story 6.1: Google OAuth Flow

## Description

As a board member,
I want to connect my Google account via OAuth,
So that I can enable calendar-aware suggestions without creating a separate account.

## Status

- **Epic:** Calendar Integration & Progressive Auth
- **Priority:** P1
- **Branch:** `feature/calendar-auth`
- **Assignee:** Whoever finishes P0 first

## Acceptance Criteria

**Given** a user is on the profile screen
**When** they see "Connect Calendar" option
**Then** the option is clearly labeled with a Google icon and explains the benefit ("Get smarter suggestions based on your availability")

**Given** the user taps "Connect Calendar"
**When** the Google OAuth flow launches via expo-auth-session
**Then** the user is presented with Google's consent screen requesting calendar read-only access
**And** the consent scope includes only `https://www.googleapis.com/auth/calendar.freebusy`

**Given** the user completes Google OAuth successfully
**When** the auth code is exchanged for tokens
**Then** the user's `google_id` is saved to their `members` row
**And** the OAuth access token and refresh token are stored securely in Expo SecureStore
**And** the profile screen updates to show "Calendar Connected" with a green checkmark
**And** the user is not required to re-authenticate on app restart (tokens persist)

**Given** the user denies the OAuth permission or cancels the flow
**When** the auth flow returns
**Then** the app gracefully returns to the profile screen with no error crash
**And** the "Connect Calendar" option remains available for retry

**Given** the user has previously connected their Google account
**When** they return to the profile screen
**Then** the screen shows "Calendar Connected" and a "Disconnect" option
**And** their `google_id` is displayed (or email) as confirmation

**Given** the access token has expired
**When** a calendar API call is attempted
**Then** the refresh token is used to obtain a new access token automatically (NFR14)
**And** the user is not prompted to re-authenticate

## Technical Context

### Relevant Schema

```sql
members (
  id uuid PK,
  board_id uuid FK,
  display_name text,
  device_id text,
  google_id text nullable,   -- Set after OAuth completion
  avatar_url text,
  push_token text,
  UNIQUE(board_id, device_id)
)
```

### Architecture References

- **Screen:** `app/(tabs)/profile.tsx` -- Profile/settings screen with calendar connect option
- **Auth Library:** `expo-auth-session` -- Google OAuth provider
- **Secure Storage:** `expo-secure-store` -- Store OAuth tokens (access_token, refresh_token)
- **Store:** `lib/stores/auth-store.ts` -- Track Google auth state
- **Hook:** `lib/hooks/use-auth.ts` -- Expose auth state and connect/disconnect actions
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Epic 1 complete (user has a member row with device_id)
- **Requires:** Google Cloud Console project with OAuth 2.0 credentials configured
- **Requires:** `expo-auth-session` installed (included in project dependencies)
- **Requires:** `expo-secure-store` installed (included in project dependencies)
- **Google OAuth Scopes:** `https://www.googleapis.com/auth/calendar.freebusy` (read-only free/busy data)
- **Downstream:** Story 6.2 (calendar sync uses the OAuth token)

## Implementation Notes

### Google OAuth Configuration

Create a Google Cloud Console OAuth 2.0 Client ID for the app:

- **Application type:** Web application (for Expo auth proxy) or iOS/Android native
- **Redirect URIs:** Expo auth session proxy URI (`https://auth.expo.io/@your-username/sendit-app`)
- **Scopes:** `https://www.googleapis.com/auth/calendar.freebusy`

Store the client ID as an environment variable:

```
EXPO_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### OAuth Flow with expo-auth-session

```typescript
// lib/hooks/use-google-auth.ts
import * as AuthSession from 'expo-auth-session';
import * as Google from 'expo-auth-session/providers/google';
import * as SecureStore from 'expo-secure-store';
import { supabase } from '../supabase';

const GOOGLE_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID;

export const useGoogleAuth = () => {
  const [request, response, promptAsync] = Google.useAuthRequest({
    clientId: GOOGLE_CLIENT_ID,
    scopes: ['https://www.googleapis.com/auth/calendar.freebusy'],
    // Use Expo auth proxy for managed workflow
    redirectUri: AuthSession.makeRedirectUri({ useProxy: true }),
  });

  const connectGoogle = async () => {
    const result = await promptAsync();

    if (result.type === 'success' && result.authentication) {
      const { accessToken, refreshToken, idToken } = result.authentication;

      // Decode the ID token to get google_id (sub claim)
      const decoded = JSON.parse(atob(idToken!.split('.')[1]));
      const googleId = decoded.sub;
      const email = decoded.email;

      // Store tokens securely
      await SecureStore.setItemAsync('google_access_token', accessToken);
      if (refreshToken) {
        await SecureStore.setItemAsync('google_refresh_token', refreshToken);
      }
      await SecureStore.setItemAsync('google_id', googleId);

      // Update member row with google_id
      const memberId = useAuthStore.getState().memberId;
      await supabase
        .from('members')
        .update({ google_id: googleId })
        .eq('id', memberId);

      return { googleId, email };
    }

    return null;
  };

  return { connectGoogle, request };
};
```

### Token Refresh Logic

```typescript
// lib/hooks/use-google-token.ts
import * as SecureStore from 'expo-secure-store';

const GOOGLE_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token';

export const getValidAccessToken = async (): Promise<string | null> => {
  const accessToken = await SecureStore.getItemAsync('google_access_token');

  if (!accessToken) return null;

  // Check if token is still valid by attempting a lightweight API call
  const testResponse = await fetch(
    'https://www.googleapis.com/calendar/v3/freeBusy',
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({
        timeMin: new Date().toISOString(),
        timeMax: new Date().toISOString(),
        items: [],
      }),
    }
  );

  if (testResponse.ok) return accessToken;

  // Token expired -- refresh it
  const refreshToken = await SecureStore.getItemAsync('google_refresh_token');
  if (!refreshToken) return null;

  const refreshResponse = await fetch(GOOGLE_TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID!,
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    }).toString(),
  });

  if (!refreshResponse.ok) return null;

  const tokenData = await refreshResponse.json();
  await SecureStore.setItemAsync('google_access_token', tokenData.access_token);

  return tokenData.access_token;
};
```

### Auth Store Extension

```typescript
// lib/stores/auth-store.ts -- extend existing store
interface AuthState {
  deviceId: string | null;
  memberId: string | null;
  googleId: string | null;
  isGoogleConnected: boolean;

  setGoogleConnected: (googleId: string) => void;
  disconnectGoogle: () => Promise<void>;
  checkGoogleConnection: () => Promise<void>;
}

// On app load, check if google tokens exist in SecureStore
const checkGoogleConnection = async () => {
  const googleId = await SecureStore.getItemAsync('google_id');
  set({ googleId, isGoogleConnected: !!googleId });
};

const disconnectGoogle = async () => {
  await SecureStore.deleteItemAsync('google_access_token');
  await SecureStore.deleteItemAsync('google_refresh_token');
  await SecureStore.deleteItemAsync('google_id');

  const memberId = get().memberId;
  if (memberId) {
    await supabase
      .from('members')
      .update({ google_id: null })
      .eq('id', memberId);
  }

  set({ googleId: null, isGoogleConnected: false });
};
```

### Profile Screen UI

```typescript
// In profile.tsx
const CalendarConnectSection = () => {
  const { isGoogleConnected, googleId } = useAuthStore();
  const { connectGoogle } = useGoogleAuth();

  if (isGoogleConnected) {
    return (
      <View>
        <Text>Calendar Connected ✓</Text>
        <Text style={styles.subtitle}>{googleId}</Text>
        <TouchableOpacity onPress={disconnectGoogle}>
          <Text>Disconnect</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <TouchableOpacity onPress={connectGoogle}>
      <Text>Connect Google Calendar</Text>
      <Text style={styles.subtitle}>Get smarter suggestions based on your availability</Text>
    </TouchableOpacity>
  );
};
```

### SecureStore Keys

| Key | Value |
|-----|-------|
| `google_access_token` | OAuth access token for Calendar API calls |
| `google_refresh_token` | OAuth refresh token for token renewal |
| `google_id` | User's Google account ID (sub claim from ID token) |

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `lib/hooks/use-google-auth.ts` | Hook wrapping expo-auth-session Google OAuth flow |
| `lib/hooks/use-google-token.ts` | Hook for getting a valid access token with automatic refresh |
| `components/shared/CalendarConnectCard.tsx` | Reusable card component for calendar connection status and action |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/profile.tsx` | Add CalendarConnectCard section with connect/disconnect functionality |
| `lib/stores/auth-store.ts` | Add Google OAuth state: googleId, isGoogleConnected, setGoogleConnected, disconnectGoogle, checkGoogleConnection |
| `app/_layout.tsx` | Call checkGoogleConnection on app mount to restore auth state |

## Definition of Done

- [ ] "Connect Calendar" button on profile screen launches Google OAuth via expo-auth-session
- [ ] OAuth consent screen requests only `calendar.freebusy` scope (minimal permissions)
- [ ] Successful auth saves `google_id` to the member row in Supabase
- [ ] Access token and refresh token stored securely in Expo SecureStore
- [ ] Profile screen shows "Calendar Connected" state after successful auth
- [ ] Canceling or denying OAuth returns gracefully to profile screen without crash
- [ ] "Disconnect" option clears tokens from SecureStore and nullifies `google_id` in member row
- [ ] Token refresh works automatically when access token expires (NFR14)
- [ ] Auth state persists across app restarts (tokens checked from SecureStore on mount)
- [ ] Google Cloud Console OAuth credentials configured with correct redirect URI
- [ ] No calendar event data is requested or accessed (only free/busy scope)
