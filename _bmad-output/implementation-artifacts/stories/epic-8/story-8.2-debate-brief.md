# Story 8.2: Weekly Debate Brief

## Description

As a board member,
I want a weekly discussion topic generated from the political and philosophical content we share,
So that our shared reels spark real conversations beyond just plans.

## Status

- **Epic:** Shared Objects
- **Priority:** P2
- **Branch:** `feature/shared-objects`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** a board has 3+ reels classified as `humour_identity` that contain political, philosophical, or opinion-based content
**When** the user taps "Generate Debate Brief" or the weekly brief is auto-generated
**Then** Claude analyzes the relevant reels and produces a structured debate brief
**And** the brief includes: a motion statement, 2-3 arguments for, 2-3 arguments against, and 2-3 provocations/questions

**Given** a debate brief has been generated
**When** any board member views it
**Then** the brief is displayed in a structured card format with clear sections
**And** the motion is displayed prominently at the top
**And** "For" and "Against" arguments are displayed in two columns or sections
**And** provocations are displayed as highlighted questions

**Given** a board does not have 3+ qualifying reels
**When** the user tries to generate a debate brief
**Then** the button is disabled with: "Share more opinion/political content to unlock debate briefs (need 3+, have X)"

**Given** a debate brief was generated last week
**When** the user taps "Generate New Brief"
**Then** a fresh brief is generated using any new qualifying reels since the last brief
**And** the previous brief is still accessible in a "Past Briefs" list

**Given** the brief is generated
**When** the user views it
**Then** the brief cites which reels influenced each argument (linked by reel ID)

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK,
  url text,
  platform text,
  extraction_data jsonb,    -- { venue_name, activity, vibe, mood, hashtags, ... }
  classification text,      -- 'real_event' | 'real_venue' | 'vibe_inspiration' | 'recipe_food' | 'humour_identity'
  created_at timestamptz
)

taste_profiles (
  id uuid PK,
  board_id uuid FK UNIQUE,
  profile_data jsonb,       -- Can store debate_briefs here as an array
  identity_label text,
  updated_at timestamptz
)
```

**Debate Brief Storage:** Store in `taste_profiles.profile_data.debate_briefs` as an array of briefs:

```json
{
  "debate_briefs": [
    {
      "generated_at": "2026-03-28T12:00:00Z",
      "motion": "This house believes...",
      "arguments_for": [...],
      "arguments_against": [...],
      "provocations": [...],
      "source_reel_ids": [...]
    }
  ]
}
```

### Architecture References

- **Edge Function:** `supabase/functions/generate-debate-brief/index.ts`
- **Claude API:** Called from Edge Function with filtered reel data
- **Screen:** Dedicated debate brief view or section within the board detail
- **Components:** `components/shared/DebateBriefCard.tsx`
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Epic 2 (reels with extraction_data and classification)
- **Requires:** Reels classified as `humour_identity` with political/philosophical signals
- **Requires:** Claude API key as Supabase secret (`CLAUDE_API_KEY`)

## Implementation Notes

### Filtering Qualifying Reels

Not all `humour_identity` reels are debate-worthy. The Edge Function should look for signals of political, philosophical, or opinion-based content in the extraction data:

```typescript
const filterDebateReels = (reels: any[]): any[] => {
  const debateSignals = [
    'political', 'philosophy', 'debate', 'opinion', 'controversial',
    'society', 'capitalism', 'feminism', 'justice', 'rights', 'equality',
    'climate', 'technology', 'AI', 'privacy', 'culture war', 'woke',
    'tradition', 'progressive', 'conservative', 'moral', 'ethical',
    'take', 'hot take', 'unpopular opinion', 'satire', 'commentary',
  ];

  return reels.filter((reel) => {
    if (reel.classification !== 'humour_identity') return false;

    const extractionText = JSON.stringify(reel.extraction_data).toLowerCase();
    return debateSignals.some((signal) => extractionText.includes(signal));
  });
};
```

### Claude Prompt for Debate Brief Generation

```typescript
const buildDebateBriefPrompt = (
  boardName: string,
  identityLabel: string,
  reelSummaries: { id: string; summary: string; url: string }[]
): string => {
  const reelsList = reelSummaries
    .map((r, i) => `[Reel ${i + 1}] (ID: ${r.id})\n${r.summary}\nSource: ${r.url}`)
    .join('\n\n');

  return `You are a sharp, provocative debate moderator crafting a weekly discussion brief for a friend group called "${boardName}" (aka "${identityLabel}"). They share political takes, philosophical memes, satire, and hot takes with each other. Your job is to distill their shared content into a structured debate that will get them arguing at dinner.

CONTENT THEY'VE BEEN SHARING:
${reelsList}

Generate a debate brief with this EXACT structure (use these exact headings):

MOTION: [Write a formal debate motion in the style of "This house believes..." that captures the central tension in their shared content. Make it specific to what they've been sharing, not generic.]

FOR THE MOTION:
1. [Argument 1 -- reference specific content they shared] (Source: Reel X)
2. [Argument 2] (Source: Reel X)
3. [Argument 3] (Source: Reel X)

AGAINST THE MOTION:
1. [Counter-argument 1 -- reference specific content they shared] (Source: Reel X)
2. [Counter-argument 2] (Source: Reel X)
3. [Counter-argument 3] (Source: Reel X)

PROVOCATIONS:
1. [A question designed to make someone at the table uncomfortable because it challenges their assumed position]
2. [A question that forces the group to confront a contradiction in their own behaviour]
3. [A "what would you actually do" scenario that tests their convictions]

RULES:
- The motion must be debatable -- reasonable people could disagree.
- Arguments must reference the actual content they shared (cite Reel numbers).
- Provocations should be personal enough to sting but not cruel.
- Write in a tone that matches this group's energy: sharp, irreverent, intellectual.
- Do NOT be generic. This brief should feel like it was written for THIS group.
- Do NOT use emojis.
- Keep each argument to 1-2 sentences max.
- Keep each provocation to 1-2 sentences max.

Generate the debate brief now:`;
};
```

### Edge Function: generate-debate-brief

```typescript
// supabase/functions/generate-debate-brief/index.ts
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

  // Fetch board name and taste profile
  const { data: board } = await supabase
    .from('boards')
    .select('name')
    .eq('id', board_id)
    .single();

  const { data: tasteProfile } = await supabase
    .from('taste_profiles')
    .select('profile_data, identity_label')
    .eq('board_id', board_id)
    .single();

  // Fetch humour_identity reels
  const { data: allReels } = await supabase
    .from('reels')
    .select('id, url, platform, extraction_data, classification')
    .eq('board_id', board_id)
    .eq('classification', 'humour_identity')
    .order('created_at', { ascending: false });

  // Filter for debate-worthy content
  const debateReels = filterDebateReels(allReels ?? []);

  if (debateReels.length < 3) {
    return new Response(
      JSON.stringify({
        error: `Need 3+ debate-worthy reels, found ${debateReels.length}. Share more opinion or political content.`,
      }),
      { status: 400 }
    );
  }

  // Summarize each reel for the prompt
  const reelSummaries = debateReels.slice(0, 8).map((reel) => {
    const data = reel.extraction_data as any;
    const parts = [
      data?.title && `Title: ${data.title}`,
      data?.description && `Description: ${data.description}`,
      data?.transcript && `Transcript excerpt: ${(data.transcript as string).substring(0, 200)}`,
      data?.hashtags?.length && `Hashtags: ${data.hashtags.join(', ')}`,
      data?.vibe && `Vibe: ${data.vibe}`,
      data?.mood && `Mood: ${data.mood}`,
    ].filter(Boolean);

    return {
      id: reel.id,
      summary: parts.join('\n'),
      url: reel.url,
    };
  });

  const prompt = buildDebateBriefPrompt(
    board?.name ?? 'This Group',
    tasteProfile?.identity_label ?? 'Anonymous Intellectuals',
    reelSummaries
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
      max_tokens: 800,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!claudeResponse.ok) {
    // Retry once
    const retryResponse = await fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 800,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!retryResponse.ok) {
      return new Response(
        JSON.stringify({ error: 'Debate brief generation failed after retry' }),
        { status: 502 }
      );
    }

    const retryData = await retryResponse.json();
    const briefText = retryData.content[0].text;
    const parsedBrief = parseDebateBrief(briefText, reelSummaries.map((r) => r.id));

    await saveBrief(supabase, board_id, parsedBrief, tasteProfile);

    return new Response(JSON.stringify(parsedBrief), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const claudeData = await claudeResponse.json();
  const briefText = claudeData.content[0].text;

  // Parse the structured response
  const parsedBrief = parseDebateBrief(briefText, reelSummaries.map((r) => r.id));

  // Save to taste_profiles
  await saveBrief(supabase, board_id, parsedBrief, tasteProfile);

  return new Response(JSON.stringify(parsedBrief), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
});

function parseDebateBrief(text: string, sourceReelIds: string[]) {
  // Parse the structured text into sections
  const motionMatch = text.match(/MOTION:\s*(.*?)(?=\n\s*FOR)/s);
  const forMatch = text.match(/FOR THE MOTION:\s*([\s\S]*?)(?=\n\s*AGAINST)/);
  const againstMatch = text.match(/AGAINST THE MOTION:\s*([\s\S]*?)(?=\n\s*PROVOCATIONS)/);
  const provocationsMatch = text.match(/PROVOCATIONS:\s*([\s\S]*?)$/);

  const parseNumberedList = (text: string | undefined): string[] => {
    if (!text) return [];
    return text
      .split(/\n\d+\.\s*/)
      .map((item) => item.trim())
      .filter(Boolean);
  };

  return {
    generated_at: new Date().toISOString(),
    raw_text: text,
    motion: motionMatch?.[1]?.trim() ?? 'Motion not parsed',
    arguments_for: parseNumberedList(forMatch?.[1]),
    arguments_against: parseNumberedList(againstMatch?.[1]),
    provocations: parseNumberedList(provocationsMatch?.[1]),
    source_reel_ids: sourceReelIds,
  };
}

async function saveBrief(supabase: any, boardId: string, brief: any, tasteProfile: any) {
  const existingBriefs = (tasteProfile?.profile_data as any)?.debate_briefs ?? [];

  await supabase
    .from('taste_profiles')
    .update({
      profile_data: {
        ...(tasteProfile?.profile_data as object),
        debate_briefs: [...existingBriefs, brief],
      },
    })
    .eq('board_id', boardId);
}

function filterDebateReels(reels: any[]): any[] {
  const debateSignals = [
    'political', 'philosophy', 'debate', 'opinion', 'controversial',
    'society', 'capitalism', 'feminism', 'justice', 'rights', 'equality',
    'climate', 'technology', 'AI', 'privacy', 'culture war', 'woke',
    'tradition', 'progressive', 'conservative', 'moral', 'ethical',
    'take', 'hot take', 'unpopular opinion', 'satire', 'commentary',
  ];

  return reels.filter((reel) => {
    if (reel.classification !== 'humour_identity') return false;
    const extractionText = JSON.stringify(reel.extraction_data).toLowerCase();
    return debateSignals.some((signal) => extractionText.includes(signal));
  });
}

function buildDebateBriefPrompt(
  boardName: string,
  identityLabel: string,
  reelSummaries: { id: string; summary: string; url: string }[]
): string {
  const reelsList = reelSummaries
    .map((r, i) => `[Reel ${i + 1}] (ID: ${r.id})\n${r.summary}\nSource: ${r.url}`)
    .join('\n\n');

  return `You are a sharp, provocative debate moderator crafting a weekly discussion brief for a friend group called "${boardName}" (aka "${identityLabel}"). They share political takes, philosophical memes, satire, and hot takes with each other. Your job is to distill their shared content into a structured debate that will get them arguing at dinner.

CONTENT THEY'VE BEEN SHARING:
${reelsList}

Generate a debate brief with this EXACT structure (use these exact headings):

MOTION: [Write a formal debate motion in the style of "This house believes..." that captures the central tension in their shared content. Make it specific to what they've been sharing, not generic.]

FOR THE MOTION:
1. [Argument 1 -- reference specific content they shared] (Source: Reel X)
2. [Argument 2] (Source: Reel X)
3. [Argument 3] (Source: Reel X)

AGAINST THE MOTION:
1. [Counter-argument 1 -- reference specific content they shared] (Source: Reel X)
2. [Counter-argument 2] (Source: Reel X)
3. [Counter-argument 3] (Source: Reel X)

PROVOCATIONS:
1. [A question designed to make someone at the table uncomfortable because it challenges their assumed position]
2. [A question that forces the group to confront a contradiction in their own behaviour]
3. [A "what would you actually do" scenario that tests their convictions]

RULES:
- The motion must be debatable -- reasonable people could disagree.
- Arguments must reference the actual content they shared (cite Reel numbers).
- Provocations should be personal enough to sting but not cruel.
- Write in a tone that matches this group's energy: sharp, irreverent, intellectual.
- Do NOT be generic. This brief should feel like it was written for THIS group.
- Do NOT use emojis.
- Keep each argument to 1-2 sentences max.
- Keep each provocation to 1-2 sentences max.

Generate the debate brief now:`;
}
```

### Debate Brief Card Component

```typescript
// components/shared/DebateBriefCard.tsx
const DebateBriefCard = ({ brief }: { brief: DebateBrief }) => (
  <ScrollView style={styles.container}>
    {/* Motion */}
    <View style={styles.motionCard}>
      <Text style={styles.motionLabel}>THIS WEEK'S MOTION</Text>
      <Text style={styles.motionText}>{brief.motion}</Text>
    </View>

    {/* Arguments */}
    <View style={styles.argumentsContainer}>
      <View style={styles.forSection}>
        <Text style={styles.forHeader}>FOR</Text>
        {brief.arguments_for.map((arg, i) => (
          <Text key={i} style={styles.argument}>{i + 1}. {arg}</Text>
        ))}
      </View>

      <View style={styles.againstSection}>
        <Text style={styles.againstHeader}>AGAINST</Text>
        {brief.arguments_against.map((arg, i) => (
          <Text key={i} style={styles.argument}>{i + 1}. {arg}</Text>
        ))}
      </View>
    </View>

    {/* Provocations */}
    <View style={styles.provocationsSection}>
      <Text style={styles.provocationsHeader}>PROVOCATIONS</Text>
      {brief.provocations.map((q, i) => (
        <Text key={i} style={styles.provocation}>{q}</Text>
      ))}
    </View>

    <Text style={styles.generatedDate}>
      Generated {new Date(brief.generated_at).toLocaleDateString()}
    </Text>
  </ScrollView>
);
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/generate-debate-brief/index.ts` | Edge Function: filters debate reels, builds prompt, calls Claude, parses response, saves brief |
| `components/shared/DebateBriefCard.tsx` | Structured card displaying motion, for/against arguments, and provocations |
| `lib/hooks/use-debate-brief.ts` | Hook for generating, fetching, and managing debate briefs |
| `app/debate-brief.tsx` | Screen for viewing the current debate brief and past briefs |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Add "Debate Brief" section/link on board detail screen |

## Definition of Done

- [ ] Edge Function `generate-debate-brief` deployed and callable
- [ ] Only reels classified as `humour_identity` with debate-worthy signals are used as input
- [ ] Minimum 3 qualifying reels required; disabled with clear message if insufficient
- [ ] Claude prompt includes reel summaries with extraction data, hashtags, transcript excerpts
- [ ] Generated brief includes: motion, 3 arguments for, 3 arguments against, 3 provocations
- [ ] Arguments reference specific reels (source citations)
- [ ] Brief stored in `taste_profiles.profile_data.debate_briefs` array
- [ ] Previous briefs preserved and accessible in "Past Briefs" list
- [ ] Debate brief card displays structured sections clearly
- [ ] Loading state during generation
- [ ] Retry logic on Claude API failure (NFR13)
- [ ] No emojis or generic content in generated brief
- [ ] Motion is specific to the group's shared content, not a generic philosophical question
