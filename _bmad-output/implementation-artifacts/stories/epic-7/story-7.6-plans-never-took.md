# Story 7.6: Plans You Never Took

## Description

As a board member,
I want to see archived suggestions our group never acted on,
So that good ideas can be rediscovered and given a second chance.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** a board has one or more archived suggestions (status = 'archived')
**When** the user navigates to the "Plans You Never Took" screen
**Then** all archived suggestions are displayed in a list ordered by most recently archived
**And** each card shows:
  - The suggestion's "what" (activity name)
  - The suggestion's "where" (venue)
  - The original "when" (proposed date/time)
  - How long ago it was archived
  - The final commitment count (e.g., "1 of 5 were in")

**Given** the user taps "Revive" on an archived suggestion
**When** the revive action is triggered
**Then** a new suggestion row is created with status = 'active'
**And** the new suggestion copies the `suggestion_data` from the archived suggestion
**And** the `influenced_by` field in suggestion_data is preserved
**And** the user is navigated to the new active suggestion screen
**And** all existing commitments on the old archived suggestion are NOT carried over (fresh vote)

**Given** the user is viewing an archived suggestion card
**When** they tap on it (not the Revive button)
**Then** a detail view expands showing the full suggestion details (why, cost, booking link if still valid)

**Given** a board has no archived suggestions
**When** the user views the "Plans You Never Took" screen
**Then** an empty state is displayed: "No missed plans yet. Every suggestion has been acted on!"

**Given** a suggestion is archived with `_archived_reason: 'insufficient_commitment'`
**When** displayed in the archive list
**Then** the reason is shown: "Expired -- not enough people committed"

## Technical Context

### Relevant Schema

```sql
suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb,   -- { what, why, where, when, cost_per_person, booking_url, influenced_by[], _archived_at, _archived_reason, _final_in_count }
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
  created_at timestamptz
)
```

The `suggestion_data` jsonb includes metadata added by Story 5.5 when archiving:
- `_archived_at`: ISO timestamp of when the suggestion was archived
- `_archived_reason`: Why it was archived (e.g., 'insufficient_commitment')
- `_final_in_count`: Number of "in" votes at time of archiving

### Architecture References

- **Screen:** `app/(tabs)/archive.tsx` or nested within timeline -- "Plans You Never Took" screen
- **Components:** `components/memory/ArchivedSuggestionCard.tsx`, `components/memory/ArchiveScreen.tsx`
- **Navigation:** Accessible from timeline screen or suggestion screen (ArchivedBanner from Story 5.5)
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 5.5 (archive expired suggestions) -- archived suggestions exist
- **Requires:** Epic 4 (suggestions with suggestion_data)
- **Downstream:** Revived suggestions feed back into Epic 5 (voting) flow

## Implementation Notes

### Fetching Archived Suggestions

```typescript
// lib/hooks/use-archived-suggestions.ts
import { useState, useEffect } from 'react';
import { supabase } from '../supabase';

interface ArchivedSuggestion {
  id: string;
  board_id: string;
  suggestion_data: {
    what: string;
    why: string;
    where: string;
    when: string;
    cost_per_person?: string;
    booking_url?: string;
    influenced_by?: string[];
    _archived_at?: string;
    _archived_reason?: string;
    _final_in_count?: number;
  };
  created_at: string;
}

export const useArchivedSuggestions = (boardId: string) => {
  const [suggestions, setSuggestions] = useState<ArchivedSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchArchived = async () => {
      setIsLoading(true);

      const { data, error } = await supabase
        .from('suggestions')
        .select('id, board_id, suggestion_data, created_at')
        .eq('board_id', boardId)
        .eq('status', 'archived')
        .order('created_at', { ascending: false });

      if (error) {
        console.error('Archive fetch error:', error);
      } else {
        setSuggestions(data ?? []);
      }

      setIsLoading(false);
    };

    if (boardId) fetchArchived();
  }, [boardId]);

  return { suggestions, isLoading };
};
```

### Revive Logic

```typescript
// lib/hooks/use-archived-suggestions.ts (continued)
export const reviveSuggestion = async (
  archivedSuggestion: ArchivedSuggestion
): Promise<string> => {
  // Strip archive metadata from suggestion_data
  const { _archived_at, _archived_reason, _final_in_count, _decay_reminder_sent, _nudge_sent, ...cleanData } =
    archivedSuggestion.suggestion_data;

  // Create new active suggestion with cleaned data
  const { data: newSuggestion, error } = await supabase
    .from('suggestions')
    .insert({
      board_id: archivedSuggestion.board_id,
      suggestion_data: {
        ...cleanData,
        _revived_from: archivedSuggestion.id,
        _revived_at: new Date().toISOString(),
      },
      status: 'active',
    })
    .select('id')
    .single();

  if (error) throw error;

  return newSuggestion.id;
};
```

### Archived Suggestion Card

```typescript
// components/memory/ArchivedSuggestionCard.tsx
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { router } from 'expo-router';

interface ArchivedSuggestionCardProps {
  suggestion: ArchivedSuggestion;
  totalBoardMembers: number;
  onRevive: (suggestion: ArchivedSuggestion) => void;
}

const ArchivedSuggestionCard = ({
  suggestion,
  totalBoardMembers,
  onRevive,
}: ArchivedSuggestionCardProps) => {
  const data = suggestion.suggestion_data;
  const archivedAt = data._archived_at
    ? getRelativeTime(data._archived_at)
    : getRelativeTime(suggestion.created_at);

  const commitmentText = data._final_in_count !== undefined
    ? `${data._final_in_count} of ${totalBoardMembers} were in`
    : 'No one committed';

  const reasonText = data._archived_reason === 'insufficient_commitment'
    ? 'Expired -- not enough people committed'
    : 'Archived';

  return (
    <View style={styles.card}>
      <View style={styles.content}>
        <Text style={styles.what}>{data.what ?? 'Untitled plan'}</Text>
        <Text style={styles.where}>{data.where ?? ''}</Text>
        <Text style={styles.when}>Originally for: {data.when ?? 'TBD'}</Text>

        <View style={styles.metaRow}>
          <Text style={styles.reason}>{reasonText}</Text>
          <Text style={styles.commitment}>{commitmentText}</Text>
        </View>

        <Text style={styles.archivedTime}>Archived {archivedAt}</Text>
      </View>

      <TouchableOpacity
        style={styles.reviveButton}
        onPress={() => onRevive(suggestion)}
      >
        <Text style={styles.reviveText}>Revive</Text>
      </TouchableOpacity>
    </View>
  );
};

const getRelativeTime = (isoString: string): string => {
  const diff = Date.now() - new Date(isoString).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  what: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 2,
  },
  where: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 2,
  },
  when: {
    fontSize: 13,
    color: '#9CA3AF',
    marginBottom: 6,
  },
  metaRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 4,
  },
  reason: {
    fontSize: 12,
    color: '#DC2626',
    fontStyle: 'italic',
  },
  commitment: {
    fontSize: 12,
    color: '#6B7280',
  },
  archivedTime: {
    fontSize: 11,
    color: '#D1D5DB',
  },
  reviveButton: {
    backgroundColor: '#3B82F6',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    marginLeft: 12,
  },
  reviveText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
});
```

### Archive Screen

```typescript
// app/(tabs)/archive.tsx (or app/archive.tsx if not a tab)
import { FlatList, View, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { router } from 'expo-router';
import { useArchivedSuggestions, reviveSuggestion } from '../../lib/hooks/use-archived-suggestions';
import { ArchivedSuggestionCard } from '../../components/memory/ArchivedSuggestionCard';
import { useBoardStore } from '../../lib/stores/board-store';

export default function ArchiveScreen() {
  const activeBoardId = useBoardStore((s) => s.activeBoardId);
  const totalMembers = useBoardStore((s) => s.activeBoardMembers?.length ?? 0);
  const { suggestions, isLoading } = useArchivedSuggestions(activeBoardId!);

  const handleRevive = async (suggestion: ArchivedSuggestion) => {
    try {
      const newSuggestionId = await reviveSuggestion(suggestion);
      router.push(`/suggestion/${newSuggestionId}`);
    } catch (err) {
      Alert.alert('Error', 'Failed to revive this plan. Try again.');
    }
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (suggestions.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No missed plans</Text>
        <Text style={styles.emptySubtitle}>
          Every suggestion has been acted on!
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Plans You Never Took</Text>
      <FlatList
        data={suggestions}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <ArchivedSuggestionCard
            suggestion={item}
            totalBoardMembers={totalMembers}
            onRevive={handleRevive}
          />
        )}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  header: { fontSize: 22, fontWeight: '700', color: '#111827', padding: 16, paddingBottom: 8 },
  emptyTitle: { fontSize: 20, fontWeight: '600', color: '#111827', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: '#6B7280', textAlign: 'center' },
  list: { paddingBottom: 16 },
});
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `app/archive.tsx` | "Plans You Never Took" screen showing all archived suggestions |
| `components/memory/ArchivedSuggestionCard.tsx` | Card showing archived suggestion details with Revive button |
| `lib/hooks/use-archived-suggestions.ts` | Hook to fetch archived suggestions and revive them |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/timeline.tsx` | Add navigation link to archive screen ("Plans you never took" button at bottom) |
| `components/suggestion/ArchivedBanner.tsx` | "View plans you never took" link navigates to archive screen |
| `app/(tabs)/_layout.tsx` | Add route for archive screen if needed |

## Definition of Done

- [ ] "Plans You Never Took" screen displays all archived suggestions for the board
- [ ] Suggestions ordered by most recently archived (or most recently created)
- [ ] Each card shows: activity name, venue, original proposed time, archive reason, final commitment count
- [ ] "Revive" button creates a new active suggestion copying data from the archived one
- [ ] Revived suggestion starts with zero commitments (fresh vote)
- [ ] Archive metadata (`_archived_at`, `_nudge_sent`, etc.) stripped from revived suggestion data
- [ ] Revived suggestion data includes `_revived_from` reference to original
- [ ] After reviving, user navigated to the new active suggestion screen
- [ ] Empty state shown when no archived suggestions exist
- [ ] Screen accessible from timeline screen and from ArchivedBanner (Story 5.5)
- [ ] Tapping a card (not Revive button) can expand to show full suggestion details
