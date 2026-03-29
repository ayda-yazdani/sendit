# Story 4.2: Suggestion Card UI with Reasoning

## Description

As a board member,
I want to see the plan suggestion displayed as a rich card with a clear explanation of why it was chosen,
So that I understand the recommendation is based on what our group has been sharing and can trust the suggestion.

## Status

- **Epic:** Epic 4 - Plan Suggestions
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR27 (what/why/where/when/cost/booking), FR31 (view reasoning — which reels influenced it)
- **NFRs Covered:** NFR2 (real-time propagation), NFR16 (Realtime subscriptions)

## Acceptance Criteria

**Given** an active suggestion exists for the board
**When** the user navigates to the suggestion screen (or the suggestion tab on the board)
**Then** a suggestion card is displayed showing:
- **What:** Plan title/description as a headline
- **Where:** Venue name and address, styled with a location pin icon
- **When:** Date and time, styled with a calendar icon
- **Cost:** Per-person cost, styled with a currency icon
- **Booking link:** A tappable "Book Now" button that opens the URL in the device browser (if `booking_url` is not empty)

**Given** the suggestion card is displayed
**When** the user taps "Why this?" or an expand toggle
**Then** an expandable section reveals:
- The `why` text explaining the reasoning
- A list of "influenced by" reels: for each reel UUID in `influenced_by`, fetch the reel's extraction data and display a mini extraction card (platform icon, classification badge, venue or vibe text)
- Each mini reel card is tappable and navigates to the full extraction card view

**Given** the suggestion has no `booking_url` (empty string)
**When** the card is rendered
**Then** the "Book Now" button is hidden

**Given** no active suggestion exists for the board
**When** the user navigates to the suggestion screen
**Then** an empty state is shown with:
- Text: "No suggestions yet"
- A "Generate Suggestion" button that calls the `suggest` Edge Function
- The button shows a loading spinner while the suggestion is being generated

**Given** a new suggestion is created while the user is viewing the suggestion screen
**When** the suggestion is inserted into the `suggestions` table
**Then** the card appears in real-time via Supabase Realtime subscription

**Given** the user taps the "Book Now" button
**When** the `booking_url` is a valid URL
**Then** the URL opens in the device's default browser via `expo-linking`

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

reels (
  id uuid PK,
  board_id uuid FK -> boards,
  url text,
  platform text,
  extraction_data jsonb,
  classification text,
  created_at timestamptz
)
```

**suggestion_data jsonb:**

```json
{
  "what": "Club night at Peckham Audio",
  "why": "3 of you have been sending underground music reels for 2 weeks",
  "where": "Peckham Audio, 133 Rye Lane, London SE15",
  "when": "Saturday 5 April, 10pm",
  "cost_per_person": "£12",
  "booking_url": "https://ra.co/events/...",
  "influenced_by": ["reel-uuid-1", "reel-uuid-2", "reel-uuid-3"]
}
```

### Architecture References

- **Component location:** `components/suggestion/SuggestionCard.tsx`
- **Screen:** `app/(tabs)/suggestion/[id].tsx` or rendered within the board detail screen as a section
- **State:** Fetch suggestion via Supabase query, subscribe via Realtime
- **Linking:** `expo-linking` to open booking URLs (already installed)
- **Navigation:** Tapping an influenced reel navigates to the reel's extraction card

### Dependencies

- **Story 4.1:** `suggest` Edge Function must exist and produce valid suggestions
- **Epic 2 (Story 2.6):** Extraction card UI must exist for displaying influenced reels
- **Epic 1:** Board detail screen and navigation must exist
- **Library:** `expo-linking` (already installed)

## Implementation Notes

### Component: `components/suggestion/SuggestionCard.tsx`

**Card Layout:**

The suggestion card is the hero element of the suggestion screen. It should feel premium and actionable.

```
┌─────────────────────────────────────┐
│  ✨ SUGGESTION                       │
│                                     │
│  Club night at Peckham Audio        │  <- what (headline)
│                                     │
│  📍 Peckham Audio, 133 Rye Lane...  │  <- where
│  📅 Saturday 5 April, 10pm         │  <- when
│  💰 £12 per person                  │  <- cost
│                                     │
│  ┌─────────────────────────────┐   │
│  │       Book Now →             │   │  <- booking link button
│  └─────────────────────────────┘   │
│                                     │
│  ▾ Why this?                        │  <- expandable toggle
│  ┌─────────────────────────────┐   │
│  │ "3 of you have been sending  │   │  <- why text
│  │  underground music reels..." │   │
│  │                              │   │
│  │ Influenced by:               │   │
│  │ ┌──────┐ ┌──────┐ ┌──────┐ │   │  <- mini reel cards
│  │ │TikTok│ │Insta │ │YT    │ │   │
│  │ │Rave  │ │Club  │ │Music │ │   │
│  │ └──────┘ └──────┘ └──────┘ │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Component Structure:**

```tsx
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, ScrollView } from 'react-native';
import * as Linking from 'expo-linking';
import { supabase } from '@/lib/supabase';

interface SuggestionData {
  what: string;
  why: string;
  where: string;
  when: string;
  cost_per_person: string;
  booking_url: string;
  influenced_by: string[]; // reel UUIDs
}

interface Suggestion {
  id: string;
  board_id: string;
  suggestion_data: SuggestionData;
  status: string;
  created_at: string;
}

interface ReelPreview {
  id: string;
  platform: string;
  classification: string;
  extraction_data: Record<string, any>;
}

interface SuggestionCardProps {
  suggestion: Suggestion;
  onRegenerate?: () => void; // Story 4.4
}

export function SuggestionCard({ suggestion, onRegenerate }: SuggestionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [influencedReels, setInfluencedReels] = useState<ReelPreview[]>([]);
  const data = suggestion.suggestion_data;

  // Fetch influenced reels when section is expanded
  useEffect(() => {
    if (expanded && data.influenced_by?.length > 0 && influencedReels.length === 0) {
      fetchInfluencedReels();
    }
  }, [expanded]);

  async function fetchInfluencedReels() {
    const { data: reels } = await supabase
      .from('reels')
      .select('id, platform, classification, extraction_data')
      .in('id', data.influenced_by);

    if (reels) setInfluencedReels(reels);
  }

  function handleBooking() {
    if (data.booking_url) {
      Linking.openURL(data.booking_url);
    }
  }

  return (
    <View style={styles.card}>
      <Text style={styles.sectionLabel}>SUGGESTION</Text>

      {/* What */}
      <Text style={styles.what}>{data.what}</Text>

      {/* Where */}
      <View style={styles.detailRow}>
        <Text style={styles.detailIcon}>📍</Text>
        <Text style={styles.detailText}>{data.where}</Text>
      </View>

      {/* When */}
      <View style={styles.detailRow}>
        <Text style={styles.detailIcon}>📅</Text>
        <Text style={styles.detailText}>{data.when}</Text>
      </View>

      {/* Cost */}
      <View style={styles.detailRow}>
        <Text style={styles.detailIcon}>💰</Text>
        <Text style={styles.detailText}>{data.cost_per_person} per person</Text>
      </View>

      {/* Booking button */}
      {data.booking_url ? (
        <TouchableOpacity style={styles.bookButton} onPress={handleBooking}>
          <Text style={styles.bookButtonText}>Book Now</Text>
        </TouchableOpacity>
      ) : null}

      {/* Why this? expandable */}
      <TouchableOpacity
        style={styles.whyToggle}
        onPress={() => setExpanded(!expanded)}
      >
        <Text style={styles.whyToggleText}>
          {expanded ? '▴ Why this?' : '▾ Why this?'}
        </Text>
      </TouchableOpacity>

      {expanded && (
        <View style={styles.whySection}>
          <Text style={styles.whyText}>{data.why}</Text>

          {influencedReels.length > 0 && (
            <View style={styles.influencedSection}>
              <Text style={styles.influencedLabel}>Influenced by:</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {influencedReels.map((reel) => (
                  <MiniReelCard key={reel.id} reel={reel} />
                ))}
              </ScrollView>
            </View>
          )}
        </View>
      )}
    </View>
  );
}
```

### Mini Reel Card Sub-Component

A compact representation of an influenced reel:

```tsx
function MiniReelCard({ reel }: { reel: ReelPreview }) {
  const platformColors: Record<string, string> = {
    tiktok: '#00f2ea',
    instagram: '#E1306C',
    youtube: '#FF0000',
    x: '#1DA1F2',
    other: '#888888',
  };

  const classificationLabels: Record<string, string> = {
    real_event: 'Event',
    real_venue: 'Venue',
    vibe_inspiration: 'Vibe',
    recipe_food: 'Food',
    humour_identity: 'Humour',
  };

  const title = reel.extraction_data?.venue_name
    || reel.extraction_data?.title
    || reel.extraction_data?.vibe
    || reel.classification;

  return (
    <View style={[miniStyles.card, { borderLeftColor: platformColors[reel.platform] || '#888' }]}>
      <Text style={miniStyles.platform}>{reel.platform}</Text>
      <Text style={miniStyles.classification}>
        {classificationLabels[reel.classification] || reel.classification}
      </Text>
      <Text style={miniStyles.title} numberOfLines={2}>{title}</Text>
    </View>
  );
}
```

### Suggestion Screen / Section Integration

The suggestion card can live either:
- **Option A:** As a dedicated screen `app/(tabs)/suggestion/[id].tsx` navigated from the board
- **Option B:** As a section within the board detail screen `app/(tabs)/board/[id].tsx`

For the hackathon, Option B is faster — render the active suggestion directly on the board detail screen below the taste profile.

```tsx
// In board detail screen
const [activeSuggestion, setActiveSuggestion] = useState<Suggestion | null>(null);

useEffect(() => {
  // Fetch active suggestion
  supabase
    .from('suggestions')
    .select('*')
    .eq('board_id', boardId)
    .eq('status', 'active')
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
    .then(({ data }) => setActiveSuggestion(data));
}, [boardId]);

// Realtime subscription for new suggestions
useEffect(() => {
  const channel = supabase
    .channel(`suggestions-${boardId}`)
    .on('postgres_changes', {
      event: '*',
      schema: 'public',
      table: 'suggestions',
      filter: `board_id=eq.${boardId}`,
    }, (payload) => {
      if (payload.eventType === 'INSERT' && payload.new.status === 'active') {
        setActiveSuggestion(payload.new as Suggestion);
      }
      if (payload.eventType === 'UPDATE' && payload.new.status === 'archived') {
        if (activeSuggestion?.id === payload.new.id) {
          setActiveSuggestion(null);
        }
      }
    })
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}, [boardId]);
```

### Empty State with Generate Button

```tsx
{!activeSuggestion && (
  <View style={styles.emptyState}>
    <Text style={styles.emptyText}>No suggestions yet</Text>
    <TouchableOpacity
      style={styles.generateButton}
      onPress={async () => {
        setLoading(true);
        try {
          await generateSuggestion(boardId);
          // Realtime will pick up the new suggestion
        } catch (error) {
          Alert.alert('Error', 'Could not generate suggestion');
        } finally {
          setLoading(false);
        }
      }}
    >
      {loading ? (
        <ActivityIndicator color="#fff" />
      ) : (
        <Text style={styles.generateButtonText}>Generate Suggestion</Text>
      )}
    </TouchableOpacity>
  </View>
)}
```

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Create** | `components/suggestion/SuggestionCard.tsx` | Suggestion card component with what/where/when/cost/booking and expandable "Why this?" reasoning section |
| **Modify** | `app/(tabs)/board/[id].tsx` | Add suggestion section with SuggestionCard, empty state with generate button, and Realtime subscription for suggestions |

## Definition of Done

- [ ] `SuggestionCard.tsx` renders all suggestion fields: what, where, when, cost
- [ ] "Book Now" button opens `booking_url` in the device browser via `expo-linking`
- [ ] "Book Now" button is hidden when `booking_url` is empty
- [ ] "Why this?" toggle expands to show the reasoning text and influenced reels
- [ ] Influenced reels are fetched on-demand when the section is expanded
- [ ] Each influenced reel is displayed as a mini card with platform, classification, and title
- [ ] Empty state shows "No suggestions yet" with a "Generate Suggestion" button
- [ ] Generate button shows loading spinner during suggestion generation
- [ ] Realtime subscription updates the card when a new suggestion is inserted
- [ ] Realtime subscription removes the card when the active suggestion is archived
- [ ] Component is integrated into the board detail screen
- [ ] Manual test: create a suggestion via the Edge Function, verify it appears on the board with all fields rendered correctly
