# Story 7.1: Auto-Create Event Page

## Description

As the system,
I want to automatically create an event memory page when enough members commit to a suggestion,
So that the event has a container for photos, memories, and narrative before it even happens.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** a suggestion is active on a board
**When** the number of commitments with status = 'in' reaches 3 or more
**Then** an `events` row is automatically created in the database

**Given** an event row is created
**When** it is initialized
**Then** it is pre-filled with:
  - `suggestion_id` linking back to the originating suggestion
  - `board_id` from the suggestion
  - `photos` as an empty JSON array `[]`
  - `memories` as an empty JSON array `[]`
  - `narrative` as null (generated later)
  - `created_at` as the current timestamp

**Given** an event already exists for a suggestion
**When** another member votes "in" (4th, 5th, etc.)
**Then** no duplicate event row is created (idempotent)

**Given** an event has been created
**When** a board member navigates to the suggestion
**Then** they see a new "Event Page" link/button below the commitment section
**And** tapping it navigates to the event detail screen

**Given** a suggestion reaches 3 "in" votes and an event is created
**When** the suggestion status has not been manually changed
**Then** the suggestion status is updated to 'completed'

## Technical Context

### Relevant Schema

```sql
events (
  id uuid PK DEFAULT gen_random_uuid(),
  suggestion_id uuid FK REFERENCES suggestions(id),
  board_id uuid FK REFERENCES boards(id),
  photos jsonb DEFAULT '[]',
  memories jsonb DEFAULT '[]',
  narrative text,
  created_at timestamptz DEFAULT now()
)

suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb,
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
  created_at timestamptz
)

commitments (
  id uuid PK,
  suggestion_id uuid FK,
  member_id uuid FK,
  status text CHECK (status IN ('in', 'maybe', 'out')),
  receipt_url text,
  updated_at timestamptz,
  UNIQUE(suggestion_id, member_id)
)
```

### Architecture References

- **Trigger:** Client-side check after commitment upsert, or database trigger on commitments table
- **Screen:** `app/(tabs)/event/[id].tsx` -- New event detail screen (to be created)
- **Store:** `lib/stores/commitment-store.ts` -- Check threshold and create event
- **Components:** `components/memory/EventPage.tsx` -- Event page layout
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 5.1 (voting) -- commitments exist
- **Requires:** Epic 4 (suggestions exist with suggestion_data)
- **Downstream:** Story 7.2 (photo drop), Story 7.3 (one-line memory), Story 7.4 (AI narrative), Story 7.5 (group timeline)

## Implementation Notes

### Event Creation Logic

**Option A: Client-side (recommended for hackathon)**

After each "in" vote, the client checks if the threshold is met and creates the event:

```typescript
// In commitment-store.ts or a dedicated hook

const checkAndCreateEvent = async (suggestionId: string, boardId: string) => {
  // Count "in" commitments
  const { count } = await supabase
    .from('commitments')
    .select('*', { count: 'exact', head: true })
    .eq('suggestion_id', suggestionId)
    .eq('status', 'in');

  if (!count || count < 3) return null;

  // Check if event already exists for this suggestion
  const { data: existingEvent } = await supabase
    .from('events')
    .select('id')
    .eq('suggestion_id', suggestionId)
    .single();

  if (existingEvent) return existingEvent.id; // Already created

  // Create event
  const { data: newEvent, error } = await supabase
    .from('events')
    .insert({
      suggestion_id: suggestionId,
      board_id: boardId,
      photos: [],
      memories: [],
      narrative: null,
    })
    .select('id')
    .single();

  if (error) {
    // Handle race condition: another client may have created it simultaneously
    if (error.code === '23505') { // Unique violation
      const { data: existing } = await supabase
        .from('events')
        .select('id')
        .eq('suggestion_id', suggestionId)
        .single();
      return existing?.id ?? null;
    }
    throw error;
  }

  // Mark suggestion as completed
  await supabase
    .from('suggestions')
    .update({ status: 'completed' })
    .eq('id', suggestionId);

  return newEvent.id;
};
```

**Option B: Database trigger (more robust but harder to debug)**

```sql
CREATE OR REPLACE FUNCTION auto_create_event()
RETURNS trigger AS $$
DECLARE
  in_count integer;
  existing_event_id uuid;
  board uuid;
BEGIN
  IF NEW.status = 'in' THEN
    -- Count "in" commitments for this suggestion
    SELECT COUNT(*) INTO in_count
    FROM commitments
    WHERE suggestion_id = NEW.suggestion_id AND status = 'in';

    IF in_count >= 3 THEN
      -- Check if event already exists
      SELECT id INTO existing_event_id
      FROM events
      WHERE suggestion_id = NEW.suggestion_id;

      IF existing_event_id IS NULL THEN
        -- Get board_id from suggestion
        SELECT board_id INTO board
        FROM suggestions
        WHERE id = NEW.suggestion_id;

        -- Create event
        INSERT INTO events (suggestion_id, board_id, photos, memories)
        VALUES (NEW.suggestion_id, board, '[]'::jsonb, '[]'::jsonb);

        -- Mark suggestion as completed
        UPDATE suggestions SET status = 'completed'
        WHERE id = NEW.suggestion_id;
      END IF;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_commitment_check_event
  AFTER INSERT OR UPDATE ON commitments
  FOR EACH ROW
  EXECUTE FUNCTION auto_create_event();
```

### Preventing Duplicate Events

Add a unique constraint on `suggestion_id` in the events table to prevent race conditions:

```sql
ALTER TABLE events ADD CONSTRAINT events_suggestion_id_unique UNIQUE (suggestion_id);
```

### Event Detail Screen

```typescript
// app/(tabs)/event/[id].tsx
import { useLocalSearchParams } from 'expo-router';
import { EventPage } from '../../../components/memory/EventPage';

export default function EventDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  return <EventPage eventId={id} />;
}
```

### EventPage Component Structure

```typescript
// components/memory/EventPage.tsx
const EventPage = ({ eventId }: { eventId: string }) => {
  const { event, suggestion, attendees, isLoading } = useEvent(eventId);

  if (isLoading) return <LoadingSpinner />;
  if (!event) return <Text>Event not found</Text>;

  const suggestionData = suggestion?.suggestion_data;

  return (
    <ScrollView>
      {/* Header with event details from suggestion */}
      <View style={styles.header}>
        <Text style={styles.title}>{suggestionData?.what}</Text>
        <Text style={styles.venue}>{suggestionData?.where}</Text>
        <Text style={styles.date}>{suggestionData?.when}</Text>
      </View>

      {/* Attendee avatars */}
      <View style={styles.attendees}>
        <Text style={styles.sectionTitle}>Going</Text>
        <AttendeeRow attendees={attendees} />
      </View>

      {/* Photo grid (Story 7.2) */}
      <PhotoGrid photos={event.photos} eventId={eventId} />

      {/* Memories section (Story 7.3) */}
      <MemoriesSection memories={event.memories} eventId={eventId} />

      {/* AI Narrative (Story 7.4) */}
      {event.narrative && <NarrativeSection narrative={event.narrative} />}
    </ScrollView>
  );
};
```

### useEvent Hook

```typescript
// lib/hooks/use-event.ts
export const useEvent = (eventId: string) => {
  const [event, setEvent] = useState<Event | null>(null);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [attendees, setAttendees] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchEvent = async () => {
      const { data: eventData } = await supabase
        .from('events')
        .select('*, suggestions(*, commitments(*, members(*)))')
        .eq('id', eventId)
        .single();

      if (eventData) {
        setEvent(eventData);
        setSuggestion(eventData.suggestions);
        // Attendees = members who voted "in"
        const inMembers = eventData.suggestions?.commitments
          ?.filter((c: any) => c.status === 'in')
          .map((c: any) => c.members) ?? [];
        setAttendees(inMembers);
      }
      setIsLoading(false);
    };

    fetchEvent();
  }, [eventId]);

  return { event, suggestion, attendees, isLoading };
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `app/(tabs)/event/[id].tsx` | Event detail screen with dynamic route |
| `components/memory/EventPage.tsx` | Main event page layout: header, attendees, photo grid, memories, narrative |
| `components/memory/AttendeeRow.tsx` | Horizontal row of attendee avatars for the event |
| `lib/hooks/use-event.ts` | Hook to fetch event data, joined with suggestion and attendees |

### Modify

| File | Change |
|------|--------|
| `lib/stores/commitment-store.ts` | After "in" vote upsert, call `checkAndCreateEvent` if count >= 3 |
| `app/(tabs)/suggestion/[id].tsx` | Show "View Event" button when an event exists for the suggestion |
| `app/(tabs)/_layout.tsx` | Add event route to tab navigator if needed |

## Definition of Done

- [ ] Event row auto-created when 3+ members vote "in" on a suggestion
- [ ] Event pre-filled with `suggestion_id`, `board_id`, empty `photos` and `memories` arrays
- [ ] No duplicate events created for the same suggestion (idempotent)
- [ ] Race condition handled (concurrent "in" votes don't create duplicate events)
- [ ] Suggestion status updated to 'completed' when event is created
- [ ] Event detail screen accessible via `event/[id]` route
- [ ] Event page shows suggestion details: what, where, when
- [ ] Event page shows attendee avatars (members who voted "in")
- [ ] "View Event" button/link appears on the suggestion screen after event creation
- [ ] Photo grid, memories section, and narrative section render (empty state for now, populated by Stories 7.2-7.4)
