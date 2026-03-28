# Story 7.3: One-Line Memory

## Description

As a member who attended an event,
I want to submit one sentence about the night,
So that the group builds a collective memory from everyone's individual perspective.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** an event page exists
**When** the user views the event page
**Then** a text input is displayed with the prompt "One thing you'll remember about tonight?"
**And** a submit button is next to the input

**Given** the user types a one-line memory and taps submit
**When** the memory is submitted
**Then** a `{ member_id, text, created_at }` object is appended to the `events.memories` jsonb array
**And** the input clears after successful submission
**And** the new memory appears in the memories list immediately

**Given** multiple members have submitted memories
**When** any board member views the event page
**Then** all memories are displayed in a list with:
  - The member's display name or avatar
  - The memory text
  - A relative timestamp (e.g., "2h ago")

**Given** a member has already submitted a memory
**When** they view the event page
**Then** their existing memory is shown
**And** they can submit additional memories (no limit per member)

**Given** a memory is submitted by another member while the current user is viewing the event page
**When** the update propagates
**Then** the new memory appears in the list via Realtime subscription

## Technical Context

### Relevant Schema

```sql
events (
  id uuid PK,
  suggestion_id uuid FK,
  board_id uuid FK,
  photos jsonb DEFAULT '[]',
  memories jsonb DEFAULT '[]',   -- Array of { member_id: uuid, text: string, created_at: string }
  narrative text,
  created_at timestamptz
)
```

**Example memories value:**

```json
[
  {
    "member_id": "uuid-priya",
    "text": "The queue was worth it.",
    "created_at": "2026-03-30T01:15:00Z"
  },
  {
    "member_id": "uuid-tom",
    "text": "Mehrdad's dance moves were unreal.",
    "created_at": "2026-03-30T01:22:00Z"
  },
  {
    "member_id": "uuid-sofia",
    "text": "The DJ played that one song from the reel.",
    "created_at": "2026-03-30T10:45:00Z"
  }
]
```

### Architecture References

- **Screen:** `app/(tabs)/event/[id].tsx` -- Memories section of the event page
- **Components:** `components/memory/MemoriesSection.tsx`, `components/memory/MemoryInput.tsx`, `components/memory/MemoryItem.tsx`
- **Store:** Extend `use-event.ts` hook or create dedicated `use-memories.ts` hook
- **Realtime:** Subscribe to event row updates to catch new memories from other members
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 7.1 (event page exists)
- **Requires:** Member data available (display_name for attribution)
- **Downstream:** Story 7.4 (AI narrative uses memories as input)

## Implementation Notes

### Submit Memory

```typescript
// lib/hooks/use-memories.ts
const submitMemory = async (
  eventId: string,
  memberId: string,
  text: string
) => {
  // Fetch current memories
  const { data: event } = await supabase
    .from('events')
    .select('memories')
    .eq('id', eventId)
    .single();

  const currentMemories = (event?.memories as any[]) ?? [];

  const newMemory = {
    member_id: memberId,
    text: text.trim(),
    created_at: new Date().toISOString(),
  };

  const updatedMemories = [...currentMemories, newMemory];

  const { error } = await supabase
    .from('events')
    .update({ memories: updatedMemories })
    .eq('id', eventId);

  if (error) throw error;

  return newMemory;
};
```

**Production-safe RPC (for concurrent writes):**

```sql
CREATE OR REPLACE FUNCTION append_event_memory(
  p_event_id uuid,
  p_member_id uuid,
  p_text text
) RETURNS void AS $$
BEGIN
  UPDATE events
  SET memories = memories || jsonb_build_array(
    jsonb_build_object(
      'member_id', p_member_id,
      'text', p_text,
      'created_at', now()
    )
  )
  WHERE id = p_event_id;
END;
$$ LANGUAGE plpgsql;
```

### Memory Input Component

```typescript
// components/memory/MemoryInput.tsx
import { useState } from 'react';
import { View, TextInput, TouchableOpacity, Text, StyleSheet } from 'react-native';

interface MemoryInputProps {
  onSubmit: (text: string) => Promise<void>;
}

const MemoryInput = ({ onSubmit }: MemoryInputProps) => {
  const [text, setText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onSubmit(text.trim());
      setText(''); // Clear after success
    } catch (err) {
      Alert.alert('Error', 'Failed to save your memory. Try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.prompt}>One thing you'll remember about tonight?</Text>
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={setText}
          placeholder="Type your memory..."
          maxLength={200}
          returnKeyType="send"
          onSubmitEditing={handleSubmit}
        />
        <TouchableOpacity
          style={[styles.submitButton, (!text.trim() || isSubmitting) && styles.disabled]}
          onPress={handleSubmit}
          disabled={!text.trim() || isSubmitting}
        >
          <Text style={styles.submitText}>
            {isSubmitting ? '...' : 'Send'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};
```

### Memory List Component

```typescript
// components/memory/MemoryItem.tsx
import { View, Text, StyleSheet } from 'react-native';

interface MemoryItemProps {
  displayName: string;
  avatarUrl?: string;
  text: string;
  createdAt: string;
}

const MemoryItem = ({ displayName, text, createdAt }: MemoryItemProps) => {
  const timeAgo = getRelativeTime(createdAt); // e.g., "2h ago"

  return (
    <View style={styles.memoryItem}>
      <View style={styles.header}>
        <Text style={styles.name}>{displayName}</Text>
        <Text style={styles.time}>{timeAgo}</Text>
      </View>
      <Text style={styles.text}>"{text}"</Text>
    </View>
  );
};

// Utility for relative time
const getRelativeTime = (isoString: string): string => {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};
```

### Realtime Updates for Memories

Subscribe to the event row to receive new memories from other members:

```typescript
// In use-event.ts or use-memories.ts
useEffect(() => {
  const channel = supabase
    .channel(`event-memories:${eventId}`)
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'events',
        filter: `id=eq.${eventId}`,
      },
      (payload) => {
        // Update local memories state
        const updatedMemories = payload.new.memories as MemoryItem[];
        setMemories(updatedMemories);
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}, [eventId]);
```

### Memories Section Layout

```typescript
// components/memory/MemoriesSection.tsx
const MemoriesSection = ({ memories, eventId, members }: Props) => {
  const { memberId } = useAuthStore();

  const handleSubmit = async (text: string) => {
    await submitMemory(eventId, memberId!, text);
  };

  // Resolve member names
  const memoriesWithNames = memories.map((m) => ({
    ...m,
    displayName: members.find((mem) => mem.id === m.member_id)?.display_name ?? 'Unknown',
  }));

  return (
    <View>
      <Text style={styles.sectionTitle}>Memories</Text>

      {/* Memory input */}
      <MemoryInput onSubmit={handleSubmit} />

      {/* Memory list */}
      {memoriesWithNames.length === 0 ? (
        <Text style={styles.emptyState}>No memories yet. Be the first!</Text>
      ) : (
        memoriesWithNames.map((m, index) => (
          <MemoryItem
            key={`${m.member_id}-${index}`}
            displayName={m.displayName}
            text={m.text}
            createdAt={m.created_at}
          />
        ))
      )}
    </View>
  );
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/memory/MemoriesSection.tsx` | Container for memory input and list |
| `components/memory/MemoryInput.tsx` | Text input with prompt and submit button |
| `components/memory/MemoryItem.tsx` | Individual memory display with name and timestamp |
| `lib/hooks/use-memories.ts` | Hook for submitting memories and subscribing to updates |

### Modify

| File | Change |
|------|--------|
| `components/memory/EventPage.tsx` | Integrate MemoriesSection into the event page layout |
| `lib/hooks/use-event.ts` | Include Realtime subscription for event memories updates |

## Definition of Done

- [ ] Text input displayed on event page with prompt "One thing you'll remember about tonight?"
- [ ] User can type and submit a one-line memory (max 200 characters)
- [ ] Submitted memory appended to `events.memories` jsonb array as `{ member_id, text, created_at }`
- [ ] Input clears after successful submission
- [ ] All memories displayed in a list with member name and relative timestamp
- [ ] Members can submit multiple memories (no limit)
- [ ] New memories from other members appear via Realtime subscription
- [ ] Empty state shows "No memories yet. Be the first!" when no memories exist
- [ ] Submit button disabled while submitting (prevents double-submit)
- [ ] Error handling: failed submit shows alert and preserves input text
- [ ] Memory attribution: each memory shows the display name of the member who wrote it
