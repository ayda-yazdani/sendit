# Story 5.3: Decay Reminder Notification

## Description

As a board member,
I want to get a nudge if nobody acts on a suggestion within 72 hours,
So that good plans don't die silently in the app.

## Status

- **Epic:** Commitment & Social Pressure
- **Priority:** P1
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B

## Acceptance Criteria

**Given** a suggestion has been active for 72 hours (created_at + 72hr <= now)
**When** the system checks for stale suggestions
**Then** it queries the `commitments` table for that suggestion
**And** if zero members have status = 'in', the suggestion qualifies for a decay reminder

**Given** a suggestion qualifies for a decay reminder
**When** the reminder is triggered
**Then** a push notification is sent to ALL board members via Expo Push Notifications
**And** the notification message reads: "Still interested in [suggestion what]? No one's committed yet -- don't let it die."
**And** the notification deep-links to the suggestion screen when tapped

**Given** a suggestion already has at least one "in" commitment
**When** the 72-hour check runs
**Then** no decay reminder is sent for that suggestion

**Given** the decay reminder has already been sent for a suggestion
**When** the check runs again
**Then** the reminder is NOT sent a second time (idempotent)

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

members (
  id uuid PK,
  board_id uuid FK,
  display_name text,
  device_id text,
  push_token text           -- Expo push token for notifications
)
```

### Architecture References

- **Edge Function:** `supabase/functions/decay-check/index.ts` -- Scheduled function that runs periodically
- **Trigger:** Supabase pg_cron or external cron (e.g., Supabase scheduled Edge Function invocation via `pg_net` or a cron webhook)
- **Push Service:** Expo Push Notifications API (`https://exp.host/--/api/v2/push/send`)
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Suggestions exist in the `suggestions` table (Epic 4)
- **Requires:** Members have `push_token` stored (push notification registration from onboarding)
- **Requires:** `expo-notifications` configured on the client for receiving push notifications
- **Requires:** Story 5.1 (voting) for commitment data

## Implementation Notes

### Edge Function: decay-check

This Edge Function is invoked on a schedule (e.g., every hour) and checks all active suggestions that have passed the 72-hour threshold.

```typescript
// supabase/functions/decay-check/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const seventyTwoHoursAgo = new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString();

  // Find active suggestions older than 72 hours
  const { data: staleSuggestions, error: sugError } = await supabase
    .from('suggestions')
    .select('id, board_id, suggestion_data')
    .eq('status', 'active')
    .lt('created_at', seventyTwoHoursAgo);

  if (sugError || !staleSuggestions?.length) {
    return new Response(JSON.stringify({ checked: 0 }), { status: 200 });
  }

  for (const suggestion of staleSuggestions) {
    // Check if anyone has committed "in"
    const { count } = await supabase
      .from('commitments')
      .select('*', { count: 'exact', head: true })
      .eq('suggestion_id', suggestion.id)
      .eq('status', 'in');

    if (count && count > 0) continue; // Someone committed, skip

    // Get all board members with push tokens
    const { data: members } = await supabase
      .from('members')
      .select('push_token')
      .eq('board_id', suggestion.board_id)
      .not('push_token', 'is', null);

    if (!members?.length) continue;

    const what = suggestion.suggestion_data?.what ?? 'your plan';

    // Send push notifications via Expo
    const pushMessages = members
      .filter((m) => m.push_token)
      .map((m) => ({
        to: m.push_token,
        title: 'Plan fading...',
        body: `Still interested in ${what}? No one's committed yet -- don't let it die.`,
        data: { suggestionId: suggestion.id, type: 'decay_reminder' },
        sound: 'default',
      }));

    if (pushMessages.length > 0) {
      await fetch('https://exp.host/--/api/v2/push/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(pushMessages),
      });
    }

    // Mark suggestion so we don't send duplicate reminders
    // Use a jsonb field or a separate tracking mechanism
    await supabase
      .from('suggestions')
      .update({
        suggestion_data: {
          ...suggestion.suggestion_data,
          _decay_reminder_sent: true,
        },
      })
      .eq('id', suggestion.id);
  }

  return new Response(
    JSON.stringify({ checked: staleSuggestions.length }),
    { status: 200, headers: { 'Content-Type': 'application/json' } }
  );
});
```

### Idempotency

To prevent duplicate reminders, the function checks for a `_decay_reminder_sent` flag inside `suggestion_data`. The query should be extended:

```typescript
// Add to the initial query filter
.not('suggestion_data->_decay_reminder_sent', 'eq', 'true')
```

### Scheduling the Edge Function

**Option A: Supabase pg_cron (recommended)**

```sql
SELECT cron.schedule(
  'decay-check',
  '0 * * * *',  -- Every hour
  $$
  SELECT net.http_post(
    'https://ubhbeqnagxbuoikzftht.supabase.co/functions/v1/decay-check',
    '{}',
    'application/json',
    ARRAY[
      ('Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'))::net.http_header
    ]
  );
  $$
);
```

**Option B: External cron (e.g., GitHub Actions, Vercel cron)**

Call the Edge Function endpoint with the service role key on a schedule.

### Client-Side: Handling Push Notification Tap

```typescript
import * as Notifications from 'expo-notifications';

// In app root layout
Notifications.addNotificationResponseReceivedListener((response) => {
  const data = response.notification.request.content.data;
  if (data.type === 'decay_reminder' && data.suggestionId) {
    router.push(`/suggestion/${data.suggestionId}`);
  }
});
```

### Push Token Registration

Ensure the client registers for push notifications and saves the token to the member row:

```typescript
import * as Notifications from 'expo-notifications';

const registerForPush = async (memberId: string) => {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return;

  const token = (await Notifications.getExpoPushTokenAsync()).data;

  await supabase
    .from('members')
    .update({ push_token: token })
    .eq('id', memberId);
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/decay-check/index.ts` | Edge Function that checks for stale suggestions and sends decay reminders |
| `lib/hooks/use-push-notifications.ts` | Hook for registering push token and handling notification taps |

### Modify

| File | Change |
|------|--------|
| `app/_layout.tsx` | Initialize push notification listener for deep-linking on notification tap |
| `lib/stores/auth-store.ts` | Add push token registration on member creation/login |

## Definition of Done

- [ ] Edge Function `decay-check` deployed and callable
- [ ] Function identifies active suggestions older than 72 hours with zero "in" commitments
- [ ] Push notifications sent to all board members with valid push tokens
- [ ] Notification message includes the suggestion name (what field)
- [ ] Notification taps deep-link to the suggestion screen
- [ ] Duplicate reminders are prevented (idempotent -- sent only once per suggestion)
- [ ] Suggestions that already have "in" commitments are skipped
- [ ] Scheduling mechanism configured (pg_cron or external cron)
- [ ] Client registers push token on app launch and saves to member row
- [ ] Edge Function handles edge cases: no members with tokens, missing suggestion_data
- [ ] Function returns a count of suggestions checked for monitoring
