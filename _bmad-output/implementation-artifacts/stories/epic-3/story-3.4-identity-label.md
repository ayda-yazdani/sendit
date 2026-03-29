# Story 3.4: Group Identity Label Generation

## Description

As a board member,
I want the app to generate a fun, memorable group identity label based on our taste profile,
So that my friend group has a shareable personality tag that captures who we are.

## Status

- **Epic:** Epic 3 - Group Taste Intelligence
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR23 (generate group identity label)
- **NFRs Covered:** NFR4 (part of taste recalculation < 2s)

## Acceptance Criteria

**Given** a board has 3 or more reels with extraction data
**When** the `taste-update` Edge Function generates the taste profile (Story 3.1)
**Then** the Claude API prompt also generates a group identity label (2-4 words)
**And** the label is a fun, memorable phrase that captures the group's personality (e.g., "The Chaotic Intellectuals", "The Low-Effort Loyalists", "Underground Brunch Club")
**And** the `identity_label` field is saved to the `taste_profiles` row alongside the `profile_data`

**Given** a taste profile is regenerated because a new reel was added
**When** the updated profile data changes significantly
**Then** the identity label may change to reflect the evolved group personality
**And** the old label is overwritten (no history of past labels)

**Given** the identity label is generated
**When** it is displayed on the board detail screen (Story 3.2)
**Then** it appears as a prominent heading above the taste profile section
**And** it is styled as a bold, eye-catching title (e.g., "You are: The Chaotic Intellectuals")

**Given** the taste profile has insufficient data (fewer than 3 reels)
**When** the taste profile section is viewed
**Then** no identity label is displayed and the empty state from Story 3.2 is shown

## Technical Context

### Relevant Schema

```sql
taste_profiles (
  id uuid PK,
  board_id uuid FK -> boards UNIQUE,
  profile_data jsonb DEFAULT '{}',
  identity_label text,       -- <-- This field, generated alongside profile_data
  updated_at timestamptz
)
```

### Architecture References

- **This story modifies Story 3.1's Edge Function** — it extends the Claude prompt used in `taste-update` to also produce the identity label. This is NOT a separate API call; it is part of the same Claude request.
- **Display handled by Story 3.2** — the `TasteProfile.tsx` component already renders `identity_label` if present (per Story 3.2 acceptance criteria). This story ensures the backend produces it.

### Dependencies

- **Story 3.1:** This story extends the `taste-update` Edge Function prompt. Story 3.1 must be implemented first, or both can be implemented together.
- **Story 3.2:** The display component reads `identity_label` from the taste store. Ensure the component handles the label field.

## Implementation Notes

### Modify the Claude Prompt in `taste-update` Edge Function

Extend the system prompt from Story 3.1 to include identity label generation. The label should be part of the same API call, not a separate request — this keeps latency within NFR4 bounds.

**Updated System Prompt (additions in bold context):**

```typescript
const TASTE_PROFILE_SYSTEM_PROMPT = `You are a cultural analyst for a friend group app called Sendit. You analyze shared video content extractions from a friend group and produce a structured taste profile that captures the group's collective personality.

You will receive an array of extraction objects from videos the group has shared. Each extraction contains metadata like venue names, locations, vibes, food references, activity types, humour signals, and the platform it was shared from.

Your job is to synthesize ALL extractions into a single group taste profile. Look for patterns, recurring themes, and collective preferences — not individual outliers.

RULES FOR PROFILE DATA:
- activity_types: Array of 3-7 activity categories the group gravitates toward (e.g., "club nights", "rooftop bars", "dinner spots", "comedy shows", "galleries", "day trips")
- aesthetic: A short phrase (2-5 words) describing the group's overall vibe/aesthetic register (e.g., "underground, intimate", "bougie brunch energy", "chaotic and spontaneous")
- food_preferences: Array of 2-5 cuisine types or food styles (e.g., "Japanese", "street food", "brunch", "late-night kebabs")
- location_patterns: Array of 1-4 geographic areas or neighbourhoods the group's content clusters around (e.g., "east London", "Shoreditch", "Peckham")
- price_range: A human-readable string indicating the group's typical spend per person (e.g., "~£15/head", "£20-40/head", "budget-friendly")
- humour_style: A short phrase capturing the group's humour based on humour/identity content (e.g., "dark, absurdist", "wholesome chaos", "politically unhinged"). If no humour content exists, use "not enough data yet"
- platform_mix: An object counting how many reels came from each platform (e.g., { "tiktok": 5, "instagram": 3, "youtube": 2 })

RULES FOR IDENTITY LABEL:
- identity_label: A fun, memorable 2-4 word group identity label that captures the group's personality
- The label should feel like a group nickname — something friends would actually adopt
- Format: "The [Adjective] [Noun(s)]" or similar catchy pattern
- Examples: "The Chaotic Intellectuals", "The Low-Effort Loyalists", "Underground Brunch Club", "Rooftop Romantics", "The Cultured Degenerates", "East London Explorers", "The Spontaneous Foodies"
- The label should synthesize the group's dominant traits: their activities, aesthetic, humour, and vibe
- Be creative, slightly cheeky, and never generic. Avoid bland labels like "The Fun Group" or "The Friends"

Return ONLY valid JSON with this exact structure:
{
  "profile_data": { activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix },
  "identity_label": "The [Label]"
}

No markdown, no explanation, no wrapping.`;
```

**Updated User Prompt:**

```typescript
const userPrompt = `Here are ${reels.length} video extractions shared by a friend group. Analyze them and produce both the group taste profile AND a catchy group identity label.

EXTRACTIONS:
${JSON.stringify(reelData, null, 2)}

Return JSON with "profile_data" (containing activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix) and "identity_label".`;
```

### Update Response Parsing in `taste-update` Edge Function

The Claude response now returns a wrapper object with both `profile_data` and `identity_label`. Update the parsing logic:

```typescript
// Parse Claude's response
const responseText = await callClaudeWithRetry(userPrompt, TASTE_PROFILE_SYSTEM_PROMPT);
const parsed = JSON.parse(responseText);

// Validate structure
if (!parsed.profile_data || !parsed.identity_label) {
  throw new Error('Missing profile_data or identity_label in Claude response');
}

// Validate profile_data keys
const requiredKeys = ['activity_types', 'aesthetic', 'food_preferences', 'location_patterns', 'price_range', 'humour_style', 'platform_mix'];
for (const key of requiredKeys) {
  if (!(key in parsed.profile_data)) {
    throw new Error(`Missing key in profile_data: ${key}`);
  }
}

// Upsert taste profile
const { data, error } = await supabaseAdmin
  .from('taste_profiles')
  .upsert({
    board_id: boardId,
    profile_data: parsed.profile_data,
    identity_label: parsed.identity_label,
    updated_at: new Date().toISOString(),
  }, { onConflict: 'board_id' })
  .select()
  .single();
```

### Display Integration (Story 3.2 Enhancement)

In `TasteProfile.tsx`, render the identity label when present:

```tsx
{profile?.identity_label && (
  <View style={styles.labelContainer}>
    <Text style={styles.labelPrefix}>You are</Text>
    <Text style={styles.identityLabel}>{profile.identity_label}</Text>
  </View>
)}
```

Style the label prominently — large bold font, centered, possibly with a gradient or accent color background.

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Modify** | `supabase/functions/taste-update/index.ts` | Extend Claude prompt to generate identity_label alongside profile_data; update response parsing and upsert to include identity_label |
| **Modify** | `components/board/TasteProfile.tsx` | Add identity label rendering at the top of the taste profile section (if not already handled in Story 3.2) |

## Definition of Done

- [ ] The `taste-update` Claude prompt includes instructions to generate a 2-4 word group identity label
- [ ] The Claude response is parsed to extract both `profile_data` and `identity_label`
- [ ] Both fields are saved to the `taste_profiles` row in a single upsert
- [ ] The identity label is displayed prominently on the board detail screen above the taste profile
- [ ] The label feels creative and personality-driven (not generic)
- [ ] The label updates when the taste profile is recalculated
- [ ] Validation ensures both `profile_data` and `identity_label` are present before upserting
- [ ] Manual test: board with 5 diverse reels produces a label that clearly reflects the content themes (e.g., food reels + club reels -> food/nightlife label)
