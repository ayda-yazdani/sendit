# Story 3.2: Taste Profile Display

## Description

As a board member,
I want to see the group's taste profile displayed visually on the board screen,
So that I can see what our group is collectively into and experience the "that's literally us" moment.

## Status

- **Epic:** Epic 3 - Group Taste Intelligence
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR22 (view taste profile), FR25 (cross-platform signals)
- **NFRs Covered:** NFR2 (real-time updates < 1s), NFR16 (Realtime subscriptions)

## Acceptance Criteria

**Given** a board has a `taste_profiles` row with populated `profile_data`
**When** the user navigates to the board detail screen
**Then** a taste profile section is rendered showing:
- Activity types as colored pill/chip components
- Food preferences as emoji + text labels (e.g., "🍣 Japanese", "🌮 Street food")
- Aesthetic as a styled quote or banner text
- Location patterns as map-pin-styled labels (e.g., "📍 East London")
- Price range as a highlighted badge
- Humour style as an italic descriptor
- Platform mix as a mini horizontal bar or icon row showing relative platform distribution
**And** the section is collapsible/expandable to avoid overwhelming the board view

**Given** a board does not have a `taste_profiles` row (or `profile_data` is empty)
**When** the user views the board detail screen
**Then** an empty state is shown: "Share 3+ reels to unlock your group taste profile" with a subtle animation or icon

**Given** the taste profile is displayed on screen
**When** another member adds a reel and the `taste-update` function runs (Story 3.3)
**And** the `taste_profiles` row is updated in Supabase
**Then** the taste profile UI updates in real-time without the user refreshing
**And** new/changed values are visually distinguishable briefly (subtle highlight or animation)

**Given** the taste profile includes an `identity_label` (Story 3.4)
**When** the profile is displayed
**Then** the identity label appears prominently at the top of the taste section as a heading

## Technical Context

### Relevant Schema

```sql
taste_profiles (
  id uuid PK,
  board_id uuid FK -> boards UNIQUE,
  profile_data jsonb DEFAULT '{}',
  identity_label text,
  updated_at timestamptz
)
```

**profile_data jsonb:**

```json
{
  "activity_types": ["club nights", "rooftop bars", "dinner"],
  "aesthetic": "underground, intimate",
  "food_preferences": ["Japanese", "street food"],
  "location_patterns": ["east London", "Shoreditch"],
  "price_range": "~£15/head",
  "humour_style": "dark, absurdist",
  "platform_mix": { "tiktok": 5, "instagram": 3, "youtube": 2 }
}
```

### Architecture References

- **Component location:** `components/board/TasteProfile.tsx` per folder structure in Architecture doc
- **State management:** Zustand `taste-store.ts` for caching and real-time updates
- **Realtime hook:** `lib/hooks/use-realtime.ts` — already exists from Epic 1. Subscribe to `taste_profiles` table filtered by `board_id`.
- **Styling:** React Native `StyleSheet` — use the existing color constants from `constants/Colors.ts`
- **Screen integration:** The component will be rendered inside the board detail screen at `app/(tabs)/board/[id].tsx`

### Dependencies

- **Story 3.1:** `taste-update` Edge Function must exist and produce valid `profile_data`
- **Epic 1:** Board detail screen and navigation must exist
- **Epic 1:** `use-realtime.ts` hook must be available for Realtime subscriptions
- **Library:** No new dependencies required beyond what Expo + React Native provides

## Implementation Notes

### Zustand Store: `lib/stores/taste-store.ts`

Create a Zustand store to hold the taste profile state for the active board.

```typescript
import { create } from 'zustand';
import { supabase } from '../supabase';

interface TasteProfile {
  id: string;
  board_id: string;
  profile_data: ProfileData;
  identity_label: string | null;
  updated_at: string;
}

interface ProfileData {
  activity_types: string[];
  aesthetic: string;
  food_preferences: string[];
  location_patterns: string[];
  price_range: string;
  humour_style: string;
  platform_mix: Record<string, number>;
}

interface TasteStore {
  profile: TasteProfile | null;
  loading: boolean;
  error: string | null;
  fetchProfile: (boardId: string) => Promise<void>;
  setProfile: (profile: TasteProfile) => void;
  clearProfile: () => void;
}

export const useTasteStore = create<TasteStore>((set) => ({
  profile: null,
  loading: false,
  error: null,

  fetchProfile: async (boardId: string) => {
    set({ loading: true, error: null });
    const { data, error } = await supabase
      .from('taste_profiles')
      .select('*')
      .eq('board_id', boardId)
      .single();

    if (error && error.code !== 'PGRST116') {
      set({ loading: false, error: error.message });
      return;
    }
    set({ profile: data, loading: false });
  },

  setProfile: (profile) => set({ profile }),
  clearProfile: () => set({ profile: null, loading: false, error: null }),
}));
```

### Component: `components/board/TasteProfile.tsx`

**Visual design guidance:**

- **Activity types:** Rendered as horizontally scrolling colored pills. Use a color palette that cycles through 5-6 distinct colors. Each pill has rounded corners, padding, and the activity text in white.
- **Food preferences:** Horizontal row of chips with auto-mapped emoji prefixes. Map common foods to emojis: `Japanese -> 🍣`, `street food -> 🌮`, `brunch -> 🥞`, `Italian -> 🍝`, `Indian -> 🍛`, `coffee -> ☕`. Default to `🍽️` for unknown.
- **Aesthetic:** Displayed as a centered italic text block with a subtle background tint, like a quote card.
- **Location patterns:** Each location shown with a `📍` prefix in a muted chip style.
- **Price range:** Displayed as a standalone badge with a `💰` icon, styled distinctly (e.g., green background).
- **Humour style:** Italic text below the aesthetic, smaller font, with a `😈` or `😂` prefix.
- **Platform mix:** Horizontal bar showing platform icons (TikTok, Instagram, YouTube) with proportional widths based on counts. Or simple icon + count row.

**Empty state:** When `profile_data` is empty or the taste_profiles row doesn't exist, show an empty state with an illustration or icon and the text "Share 3+ reels to unlock your group taste profile".

**Realtime subscription:** In the board detail screen (or within the component itself), subscribe to Realtime changes on `taste_profiles` where `board_id` matches. On `INSERT` or `UPDATE`, call `useTasteStore.getState().setProfile(payload.new)`.

```typescript
// Inside board detail screen or a useEffect in TasteProfile
useEffect(() => {
  const channel = supabase
    .channel(`taste-${boardId}`)
    .on('postgres_changes', {
      event: '*',
      schema: 'public',
      table: 'taste_profiles',
      filter: `board_id=eq.${boardId}`,
    }, (payload) => {
      if (payload.new) {
        useTasteStore.getState().setProfile(payload.new as TasteProfile);
      }
    })
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}, [boardId]);
```

### Food Emoji Mapping Utility

```typescript
const FOOD_EMOJI_MAP: Record<string, string> = {
  japanese: '🍣',
  sushi: '🍣',
  ramen: '🍜',
  chinese: '🥡',
  italian: '🍝',
  pizza: '🍕',
  mexican: '🌮',
  'street food': '🌮',
  indian: '🍛',
  thai: '🍛',
  korean: '🍛',
  brunch: '🥞',
  breakfast: '🥞',
  coffee: '☕',
  dessert: '🍰',
  burger: '🍔',
  bbq: '🍖',
  seafood: '🦐',
  vegan: '🥗',
  kebab: '🥙',
};

export function getFoodEmoji(food: string): string {
  const key = food.toLowerCase();
  return FOOD_EMOJI_MAP[key] || '🍽️';
}
```

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Create** | `lib/stores/taste-store.ts` | Zustand store for taste profile state |
| **Create** | `components/board/TasteProfile.tsx` | Taste profile display component with pills, chips, and emoji labels |
| **Modify** | `app/(tabs)/board/[id].tsx` | Add `<TasteProfile />` component to board detail screen, add Realtime subscription |

## Definition of Done

- [ ] `TasteProfile.tsx` component renders all 7 profile fields with the specified visual treatment
- [ ] Activity types render as colored scrollable pills
- [ ] Food preferences render with auto-mapped emoji prefixes
- [ ] Aesthetic renders as a styled quote/banner
- [ ] Location patterns render with map pin icons
- [ ] Price range renders as a highlighted badge
- [ ] Humour style renders as italic descriptor text
- [ ] Platform mix renders as an icon + count row or proportional bar
- [ ] Empty state renders when no taste profile exists for the board
- [ ] `taste-store.ts` Zustand store manages profile state with `fetchProfile`, `setProfile`, `clearProfile` actions
- [ ] Realtime subscription on `taste_profiles` table updates the UI without manual refresh
- [ ] Identity label (if present) renders as a prominent heading above the profile
- [ ] Component is integrated into the board detail screen
- [ ] Visual test: component looks correct with sample data matching the `profile_data` schema
