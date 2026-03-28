# Story 5.4: Private Nudge to Uncommitted Members

## Description

As the system,
I want to privately nudge members who haven't committed when a majority of the group has,
So that social pressure drives follow-through without public embarrassment.

## Status

- **Epic:** Commitment & Social Pressure
- **Priority:** P1
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B

## Acceptance Criteria

**Given** a suggestion is active on a board with N members
**When** the number of commitments with status = 'in' exceeds 50% of board members (i.e., count > N/2)
**Then** the system identifies members who do NOT have an 'in' commitment (including 'maybe', 'out', or no vote)

**Given** uncommitted members are identified after majority threshold is crossed
**When** the nudge is triggered
**Then** each uncommitted member receives a private push notification
**And** the notification message reads: "[X] of your friends have confirmed for [when]. Still interested in [what]?"
**And** the notification comes from the app -- it is NOT attributed to any specific member
**And** the notification deep-links to the suggestion screen

**Given** a member has already been nudged for a specific suggestion
**When** the threshold check runs again (e.g., another member votes "in")
**Then** the nudge is NOT sent again to already-nudged members (idempotent)

**Given** a board has only 2 members
**When** 1 member votes "in" (50% exactly)
**Then** the nudge is NOT sent (threshold is strictly greater than 50%)

**Given** a board has 5 members and 3 vote "in"
**When** the 3rd "in" vote is cast (60% > 50%)
**Then** the remaining 2 members each receive a private nudge

## Technical Context

### Relevant Schema

```sql
commitments (
  id uuid PK,
  suggestion_id uuid FK,
  member_id uuid FK,
  status text CHECK (status IN ('in', 'maybe', 'out')),
  receipt_url text,
  updated_at timestamptz,
  UNIQUE(suggestion_id, member_id)
)

members (
  id uuid PK,
  board_id uuid FK,
  display_name text,
  device_id text,
  push_token text
)

suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb,  -- { what, why, where, when, cost_per_person, ... }
  status text DEFAULT 'active',
  created_at timestamptz
)
```

### Architecture References

- **Trigger:** Supabase Database Webhook or Edge Function triggered by commitment INSERT/UPDATE
- **Edge Function:** `supabase/functions/nudge-check/index.ts`
- **Push Service:** Expo Push Notifications API
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 5.1 (voting) -- commitments must exist
- **Requires:** Story 5.3 (decay-check) -- push notification infrastructure (push token registration)
- **Requires:** Members have `push_token` stored
- **Requires:** Board member count accessible via `members` table

## Implementation Notes

### Trigger Strategy

**Recommended: Database Webhook on commitments table**

When a commitment is inserted or updated to status = 'in', fire a webhook to the `nudge-check` Edge Function. This is more event-driven than polling.

```sql
-- Supabase Database Webhook configuration
-- Trigger on INSERT and UPDATE on commitments table
-- When status = 'in', call nudge-check Edge Function
```

Alternatively, call the nudge-check logic directly from the `decay-check` cron, but the webhook approach gives real-time nudges when the threshold is crossed.

### Edge Function: nudge-check

```typescript
// supabase/functions/nudge-check/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { suggestion_id } = await req.json();

  if (!suggestion_id) {
    return new Response(JSON.stringify({ error: 'suggestion_id required' }), { status: 400 });
  }

  // Get the suggestion
  const { data: suggestion, error: sugErr } = await supabase
    .from('suggestions')
    .select('id, board_id, suggestion_data')
    .eq('id', suggestion_id)
    .eq('status', 'active')
    .single();

  if (sugErr || !suggestion) {
    return new Response(JSON.stringify({ error: 'Suggestion not found or inactive' }), { status: 404 });
  }

  // Count total board members
  const { count: totalMembers } = await supabase
    .from('members')
    .select('*', { count: 'exact', head: true })
    .eq('board_id', suggestion.board_id);

  // Get members who committed "in"
  const { data: inCommitments } = await supabase
    .from('commitments')
    .select('member_id')
    .eq('suggestion_id', suggestion_id)
    .eq('status', 'in');

  const inCount = inCommitments?.length ?? 0;
  const threshold = (totalMembers ?? 0) / 2;

  // Strictly greater than 50%
  if (inCount <= threshold) {
    return new Response(JSON.stringify({ nudged: 0, reason: 'Below threshold' }), { status: 200 });
  }

  // Check if nudge already sent for this suggestion
  if (suggestion.suggestion_data?._nudge_sent) {
    return new Response(JSON.stringify({ nudged: 0, reason: 'Already nudged' }), { status: 200 });
  }

  const inMemberIds = new Set(inCommitments?.map((c) => c.member_id) ?? []);

  // Get all board members who are NOT "in"
  const { data: allMembers } = await supabase
    .from('members')
    .select('id, push_token')
    .eq('board_id', suggestion.board_id)
    .not('push_token', 'is', null);

  const uncommittedMembers = allMembers?.filter((m) => !inMemberIds.has(m.id)) ?? [];

  if (uncommittedMembers.length === 0) {
    return new Response(JSON.stringify({ nudged: 0, reason: 'All committed' }), { status: 200 });
  }

  const what = suggestion.suggestion_data?.what ?? 'the plan';
  const when = suggestion.suggestion_data?.when ?? 'soon';

  const pushMessages = uncommittedMembers
    .filter((m) => m.push_token)
    .map((m) => ({
      to: m.push_token,
      title: 'Your friends are going!',
      body: `${inCount} of your friends have confirmed for ${when}. Still interested in ${what}?`,
      data: { suggestionId: suggestion_id, type: 'private_nudge' },
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

  // Mark suggestion as nudged to prevent duplicate nudges
  await supabase
    .from('suggestions')
    .update({
      suggestion_data: {
        ...suggestion.suggestion_data,
        _nudge_sent: true,
      },
    })
    .eq('id', suggestion_id);

  return new Response(
    JSON.stringify({ nudged: uncommittedMembers.length }),
    { status: 200, headers: { 'Content-Type': 'application/json' } }
  );
});
```

### Triggering the Nudge Check

**Option A: Client-side trigger after vote**

After a successful commitment upsert with status = 'in', the client calls the nudge-check Edge Function:

```typescript
// In commitment-store.ts, after successful upsert
if (status === 'in') {
  await supabase.functions.invoke('nudge-check', {
    body: { suggestion_id: suggestionId },
  });
}
```

**Option B: Supabase Database Trigger + pg_net**

```sql
CREATE OR REPLACE FUNCTION trigger_nudge_check()
RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'in' THEN
    PERFORM net.http_post(
      'https://ubhbeqnagxbuoikzftht.supabase.co/functions/v1/nudge-check',
      jsonb_build_object('suggestion_id', NEW.suggestion_id)::text,
      'application/json',
      ARRAY[http_header('Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'))]
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_commitment_in
  AFTER INSERT OR UPDATE ON commitments
  FOR EACH ROW
  EXECUTE FUNCTION trigger_nudge_check();
```

Option A is simpler and recommended for the hackathon.

### Privacy Design

The nudge notification is intentionally anonymous:
- Title: "Your friends are going!" (not "Tom, Priya, and Mehrdad confirmed")
- Body: Uses a count, not names
- Source: The app itself, not any member
- No attribution of who asked for the nudge (because nobody did -- it's automatic)

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/nudge-check/index.ts` | Edge Function that checks majority threshold and sends private nudges |

### Modify

| File | Change |
|------|--------|
| `lib/stores/commitment-store.ts` | After successful "in" vote upsert, invoke nudge-check Edge Function |
| `lib/hooks/use-push-notifications.ts` | Handle `private_nudge` notification type for deep-linking |

## Definition of Done

- [ ] Edge Function `nudge-check` deployed and callable
- [ ] Function correctly calculates >50% threshold based on total board member count
- [ ] Uncommitted members receive private push notifications when threshold is crossed
- [ ] Notification message includes the count of confirmed friends and the suggestion's when/what
- [ ] Notification is anonymous -- does not reveal which members committed
- [ ] Nudge is sent only once per suggestion (idempotent via `_nudge_sent` flag)
- [ ] Members who already voted "in" do NOT receive the nudge
- [ ] Edge case: board with 2 members, 1 "in" = no nudge (50% exactly, not >50%)
- [ ] Edge case: all members voted "in" = no nudge needed
- [ ] Notification tap deep-links to the suggestion screen
- [ ] Function handles missing push tokens gracefully (skips members without tokens)
