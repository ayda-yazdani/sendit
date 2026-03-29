# Story 4.4: Regenerate Suggestion

## Description

As a board member,
I want to request a new suggestion if the current one does not fit our group,
So that we are not stuck with one recommendation and can explore different plan options.

## Status

- **Epic:** Epic 4 - Plan Suggestions
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR30 (regenerate suggestion)
- **NFRs Covered:** NFR5 (suggestion generation < 5s)

## Acceptance Criteria

**Given** an active suggestion is displayed on the board
**When** the user taps the "Regenerate" button
**Then** the current suggestion's status is updated to `'archived'` in the `suggestions` table
**And** the `suggest` Edge Function is called with an additional `exclude_previous` parameter containing a summary of the archived suggestion
**And** Claude generates a DIFFERENT suggestion from the previous one
**And** the new suggestion is inserted with `status: 'active'`
**And** the old suggestion card is replaced by the new one on screen

**Given** the user taps "Regenerate"
**When** the regeneration is in progress
**Then** the "Regenerate" button shows a loading spinner
**And** the current suggestion card remains visible (not removed) until the new one arrives
**And** the user cannot tap "Regenerate" again while loading

**Given** the regeneration fails (Claude API error)
**When** the error is returned
**Then** the current suggestion's status is reverted back to `'active'` (it was optimistically archived)
**And** an error alert is shown: "Could not generate a new suggestion. Try again."
**And** the original suggestion remains displayed

**Given** the user has regenerated multiple times
**When** they tap "Regenerate" again
**Then** only the most recent archived suggestion summary is passed to the prompt (not the full history)
**And** Claude is instructed to generate something different from the previous suggestion

**Given** the archived suggestion was the only active suggestion
**When** the new suggestion is generated successfully
**Then** the Realtime subscription picks up the INSERT event
**And** the new suggestion card appears on all connected clients

## Technical Context

### Relevant Schema

```sql
suggestions (
  id uuid PK,
  board_id uuid FK -> boards,
  suggestion_data jsonb NOT NULL,
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
  created_at timestamptz
)
```

**Status transitions:**
- `active` -> `archived` (when regenerated or expired)
- `active` -> `completed` (when the plan is confirmed — Epic 5/7)

### Architecture References

- **Backend:** Modify `supabase/functions/suggest/index.ts` to accept an optional `exclude_previous` parameter
- **Frontend:** Add "Regenerate" button to `SuggestionCard.tsx` from Story 4.2
- **Client wrapper:** Extend `lib/ai/suggestion-engine.ts` with a `regenerateSuggestion` function
- **Realtime:** The existing subscription from Story 4.2 handles INSERT events for new suggestions and UPDATE events for archived suggestions

### Dependencies

- **Story 4.1:** `suggest` Edge Function must exist
- **Story 4.2:** `SuggestionCard.tsx` must exist with the suggestion display
- **Story 4.3:** Time-sensitive prioritization logic should remain active during regeneration

## Implementation Notes

### Backend: Modify `suggest` Edge Function

Add support for an optional `exclude_previous` field in the request body:

```typescript
// In supabase/functions/suggest/index.ts

interface SuggestRequest {
  board_id: string;
  exclude_previous?: string; // Summary of the previous suggestion to avoid
}

// Parse request
const { board_id, exclude_previous } = await req.json() as SuggestRequest;
```

**Augmented prompt when `exclude_previous` is provided:**

```typescript
function buildSuggestionPrompt(
  tasteProfile: any,
  reels: any[],
  freeWindows: string[] | null,
  timeSensitiveReels: TimeSensitiveReel[],
  excludePrevious?: string
): string {
  let prompt = `... (existing prompt from Story 4.1 + Story 4.3) ...`;

  // Add exclusion instruction
  if (excludePrevious) {
    prompt += `\n\n🔄 REGENERATION REQUEST:
The group has seen the following suggestion and wants something DIFFERENT. Do NOT suggest the same venue, activity, or plan. Generate a meaningfully distinct alternative.

PREVIOUS SUGGESTION (do NOT repeat this):
${excludePrevious}

RULES FOR REGENERATION:
- Suggest a different venue (not the same venue or its branches)
- Suggest a different activity TYPE if possible (e.g., if previous was a club night, try a dinner or gallery)
- If the same activity type is the only good fit, suggest a different specific venue
- The "why" should reference different reels or different patterns in the taste profile
- The suggestion must still be a good fit for the group's taste — different does not mean random`;
  }

  prompt += `\n\nGenerate a suggestion as JSON with: what, why, where, when, cost_per_person, booking_url, influenced_by (array of reel indices from the list above).`;

  return prompt;
}
```

### Frontend: Regenerate Flow

**Client wrapper in `lib/ai/suggestion-engine.ts`:**

```typescript
import { supabase } from '../supabase';

export async function generateSuggestion(boardId: string, excludePrevious?: string) {
  const { data, error } = await supabase.functions.invoke('suggest', {
    body: {
      board_id: boardId,
      ...(excludePrevious ? { exclude_previous: excludePrevious } : {}),
    },
  });

  if (error) throw new Error(`Suggestion generation failed: ${error.message}`);
  return data;
}

export async function regenerateSuggestion(boardId: string, currentSuggestion: any) {
  // Step 1: Archive the current suggestion
  const { error: archiveError } = await supabase
    .from('suggestions')
    .update({ status: 'archived' })
    .eq('id', currentSuggestion.id);

  if (archiveError) {
    throw new Error(`Failed to archive suggestion: ${archiveError.message}`);
  }

  // Step 2: Build a summary of the previous suggestion for exclusion
  const previousSummary = buildPreviousSummary(currentSuggestion.suggestion_data);

  try {
    // Step 3: Generate a new suggestion with exclusion
    const result = await generateSuggestion(boardId, previousSummary);
    return result;
  } catch (error) {
    // Step 4: If generation fails, revert the archive
    await supabase
      .from('suggestions')
      .update({ status: 'active' })
      .eq('id', currentSuggestion.id);

    throw error;
  }
}

function buildPreviousSummary(suggestionData: any): string {
  return `${suggestionData.what} at ${suggestionData.where} on ${suggestionData.when} (${suggestionData.cost_per_person}). Reason: ${suggestionData.why}`;
}
```

**Add Regenerate button to `SuggestionCard.tsx`:**

```tsx
// Add to SuggestionCard component

interface SuggestionCardProps {
  suggestion: Suggestion;
  boardId: string;
  onRegenerate?: () => void;
}

export function SuggestionCard({ suggestion, boardId, onRegenerate }: SuggestionCardProps) {
  const [regenerating, setRegenerating] = useState(false);

  async function handleRegenerate() {
    setRegenerating(true);
    try {
      await regenerateSuggestion(boardId, suggestion);
      // Realtime subscription will pick up the new suggestion
      onRegenerate?.();
    } catch (error) {
      Alert.alert(
        'Could not regenerate',
        'Could not generate a new suggestion. Try again.'
      );
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <View style={styles.card}>
      {/* ... existing card content from Story 4.2 ... */}

      {/* Regenerate button */}
      <TouchableOpacity
        style={[styles.regenerateButton, regenerating && styles.regenerateButtonDisabled]}
        onPress={handleRegenerate}
        disabled={regenerating}
      >
        {regenerating ? (
          <ActivityIndicator color="#6C5CE7" size="small" />
        ) : (
          <Text style={styles.regenerateButtonText}>Regenerate</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}
```

**Regenerate button styling:**

```typescript
regenerateButton: {
  marginTop: 12,
  paddingVertical: 12,
  paddingHorizontal: 24,
  borderRadius: 10,
  borderWidth: 1.5,
  borderColor: '#6C5CE7',
  alignItems: 'center',
  backgroundColor: 'transparent',
},
regenerateButtonDisabled: {
  opacity: 0.5,
},
regenerateButtonText: {
  color: '#6C5CE7',
  fontSize: 15,
  fontWeight: '600',
},
```

### Realtime Handling for Regeneration

The existing Realtime subscription from Story 4.2 already handles this flow:

1. User taps "Regenerate"
2. Client archives the current suggestion (UPDATE: status -> 'archived')
3. Realtime fires UPDATE event -> client detects the active suggestion was archived
4. Client calls `suggest` Edge Function with exclusion
5. Edge Function inserts new suggestion (INSERT: status = 'active')
6. Realtime fires INSERT event -> client renders the new suggestion

However, there is a brief window where no active suggestion exists (between archive and new insert). To handle this smoothly:

```tsx
// In board detail screen, update the Realtime handler:
.on('postgres_changes', {
  event: '*',
  schema: 'public',
  table: 'suggestions',
  filter: `board_id=eq.${boardId}`,
}, (payload) => {
  if (payload.eventType === 'INSERT' && payload.new.status === 'active') {
    setActiveSuggestion(payload.new as Suggestion);
  }
  // Don't remove the card on UPDATE to 'archived' if regenerating
  // The SuggestionCard component manages its own loading state
})
```

The key insight: keep the old suggestion card visible with a loading overlay during regeneration, and only swap it when the new suggestion arrives via Realtime.

### Edge Case: Multiple Rapid Regenerations

If the user somehow taps "Regenerate" multiple times in quick succession, the `disabled={regenerating}` prop on the button prevents this. The button is disabled while the regeneration is in progress.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Modify** | `supabase/functions/suggest/index.ts` | Accept optional `exclude_previous` parameter; add regeneration instructions to Claude prompt when present |
| **Modify** | `lib/ai/suggestion-engine.ts` | Add `regenerateSuggestion()` function that archives current suggestion, calls suggest with exclusion, and reverts on failure |
| **Modify** | `components/suggestion/SuggestionCard.tsx` | Add "Regenerate" button with loading state and disabled-while-loading behavior |

## Definition of Done

- [ ] "Regenerate" button is visible on the suggestion card
- [ ] Tapping "Regenerate" shows a loading spinner and disables the button
- [ ] The current suggestion is archived (status set to `'archived'`) in Supabase
- [ ] The `suggest` Edge Function is called with `exclude_previous` containing a summary of the archived suggestion
- [ ] The Claude prompt includes explicit instructions to generate a DIFFERENT suggestion from the previous one
- [ ] The new suggestion is inserted with `status: 'active'`
- [ ] The new suggestion appears on screen via Realtime (replacing the old card)
- [ ] If the Claude API call fails, the archived suggestion is reverted to `'active'`
- [ ] An error alert is shown to the user on failure
- [ ] The old suggestion card remains visible during regeneration (not removed until the new one arrives)
- [ ] The button cannot be tapped again while regeneration is in progress
- [ ] Manual test: generate a suggestion, tap "Regenerate", verify the new suggestion is different from the previous one (different venue or activity)
- [ ] Manual test: simulate a Claude API failure during regeneration, verify the original suggestion is restored
