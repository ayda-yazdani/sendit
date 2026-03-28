# Story 7.5: Group Timeline

## Description

As a board member,
I want a scrollable timeline of all past events our group has done,
So that I can relive our group's history and see how far we've come.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** a board has 1 or more completed events
**When** the user navigates to the timeline screen
**Then** all events are displayed chronologically (most recent first)
**And** each event card shows:
  - Date (formatted as "Saturday 29 March 2026")
  - Venue/activity name (from suggestion_data.what and suggestion_data.where)
  - A thumbnail of the first uploaded photo (or a placeholder if no photos)
  - A preview of the narrative (first 100 characters, truncated with "...")
  - Number of attendees
  - Number of photos

**Given** the user taps on an event card in the timeline
**When** the tap is registered
**Then** the user is navigated to the full event detail page (Story 7.1)

**Given** a board has no completed events
**When** the user views the timeline screen
**Then** an empty state is displayed: "No memories yet. Your first event is just one suggestion away."
**And** a CTA links to the active suggestion (if one exists)

**Given** a new event is created (Story 7.1)
**When** the timeline screen is next viewed
**Then** the new event appears at the top of the list

**Given** the timeline has 10+ events
**When** the user scrolls through
**Then** the list scrolls smoothly with no jank
**And** images lazy-load as they scroll into view

## Technical Context

### Relevant Schema

```sql
events (
  id uuid PK,
  suggestion_id uuid FK,
  board_id uuid FK,
  photos jsonb DEFAULT '[]',
  memories jsonb DEFAULT '[]',
  narrative text,
  created_at timestamptz
)

suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb   -- { what, why, where, when, cost_per_person, booking_url, influenced_by[] }
)

commitments (
  id uuid PK,
  suggestion_id uuid FK,
  member_id uuid FK,
  status text,
  UNIQUE(suggestion_id, member_id)
)
```

### Architecture References

- **Screen:** `app/(tabs)/timeline.tsx` -- New tab or screen for the timeline
- **Components:** `components/memory/TimelineScreen.tsx`, `components/memory/TimelineCard.tsx`
- **Navigation:** Add "Timeline" or "Memories" tab to the bottom tab navigator
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 7.1 (events exist)
- **Requires:** Story 7.2 (photos for thumbnails), Story 7.4 (narrative for preview) -- both optional but enhance the display
- **Requires:** Epic 4 (suggestions with suggestion_data for event details)

## Implementation Notes

### Data Fetching

```typescript
// lib/hooks/use-timeline.ts
import { useState, useEffect } from 'react';
import { supabase } from '../supabase';

interface TimelineEvent {
  id: string;
  suggestion_id: string;
  board_id: string;
  photos: { url: string; member_id: string; uploaded_at: string }[];
  memories: { member_id: string; text: string; created_at: string }[];
  narrative: string | null;
  created_at: string;
  suggestion: {
    suggestion_data: {
      what: string;
      where: string;
      when: string;
      cost_per_person?: string;
    };
  };
  attendee_count: number;
}

export const useTimeline = (boardId: string) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTimeline = async () => {
      setIsLoading(true);

      // Fetch events with their suggestion data
      const { data: eventsData, error } = await supabase
        .from('events')
        .select(`
          id,
          suggestion_id,
          board_id,
          photos,
          memories,
          narrative,
          created_at,
          suggestions (
            suggestion_data
          )
        `)
        .eq('board_id', boardId)
        .order('created_at', { ascending: false });

      if (error) {
        console.error('Timeline fetch error:', error);
        setIsLoading(false);
        return;
      }

      // For each event, count attendees
      const eventsWithCounts = await Promise.all(
        (eventsData ?? []).map(async (event) => {
          const { count } = await supabase
            .from('commitments')
            .select('*', { count: 'exact', head: true })
            .eq('suggestion_id', event.suggestion_id)
            .eq('status', 'in');

          return {
            ...event,
            suggestion: event.suggestions,
            attendee_count: count ?? 0,
          };
        })
      );

      setEvents(eventsWithCounts);
      setIsLoading(false);
    };

    if (boardId) fetchTimeline();
  }, [boardId]);

  return { events, isLoading };
};
```

### Timeline Card Component

```typescript
// components/memory/TimelineCard.tsx
import { View, Text, Image, TouchableOpacity, StyleSheet } from 'react-native';
import { router } from 'expo-router';

interface TimelineCardProps {
  event: TimelineEvent;
}

const TimelineCard = ({ event }: TimelineCardProps) => {
  const suggestionData = event.suggestion?.suggestion_data;
  const firstPhoto = event.photos?.[0]?.url;
  const narrativePreview = event.narrative
    ? event.narrative.length > 100
      ? event.narrative.substring(0, 100) + '...'
      : event.narrative
    : null;

  const formattedDate = new Date(event.created_at).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/event/${event.id}`)}
      activeOpacity={0.7}
    >
      {/* Photo thumbnail */}
      <View style={styles.thumbnailContainer}>
        {firstPhoto ? (
          <Image
            source={{ uri: firstPhoto }}
            style={styles.thumbnail}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.placeholderThumbnail}>
            <Text style={styles.placeholderIcon}>&#x1F4F7;</Text>
          </View>
        )}
      </View>

      {/* Event details */}
      <View style={styles.details}>
        <Text style={styles.date}>{formattedDate}</Text>
        <Text style={styles.title} numberOfLines={1}>
          {suggestionData?.what ?? 'Event'}
        </Text>
        <Text style={styles.venue} numberOfLines={1}>
          {suggestionData?.where ?? ''}
        </Text>

        {narrativePreview && (
          <Text style={styles.narrative} numberOfLines={2}>
            {narrativePreview}
          </Text>
        )}

        {/* Stats row */}
        <View style={styles.statsRow}>
          <Text style={styles.stat}>{event.attendee_count} went</Text>
          <Text style={styles.stat}>{event.photos?.length ?? 0} photos</Text>
          <Text style={styles.stat}>{event.memories?.length ?? 0} memories</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  thumbnailContainer: {
    width: 80,
    height: 80,
    borderRadius: 8,
    overflow: 'hidden',
    marginRight: 12,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  placeholderThumbnail: {
    width: '100%',
    height: '100%',
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderIcon: {
    fontSize: 24,
  },
  details: {
    flex: 1,
  },
  date: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 2,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 2,
  },
  venue: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 4,
  },
  narrative: {
    fontSize: 13,
    color: '#374151',
    fontStyle: 'italic',
    marginBottom: 6,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  stat: {
    fontSize: 12,
    color: '#9CA3AF',
  },
});
```

### Timeline Screen

```typescript
// app/(tabs)/timeline.tsx
import { FlatList, View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { router } from 'expo-router';
import { useTimeline } from '../../lib/hooks/use-timeline';
import { TimelineCard } from '../../components/memory/TimelineCard';
import { useBoardStore } from '../../lib/stores/board-store';

export default function TimelineScreen() {
  const activeBoardId = useBoardStore((s) => s.activeBoardId);
  const { events, isLoading } = useTimeline(activeBoardId!);

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (events.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No memories yet</Text>
        <Text style={styles.emptySubtitle}>
          Your first event is just one suggestion away.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={events}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <TimelineCard event={item} />}
      contentContainerStyle={styles.list}
      showsVerticalScrollIndicator={false}
    />
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
  list: {
    paddingVertical: 8,
  },
});
```

### Adding Timeline Tab

Add a "Memories" tab to the bottom tab navigator:

```typescript
// In app/(tabs)/_layout.tsx
<Tabs.Screen
  name="timeline"
  options={{
    title: 'Memories',
    tabBarIcon: ({ color }) => <TabBarIcon name="clock" color={color} />,
  }}
/>
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `app/(tabs)/timeline.tsx` | Timeline screen showing all past events for the active board |
| `components/memory/TimelineCard.tsx` | Card component for each event in the timeline |
| `lib/hooks/use-timeline.ts` | Hook to fetch and format timeline events for a board |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/_layout.tsx` | Add "Memories" tab pointing to timeline screen |

## Definition of Done

- [ ] Timeline screen accessible via "Memories" tab in bottom navigation
- [ ] All events for the active board displayed chronologically (most recent first)
- [ ] Each event card shows: date, activity name, venue, photo thumbnail, narrative preview, attendee count, photo count
- [ ] Tapping an event card navigates to the full event detail page
- [ ] Empty state displayed when no events exist with appropriate messaging
- [ ] Smooth scrolling with 10+ events (FlatList performance)
- [ ] Images lazy-load as they scroll into view
- [ ] Events without photos show a placeholder thumbnail
- [ ] Events without narrative skip the narrative preview
- [ ] New events appear at the top of the timeline when created
- [ ] Stats (attendees, photos, memories) are accurate
