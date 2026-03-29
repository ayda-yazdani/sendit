# Story 6.2: Calendar Sync -- Free/Busy Mask

## Description

As the system,
I want to read a member's Google Calendar and store only free/busy time blocks,
So that suggestions can be time-aware without exposing private calendar details.

## Status

- **Epic:** Calendar Integration & Progressive Auth
- **Priority:** P1
- **Branch:** `feature/calendar-auth`
- **Assignee:** Whoever finishes P0 first

## Acceptance Criteria

**Given** a member has completed Google OAuth (google_id and access token exist)
**When** calendar sync is triggered (on auth completion, and periodically thereafter)
**Then** the Google Calendar FreeBusy API is called for the next 14 days
**And** only busy time blocks (start/end timestamps) are extracted from the response
**And** no event titles, descriptions, attendees, or locations are stored (NFR6)

**Given** the FreeBusy API returns busy blocks
**When** the data is processed
**Then** the busy slots are stored as a JSON array of `{start: string, end: string}` objects in `calendar_masks.busy_slots`
**And** the `synced_at` timestamp is updated to the current time

**Given** a member already has a calendar mask
**When** sync runs again (e.g., 24 hours later)
**Then** the existing `busy_slots` are replaced with fresh data (full refresh, not append)
**And** the `synced_at` timestamp is updated

**Given** a member has multiple Google calendars
**When** the FreeBusy API is called
**Then** busy blocks from ALL calendars are included (the FreeBusy API aggregates by default)

**Given** the Google access token has expired
**When** calendar sync is attempted
**Then** the refresh token is used to get a new access token (Story 6.1)
**And** sync proceeds with the refreshed token
**And** the user is not prompted to re-authenticate

**Given** the member has no calendar events in the next 14 days
**When** sync completes
**Then** `busy_slots` is stored as an empty array `[]`
**And** the member is treated as fully available

## Technical Context

### Relevant Schema

```sql
calendar_masks (
  id uuid PK DEFAULT gen_random_uuid(),
  member_id uuid FK REFERENCES members(id) UNIQUE,
  busy_slots jsonb DEFAULT '[]',   -- Array of { start: ISO string, end: ISO string }
  synced_at timestamptz DEFAULT now()
)
```

**Example busy_slots value:**

```json
[
  { "start": "2026-03-29T09:00:00Z", "end": "2026-03-29T10:30:00Z" },
  { "start": "2026-03-29T14:00:00Z", "end": "2026-03-29T15:00:00Z" },
  { "start": "2026-03-30T18:00:00Z", "end": "2026-03-30T20:00:00Z" }
]
```

### Architecture References

- **Google API:** Google Calendar FreeBusy API (`POST https://www.googleapis.com/calendar/v3/freeBusy`)
- **Token Management:** `lib/hooks/use-google-token.ts` (from Story 6.1)
- **Store:** `lib/stores/auth-store.ts` -- track sync status
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 6.1 (Google OAuth) -- valid access token
- **Downstream:** Story 6.3 (mutual availability) -- reads calendar_masks for all board members
- **Privacy constraint:** NFR6 -- only free/busy blocks, no event titles/descriptions/attendees

## Implementation Notes

### Google Calendar FreeBusy API Call

```typescript
// lib/calendar/sync-calendar.ts
import { getValidAccessToken } from '../hooks/use-google-token';
import { supabase } from '../supabase';

const FREEBUSY_ENDPOINT = 'https://www.googleapis.com/calendar/v3/freeBusy';

interface BusySlot {
  start: string;
  end: string;
}

export const syncCalendar = async (memberId: string): Promise<BusySlot[]> => {
  const accessToken = await getValidAccessToken();
  if (!accessToken) {
    throw new Error('No valid Google access token. Please reconnect your calendar.');
  }

  const now = new Date();
  const fourteenDaysLater = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);

  const response = await fetch(FREEBUSY_ENDPOINT, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      timeMin: now.toISOString(),
      timeMax: fourteenDaysLater.toISOString(),
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      items: [{ id: 'primary' }], // Primary calendar; FreeBusy aggregates all visible calendars
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`FreeBusy API error: ${response.status} - ${errorBody}`);
  }

  const data = await response.json();

  // Extract busy blocks from the primary calendar response
  // The FreeBusy API returns: { calendars: { primary: { busy: [{ start, end }] } } }
  const busySlots: BusySlot[] = data.calendars?.primary?.busy ?? [];

  // Store in Supabase -- upsert because calendar_masks has UNIQUE on member_id
  const { error } = await supabase
    .from('calendar_masks')
    .upsert(
      {
        member_id: memberId,
        busy_slots: busySlots,
        synced_at: new Date().toISOString(),
      },
      { onConflict: 'member_id' }
    );

  if (error) throw error;

  return busySlots;
};
```

### Privacy Enforcement

The FreeBusy API is specifically designed for privacy -- it returns ONLY start/end times of busy periods, never event details. This is enforced at the API level by Google. However, we add an additional safeguard:

```typescript
// Strip any unexpected fields from the response -- defense in depth
const sanitizeBusySlots = (slots: any[]): BusySlot[] => {
  return slots.map((slot) => ({
    start: slot.start,
    end: slot.end,
    // Explicitly exclude any other fields that might appear
  }));
};
```

### Sync Triggers

Calendar sync should happen at three points:

1. **On OAuth completion** (Story 6.1) -- immediately after first auth
2. **On app foreground** -- when the app becomes active and last sync was >6 hours ago
3. **Before suggestion generation** -- ensure fresh data before computing availability (Story 6.3)

```typescript
// lib/hooks/use-calendar-sync.ts
import { useEffect } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { syncCalendar } from '../calendar/sync-calendar';
import { useAuthStore } from '../stores/auth-store';

const SIX_HOURS_MS = 6 * 60 * 60 * 1000;

export const useCalendarSync = () => {
  const { memberId, isGoogleConnected } = useAuthStore();

  useEffect(() => {
    if (!isGoogleConnected || !memberId) return;

    // Sync on mount
    const doSync = async () => {
      try {
        const lastSync = await getLastSyncTime(memberId);
        if (!lastSync || Date.now() - new Date(lastSync).getTime() > SIX_HOURS_MS) {
          await syncCalendar(memberId);
        }
      } catch (err) {
        console.warn('Calendar sync failed:', err);
      }
    };

    doSync();

    // Sync when app returns to foreground
    const handleAppState = (state: AppStateStatus) => {
      if (state === 'active') doSync();
    };

    const subscription = AppState.addEventListener('change', handleAppState);
    return () => subscription.remove();
  }, [memberId, isGoogleConnected]);
};

const getLastSyncTime = async (memberId: string): Promise<string | null> => {
  const { data } = await supabase
    .from('calendar_masks')
    .select('synced_at')
    .eq('member_id', memberId)
    .single();

  return data?.synced_at ?? null;
};
```

### Error Handling

| Error | Handling |
|-------|----------|
| Access token expired | Auto-refresh via `getValidAccessToken()` (Story 6.1) |
| Refresh token revoked | Clear tokens, show "Reconnect Calendar" prompt |
| Network error | Retry once, then log warning. Use stale data if available. |
| API rate limit | Back off, retry after delay. Calendar data is not time-critical. |

### Data Staleness

Calendar masks have a `synced_at` timestamp. The suggestion engine (Story 6.3) can check staleness and trigger a sync if the data is older than a threshold (e.g., 24 hours).

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `lib/calendar/sync-calendar.ts` | Core function: calls FreeBusy API, sanitizes data, upserts to calendar_masks |
| `lib/hooks/use-calendar-sync.ts` | Hook that triggers sync on mount, foreground, and on-demand |

### Modify

| File | Change |
|------|--------|
| `lib/hooks/use-google-auth.ts` | After successful OAuth, trigger initial calendar sync |
| `lib/stores/auth-store.ts` | Add `lastCalendarSync` state and `isSyncing` loading state |
| `app/(tabs)/profile.tsx` | Show last sync time and manual "Refresh" button |

## Definition of Done

- [ ] Google Calendar FreeBusy API called with next 14 days window
- [ ] Only busy time blocks (start/end) extracted -- no event titles, descriptions, or attendees (NFR6)
- [ ] Busy slots stored as JSON array in `calendar_masks.busy_slots` via upsert
- [ ] `synced_at` timestamp updated on each sync
- [ ] Empty calendar results in `busy_slots: []` (member treated as fully available)
- [ ] Sync triggered on OAuth completion, app foreground (if stale), and on-demand
- [ ] Token refresh handled automatically if access token is expired (NFR14)
- [ ] Network errors handled gracefully -- stale data used as fallback
- [ ] Multiple calendars aggregated correctly by the FreeBusy API
- [ ] Privacy: defense-in-depth sanitization strips any unexpected fields from API response
- [ ] Profile screen shows last sync time
