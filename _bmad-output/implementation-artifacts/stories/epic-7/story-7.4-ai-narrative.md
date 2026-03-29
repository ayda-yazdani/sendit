# Story 7.4: AI Narrative Chapter

## Description

As a member,
I want an AI-written summary of the night based on our photos, memories, and the original suggestion,
So that the event has a lasting, well-written narrative that captures what happened.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** an event has at least 2 memories and/or 3 photos
**When** the user taps "Generate Story" on the event page (or it triggers automatically)
**Then** the system calls Claude API with the event's photos, memories, and original suggestion context
**And** Claude writes a short narrative paragraph (3-6 sentences)
**And** the narrative is saved to `events.narrative`

**Given** a narrative has been generated
**When** any board member views the event page
**Then** the narrative is displayed in a styled text section below the photos and memories
**And** the narrative reads like a vivid, personal story of the night

**Given** the user wants to regenerate the narrative
**When** they tap "Regenerate Story"
**Then** Claude generates a new narrative with the same inputs
**And** the previous narrative is replaced

**Given** an event has no memories and no photos
**When** the user tries to generate a narrative
**Then** the button is disabled with a tooltip: "Add some photos or memories first"

**Given** a narrative is being generated
**When** the API call is in progress
**Then** a loading state is shown with text like "Writing your story..."

## Technical Context

### Relevant Schema

```sql
events (
  id uuid PK,
  suggestion_id uuid FK,
  board_id uuid FK,
  photos jsonb DEFAULT '[]',   -- Array of { url, member_id, uploaded_at }
  memories jsonb DEFAULT '[]', -- Array of { member_id, text, created_at }
  narrative text,              -- AI-generated narrative paragraph
  created_at timestamptz
)

suggestions (
  id uuid PK,
  board_id uuid FK,
  suggestion_data jsonb        -- { what, why, where, when, cost_per_person, booking_url, influenced_by[] }
)
```

### Architecture References

- **Edge Function:** `supabase/functions/generate-narrative/index.ts` -- New Edge Function for narrative generation
- **Claude API:** Called from the Edge Function with structured prompt
- **Screen:** `app/(tabs)/event/[id].tsx` -- Narrative section of the event page
- **Components:** `components/memory/NarrativeSection.tsx`
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 7.1 (event page), Story 7.2 (photos), Story 7.3 (memories)
- **Requires:** Claude API key stored as Supabase Edge Function secret (`CLAUDE_API_KEY`)
- **Downstream:** Story 7.5 (group timeline shows narrative preview)

## Implementation Notes

### Claude Prompt for Narrative Generation

This is the actual prompt sent to Claude:

```typescript
const buildNarrativePrompt = (
  suggestionData: any,
  memories: { member_id: string; text: string; display_name?: string }[],
  photoCount: number,
  memberNames: string[]
): string => {
  const memoriesText = memories
    .map((m) => `- ${m.display_name ?? 'Someone'}: "${m.text}"`)
    .join('\n');

  return `You are a warm, witty storyteller writing a memory chapter for a group of friends. Write in second person plural ("you" referring to the group). Be vivid and specific, not generic. Capture the energy and feeling of the night, not just the facts.

CONTEXT:
- The plan: ${suggestionData.what ?? 'a night out'}
- The venue: ${suggestionData.where ?? 'somewhere great'}
- The date: ${suggestionData.when ?? 'recently'}
- Cost per person: ${suggestionData.cost_per_person ?? 'unknown'}
- Who went: ${memberNames.join(', ')}
- Number of photos taken: ${photoCount}

THEIR MEMORIES (one-line submissions from each person):
${memoriesText || 'No written memories yet.'}

INSTRUCTIONS:
1. Write exactly ONE paragraph, 3-6 sentences long.
2. Weave together the individual memories into a cohesive narrative -- don't just list them.
3. Use specific details from the memories to make it feel real and personal.
4. Match the tone to the content: if the memories are funny, be funny. If they're sentimental, be warm.
5. Reference the venue and what happened there naturally.
6. End with a line that feels like a mic drop or a warm closing thought.
7. Do NOT use hashtags, emojis, or bullet points.
8. Do NOT start with "It was" or "The night".
9. Write as if you were the group's favourite friend summarising the night.

Write the narrative paragraph now:`;
};
```

### Edge Function: generate-narrative

```typescript
// supabase/functions/generate-narrative/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CLAUDE_API_KEY = Deno.env.get('CLAUDE_API_KEY')!;
const CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { event_id } = await req.json();

  if (!event_id) {
    return new Response(JSON.stringify({ error: 'event_id required' }), { status: 400 });
  }

  // Fetch event with suggestion data
  const { data: event, error: eventErr } = await supabase
    .from('events')
    .select('*, suggestions(suggestion_data)')
    .eq('id', event_id)
    .single();

  if (eventErr || !event) {
    return new Response(JSON.stringify({ error: 'Event not found' }), { status: 404 });
  }

  const memories = (event.memories as any[]) ?? [];
  const photos = (event.photos as any[]) ?? [];
  const suggestionData = event.suggestions?.suggestion_data ?? {};

  // Check minimum content threshold
  if (memories.length < 2 && photos.length < 3) {
    return new Response(
      JSON.stringify({ error: 'Not enough content. Need at least 2 memories or 3 photos.' }),
      { status: 400 }
    );
  }

  // Get member names for the memories
  const memberIds = [...new Set(memories.map((m: any) => m.member_id))];
  const { data: members } = await supabase
    .from('members')
    .select('id, display_name')
    .in('id', memberIds);

  const memberMap = new Map(members?.map((m) => [m.id, m.display_name]) ?? []);

  // Get all attendees (members who voted "in")
  const { data: commitments } = await supabase
    .from('commitments')
    .select('members(display_name)')
    .eq('suggestion_id', event.suggestion_id)
    .eq('status', 'in');

  const attendeeNames = commitments?.map((c: any) => c.members?.display_name).filter(Boolean) ?? [];

  const memoriesWithNames = memories.map((m: any) => ({
    ...m,
    display_name: memberMap.get(m.member_id) ?? 'Someone',
  }));

  const prompt = buildNarrativePrompt(
    suggestionData,
    memoriesWithNames,
    photos.length,
    attendeeNames
  );

  // Call Claude API
  const claudeResponse = await fetch(CLAUDE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': CLAUDE_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 300,
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
    }),
  });

  if (!claudeResponse.ok) {
    const errorText = await claudeResponse.text();
    console.error('Claude API error:', errorText);

    // Retry once (NFR13)
    const retryResponse = await fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 300,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!retryResponse.ok) {
      return new Response(
        JSON.stringify({ error: 'AI narrative generation failed after retry' }),
        { status: 502 }
      );
    }

    const retryData = await retryResponse.json();
    const narrative = retryData.content[0].text;

    await supabase
      .from('events')
      .update({ narrative })
      .eq('id', event_id);

    return new Response(JSON.stringify({ narrative }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const claudeData = await claudeResponse.json();
  const narrative = claudeData.content[0].text;

  // Save narrative to event
  await supabase
    .from('events')
    .update({ narrative })
    .eq('id', event_id);

  return new Response(JSON.stringify({ narrative }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
});

// Prompt builder (same as above, included in the Edge Function file)
function buildNarrativePrompt(
  suggestionData: any,
  memories: { member_id: string; text: string; display_name?: string }[],
  photoCount: number,
  memberNames: string[]
): string {
  const memoriesText = memories
    .map((m) => `- ${m.display_name ?? 'Someone'}: "${m.text}"`)
    .join('\n');

  return `You are a warm, witty storyteller writing a memory chapter for a group of friends. Write in second person plural ("you" referring to the group). Be vivid and specific, not generic. Capture the energy and feeling of the night, not just the facts.

CONTEXT:
- The plan: ${suggestionData.what ?? 'a night out'}
- The venue: ${suggestionData.where ?? 'somewhere great'}
- The date: ${suggestionData.when ?? 'recently'}
- Cost per person: ${suggestionData.cost_per_person ?? 'unknown'}
- Who went: ${memberNames.join(', ')}
- Number of photos taken: ${photoCount}

THEIR MEMORIES (one-line submissions from each person):
${memoriesText || 'No written memories yet.'}

INSTRUCTIONS:
1. Write exactly ONE paragraph, 3-6 sentences long.
2. Weave together the individual memories into a cohesive narrative -- don't just list them.
3. Use specific details from the memories to make it feel real and personal.
4. Match the tone to the content: if the memories are funny, be funny. If they're sentimental, be warm.
5. Reference the venue and what happened there naturally.
6. End with a line that feels like a mic drop or a warm closing thought.
7. Do NOT use hashtags, emojis, or bullet points.
8. Do NOT start with "It was" or "The night".
9. Write as if you were the group's favourite friend summarising the night.

Write the narrative paragraph now:`;
}
```

### Client-Side Integration

```typescript
// In components/memory/NarrativeSection.tsx
const NarrativeSection = ({ eventId, narrative, hasEnoughContent }: Props) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [localNarrative, setLocalNarrative] = useState(narrative);

  const generateNarrative = async () => {
    setIsGenerating(true);
    try {
      const { data, error } = await supabase.functions.invoke('generate-narrative', {
        body: { event_id: eventId },
      });

      if (error) throw error;
      setLocalNarrative(data.narrative);
    } catch (err) {
      Alert.alert('Error', 'Failed to generate the story. Try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>The Story</Text>

      {localNarrative ? (
        <>
          <Text style={styles.narrative}>{localNarrative}</Text>
          <TouchableOpacity onPress={generateNarrative} disabled={isGenerating}>
            <Text style={styles.regenerate}>Regenerate Story</Text>
          </TouchableOpacity>
        </>
      ) : isGenerating ? (
        <View style={styles.loading}>
          <ActivityIndicator />
          <Text style={styles.loadingText}>Writing your story...</Text>
        </View>
      ) : (
        <TouchableOpacity
          onPress={generateNarrative}
          disabled={!hasEnoughContent}
          style={[styles.generateButton, !hasEnoughContent && styles.disabled]}
        >
          <Text style={styles.generateText}>
            {hasEnoughContent ? 'Generate Story' : 'Add some photos or memories first'}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/generate-narrative/index.ts` | Edge Function: builds Claude prompt from event data, generates narrative, saves to events.narrative |
| `components/memory/NarrativeSection.tsx` | UI component showing narrative text, generate button, and regenerate option |

### Modify

| File | Change |
|------|--------|
| `components/memory/EventPage.tsx` | Integrate NarrativeSection below MemoriesSection |
| `lib/hooks/use-event.ts` | Expose `hasEnoughContent` computed property for enabling/disabling generate button |

## Definition of Done

- [ ] Edge Function `generate-narrative` deployed and callable
- [ ] Claude prompt includes event context (what, where, when), attendee names, memories text, and photo count
- [ ] Claude generates a 3-6 sentence narrative paragraph in second person plural
- [ ] Narrative saved to `events.narrative` field
- [ ] Narrative displayed on event page in a styled text section
- [ ] "Generate Story" button disabled when event has fewer than 2 memories and fewer than 3 photos
- [ ] Loading state shown during generation ("Writing your story...")
- [ ] "Regenerate Story" option available after initial generation
- [ ] Retry logic: 1 retry with exponential backoff on Claude API failure (NFR13)
- [ ] Error handling: failure shows user-friendly alert
- [ ] Narrative tone matches the content (funny memories = funny narrative, sentimental = warm)
- [ ] No emojis, hashtags, or bullet points in generated narrative
