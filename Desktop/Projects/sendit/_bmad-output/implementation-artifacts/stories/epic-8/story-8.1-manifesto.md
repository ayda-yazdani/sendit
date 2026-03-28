# Story 8.1: Group Manifesto

## Description

As a board member,
I want an AI-generated character study of our group,
So that we have a shareable portrait of who we are based on everything we've sent.

## Status

- **Epic:** Shared Objects
- **Priority:** P2
- **Branch:** `feature/shared-objects`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** a board has a mature taste profile (10+ reels analyzed)
**When** the user taps "Generate Manifesto" on the board detail or profile screen
**Then** the system calls Claude API with the group's taste profile data
**And** Claude writes a 3-5 sentence character study of the group
**And** the manifesto is stored in the `taste_profiles` table (or a dedicated field)

**Given** a manifesto has been generated
**When** any board member views the manifesto screen
**Then** the character study is displayed as a styled, visually distinct card
**And** the card includes the group name (board name), the identity label, and the manifesto text

**Given** the user taps "Share" on the manifesto card
**When** the share action is triggered
**Then** a shareable image/card is generated with the manifesto content
**And** the native share sheet opens to share it to any app (WhatsApp, Instagram Stories, etc.)

**Given** a board has fewer than 10 reels
**When** the user tries to generate a manifesto
**Then** the button is disabled with a message: "Add more reels to unlock your group manifesto (need 10+, have X)"

**Given** new reels are added after a manifesto was generated
**When** the user taps "Regenerate"
**Then** a new manifesto is generated reflecting the updated taste profile
**And** the previous manifesto is replaced

## Technical Context

### Relevant Schema

```sql
taste_profiles (
  id uuid PK,
  board_id uuid FK UNIQUE,
  profile_data jsonb,    -- { activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix }
  identity_label text,   -- e.g., "The Chaotic Intellectuals"
  updated_at timestamptz
)

reels (
  id uuid PK,
  board_id uuid FK,
  extraction_data jsonb,
  classification text,
  created_at timestamptz
)
```

**Manifesto Storage:** Store the manifesto text in `taste_profiles.profile_data` as a `manifesto` field within the existing jsonb, or add a dedicated column. Using the jsonb approach for hackathon simplicity:

```json
{
  "activity_types": [...],
  "aesthetic": "...",
  "manifesto": "Your 3-5 sentence character study here..."
}
```

### Architecture References

- **Edge Function:** `supabase/functions/generate-manifesto/index.ts` -- New Edge Function
- **Claude API:** Called from Edge Function with taste profile context
- **Screen:** Board detail or dedicated manifesto screen
- **Components:** `components/shared/ManifestoCard.tsx`
- **Sharing:** React Native Share API or expo-sharing for the shareable card
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Epic 3 (taste profile exists with profile_data)
- **Requires:** 10+ reels on the board with extraction data
- **Requires:** Claude API key as Supabase secret (`CLAUDE_API_KEY`)

## Implementation Notes

### Claude Prompt for Manifesto Generation

This is the actual prompt sent to Claude:

```typescript
const buildManifestoPrompt = (
  boardName: string,
  identityLabel: string,
  profileData: any,
  reelCount: number,
  classificationBreakdown: Record<string, number>,
  sampleExtractions: string[]
): string => {
  return `You are a razor-sharp cultural critic who writes with the warmth of a best friend and the precision of a journalist. You're writing a "group manifesto" -- a character study of a friend group based entirely on the content they share with each other.

GROUP: "${boardName}"
IDENTITY LABEL: "${identityLabel}"
TOTAL CONTENT SHARED: ${reelCount} pieces

TASTE PROFILE:
- Activity types they're into: ${JSON.stringify(profileData.activity_types ?? [])}
- Aesthetic register: ${profileData.aesthetic ?? 'unknown'}
- Food preferences: ${JSON.stringify(profileData.food_preferences ?? [])}
- Location patterns: ${JSON.stringify(profileData.location_patterns ?? [])}
- Price range: ${profileData.price_range ?? 'unknown'}
- Humour style: ${profileData.humour_style ?? 'unknown'}
- Platform mix: ${JSON.stringify(profileData.platform_mix ?? {})}

CONTENT BREAKDOWN:
${Object.entries(classificationBreakdown)
  .map(([type, count]) => `- ${type}: ${count} pieces`)
  .join('\n')}

SAMPLE CONTENT SIGNALS (what they've been sending each other):
${sampleExtractions.map((s, i) => `${i + 1}. ${s}`).join('\n')}

INSTRUCTIONS:
1. Write exactly 3-5 sentences. No more, no less.
2. Write in second person ("You are...") addressing the group directly.
3. Be SPECIFIC. Reference actual patterns you see in their data -- don't be generic.
4. Balance sharp observation with affection. You see them clearly AND you like what you see.
5. Include at least one line that feels like a "that's SO us" moment -- an observation so specific they'll screenshot it.
6. If their humour is dark, match it. If they're wholesome, match that. Mirror their energy.
7. End with a line that captures their essential contradiction or defining quality.
8. Do NOT use bullet points, numbered lists, or headers.
9. Do NOT use emojis.
10. Do NOT start with "You are a group that..." -- be more creative.
11. Write it as one flowing paragraph.

Write the manifesto now:`;
};
```

### Edge Function: generate-manifesto

```typescript
// supabase/functions/generate-manifesto/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CLAUDE_API_KEY = Deno.env.get('CLAUDE_API_KEY')!;
const CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { board_id } = await req.json();

  if (!board_id) {
    return new Response(JSON.stringify({ error: 'board_id required' }), { status: 400 });
  }

  // Fetch board name
  const { data: board } = await supabase
    .from('boards')
    .select('name')
    .eq('id', board_id)
    .single();

  // Fetch taste profile
  const { data: tasteProfile } = await supabase
    .from('taste_profiles')
    .select('profile_data, identity_label')
    .eq('board_id', board_id)
    .single();

  if (!tasteProfile) {
    return new Response(
      JSON.stringify({ error: 'No taste profile found. Add more reels first.' }),
      { status: 400 }
    );
  }

  // Fetch reels for content breakdown and sample extractions
  const { data: reels, count: reelCount } = await supabase
    .from('reels')
    .select('classification, extraction_data', { count: 'exact' })
    .eq('board_id', board_id)
    .not('extraction_data', 'is', null);

  if (!reelCount || reelCount < 10) {
    return new Response(
      JSON.stringify({ error: `Need 10+ reels, currently have ${reelCount ?? 0}` }),
      { status: 400 }
    );
  }

  // Build classification breakdown
  const classificationBreakdown: Record<string, number> = {};
  reels?.forEach((r) => {
    const cls = r.classification ?? 'unclassified';
    classificationBreakdown[cls] = (classificationBreakdown[cls] ?? 0) + 1;
  });

  // Get sample extractions (up to 8 recent ones, summarized)
  const sampleExtractions = (reels ?? []).slice(0, 8).map((r) => {
    const data = r.extraction_data as any;
    const parts = [
      data?.venue_name && `Venue: ${data.venue_name}`,
      data?.activity && `Activity: ${data.activity}`,
      data?.vibe && `Vibe: ${data.vibe}`,
      data?.mood && `Mood: ${data.mood}`,
      data?.hashtags?.length && `Tags: ${data.hashtags.slice(0, 3).join(', ')}`,
    ].filter(Boolean);
    return parts.join(' | ') || 'Content signal';
  });

  const prompt = buildManifestoPrompt(
    board?.name ?? 'This Group',
    tasteProfile.identity_label ?? 'Unnamed Identity',
    tasteProfile.profile_data ?? {},
    reelCount,
    classificationBreakdown,
    sampleExtractions
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
      max_tokens: 400,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!claudeResponse.ok) {
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
        max_tokens: 400,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!retryResponse.ok) {
      return new Response(
        JSON.stringify({ error: 'AI manifesto generation failed after retry' }),
        { status: 502 }
      );
    }

    const retryData = await retryResponse.json();
    const manifesto = retryData.content[0].text;

    // Save manifesto to taste profile
    await supabase
      .from('taste_profiles')
      .update({
        profile_data: {
          ...(tasteProfile.profile_data as object),
          manifesto,
          manifesto_generated_at: new Date().toISOString(),
        },
      })
      .eq('board_id', board_id);

    return new Response(JSON.stringify({ manifesto }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const claudeData = await claudeResponse.json();
  const manifesto = claudeData.content[0].text;

  // Save manifesto to taste profile
  await supabase
    .from('taste_profiles')
    .update({
      profile_data: {
        ...(tasteProfile.profile_data as object),
        manifesto,
        manifesto_generated_at: new Date().toISOString(),
      },
    })
    .eq('board_id', board_id);

  return new Response(JSON.stringify({ manifesto }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
});

// Include the prompt builder function in the same file
function buildManifestoPrompt(
  boardName: string,
  identityLabel: string,
  profileData: any,
  reelCount: number,
  classificationBreakdown: Record<string, number>,
  sampleExtractions: string[]
): string {
  return `You are a razor-sharp cultural critic who writes with the warmth of a best friend and the precision of a journalist. You're writing a "group manifesto" -- a character study of a friend group based entirely on the content they share with each other.

GROUP: "${boardName}"
IDENTITY LABEL: "${identityLabel}"
TOTAL CONTENT SHARED: ${reelCount} pieces

TASTE PROFILE:
- Activity types they're into: ${JSON.stringify(profileData.activity_types ?? [])}
- Aesthetic register: ${profileData.aesthetic ?? 'unknown'}
- Food preferences: ${JSON.stringify(profileData.food_preferences ?? [])}
- Location patterns: ${JSON.stringify(profileData.location_patterns ?? [])}
- Price range: ${profileData.price_range ?? 'unknown'}
- Humour style: ${profileData.humour_style ?? 'unknown'}
- Platform mix: ${JSON.stringify(profileData.platform_mix ?? {})}

CONTENT BREAKDOWN:
${Object.entries(classificationBreakdown)
  .map(([type, count]) => `- ${type}: ${count} pieces`)
  .join('\n')}

SAMPLE CONTENT SIGNALS (what they've been sending each other):
${sampleExtractions.map((s, i) => `${i + 1}. ${s}`).join('\n')}

INSTRUCTIONS:
1. Write exactly 3-5 sentences. No more, no less.
2. Write in second person ("You are...") addressing the group directly.
3. Be SPECIFIC. Reference actual patterns you see in their data -- don't be generic.
4. Balance sharp observation with affection. You see them clearly AND you like what you see.
5. Include at least one line that feels like a "that's SO us" moment -- an observation so specific they'll screenshot it.
6. If their humour is dark, match it. If they're wholesome, match that. Mirror their energy.
7. End with a line that captures their essential contradiction or defining quality.
8. Do NOT use bullet points, numbered lists, or headers.
9. Do NOT use emojis.
10. Do NOT start with "You are a group that..." -- be more creative.
11. Write it as one flowing paragraph.

Write the manifesto now:`;
}
```

### Shareable Card Component

```typescript
// components/shared/ManifestoCard.tsx
import { View, Text, TouchableOpacity, Share, StyleSheet } from 'react-native';
import { captureRef } from 'react-native-view-shot'; // Optional: for image generation

interface ManifestoCardProps {
  boardName: string;
  identityLabel: string;
  manifesto: string;
}

const ManifestoCard = ({ boardName, identityLabel, manifesto }: ManifestoCardProps) => {
  const cardRef = useRef<View>(null);

  const handleShare = async () => {
    try {
      await Share.share({
        message: `${boardName} -- "${identityLabel}"\n\n${manifesto}\n\n-- Generated by Sendit`,
      });
    } catch (err) {
      console.error('Share failed:', err);
    }
  };

  return (
    <View style={styles.cardContainer}>
      <View ref={cardRef} style={styles.card}>
        <Text style={styles.boardName}>{boardName}</Text>
        <Text style={styles.identityLabel}>"{identityLabel}"</Text>
        <View style={styles.divider} />
        <Text style={styles.manifesto}>{manifesto}</Text>
        <Text style={styles.attribution}>-- Sendit</Text>
      </View>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.shareButton} onPress={handleShare}>
          <Text style={styles.shareText}>Share Manifesto</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  cardContainer: {
    margin: 16,
  },
  card: {
    backgroundColor: '#111827',
    borderRadius: 16,
    padding: 24,
  },
  boardName: {
    fontSize: 14,
    color: '#9CA3AF',
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginBottom: 4,
  },
  identityLabel: {
    fontSize: 22,
    fontWeight: '700',
    color: '#F9FAFB',
    marginBottom: 16,
    fontStyle: 'italic',
  },
  divider: {
    height: 1,
    backgroundColor: '#374151',
    marginBottom: 16,
  },
  manifesto: {
    fontSize: 16,
    lineHeight: 24,
    color: '#E5E7EB',
    fontStyle: 'italic',
  },
  attribution: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 16,
    textAlign: 'right',
  },
  actions: {
    marginTop: 12,
    alignItems: 'center',
  },
  shareButton: {
    backgroundColor: '#3B82F6',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  shareText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});
```

### Client-Side Trigger

```typescript
// In the board detail screen or a dedicated manifesto section
const generateManifesto = async (boardId: string) => {
  setIsGenerating(true);
  try {
    const { data, error } = await supabase.functions.invoke('generate-manifesto', {
      body: { board_id: boardId },
    });

    if (error) throw error;
    setManifesto(data.manifesto);
  } catch (err: any) {
    Alert.alert('Error', err.message ?? 'Failed to generate manifesto.');
  } finally {
    setIsGenerating(false);
  }
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/generate-manifesto/index.ts` | Edge Function: builds prompt from taste profile and reel data, calls Claude, saves manifesto |
| `components/shared/ManifestoCard.tsx` | Styled dark card displaying group name, identity label, and manifesto text with share button |
| `lib/hooks/use-manifesto.ts` | Hook for generating, fetching, and sharing the manifesto |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Add "Group Manifesto" section with generate button (or link to manifesto screen) |
| `lib/stores/taste-store.ts` | Add manifesto state from profile_data.manifesto |

## Definition of Done

- [ ] Edge Function `generate-manifesto` deployed and callable
- [ ] Claude prompt includes: board name, identity label, full taste profile, content breakdown, sample extractions
- [ ] Claude generates a 3-5 sentence character study paragraph
- [ ] Manifesto stored in `taste_profiles.profile_data.manifesto`
- [ ] Manifesto displayed as a styled dark card with group name and identity label
- [ ] "Generate Manifesto" disabled when board has fewer than 10 reels
- [ ] Loading state during generation
- [ ] "Regenerate" option available after initial generation
- [ ] "Share Manifesto" button opens native share sheet with manifesto text
- [ ] Retry logic: 1 retry on Claude API failure (NFR13)
- [ ] Manifesto tone mirrors the group's personality (dark humour group gets a sharp manifesto, wholesome group gets a warm one)
- [ ] No emojis, bullet points, or generic language in generated manifesto
