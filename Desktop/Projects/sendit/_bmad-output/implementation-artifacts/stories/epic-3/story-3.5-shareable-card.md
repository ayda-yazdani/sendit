# Story 3.5: Shareable Group Identity Card

## Description

As a board member,
I want to share our group's identity as a visual card image,
So that I can send it to the group chat and show off our collective personality.

## Status

- **Epic:** Epic 3 - Group Taste Intelligence
- **Priority:** P0
- **Branch:** feature/taste-suggestions
- **Assignee:** Person D (Ayday)
- **FRs Covered:** FR24 (view and share group identity as card)
- **NFRs Covered:** None directly — this is a UX feature

## Acceptance Criteria

**Given** a board has a taste profile with an `identity_label` and populated `profile_data`
**When** the user taps "Share Identity" on the board detail screen
**Then** a visual card is rendered off-screen containing:
- The board name at the top
- The identity label as a large headline (e.g., "The Chaotic Intellectuals")
- Key taste attributes: top 3 activity types, aesthetic quote, top food preferences, price range
- A subtle "sendit" watermark/branding at the bottom
**And** the card is captured as a PNG image using `react-native-view-shot`
**And** the native share sheet opens with the card image attached
**And** the user can share it to WhatsApp, Instagram Stories, or any app

**Given** a board does not have a taste profile or identity label
**When** the user looks for the "Share Identity" button
**Then** the button is hidden or disabled with a tooltip: "Need more reels to generate your group identity"

**Given** the share sheet is opened with the identity card
**When** the user selects a target app (e.g., Instagram Stories, WhatsApp)
**Then** the image is shared successfully to that app
**And** the image quality is sufficient for social media (at least 1080px wide)

**Given** the card image is generated
**When** it is displayed before sharing (preview)
**Then** the user can see a preview of the card before confirming the share action

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

boards (
  id uuid PK,
  name text NOT NULL,
  join_code text UNIQUE NOT NULL,
  created_at timestamptz
)
```

### Architecture References

- **Component location:** `components/board/IdentityCard.tsx` per Architecture doc folder structure
- **Image capture:** `react-native-view-shot` — renders a React Native view to a PNG file URI
- **Sharing:** `expo-sharing` — opens the native share sheet with a file URI
- **State:** Read from `useTasteStore` (taste profile) and board data (board name)

### Dependencies

- **Story 3.4:** Identity label must exist in the taste profile
- **Story 3.2:** Taste profile data must be accessible via `useTasteStore`
- **Libraries to install:**
  - `react-native-view-shot` — capture component as image
  - `expo-sharing` — native share sheet

## Implementation Notes

### Install Dependencies

```bash
cd sendit-app
npx expo install react-native-view-shot expo-sharing
```

### Component: `components/board/IdentityCard.tsx`

This component has two responsibilities:
1. **Render the visual card** (used both for preview and for image capture)
2. **Handle the capture-and-share flow**

**Card Design:**

The card should feel like a social media story card — visually striking, sharable, and instantly recognizable. Design guidance:

- **Dimensions:** 1080 x 1920 ratio (9:16 for Instagram Stories) or 1080 x 1080 (square for general sharing). Recommend supporting square as the default since it works everywhere.
- **Background:** Dark gradient (e.g., deep purple to dark blue) or the board's accent color. Avoid pure white — it looks bad on dark-mode Instagram.
- **Board name:** Small text at the top, secondary color, uppercase
- **Identity label:** Large, bold, centered, white text. This is the hero element. Consider a slight text shadow for depth.
- **Taste attributes:** Below the label, show 3-4 key attributes as styled text or chips:
  - Top activity types (e.g., "club nights / rooftop bars / dinner")
  - Aesthetic (e.g., "underground, intimate")
  - Food preferences (e.g., "Japanese / street food")
  - Price range (e.g., "~£15/head")
- **Branding:** "sendit" in small text at the bottom with a subtle opacity

```tsx
import React, { useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import ViewShot from 'react-native-view-shot';
import * as Sharing from 'expo-sharing';

interface IdentityCardProps {
  boardName: string;
  identityLabel: string;
  profileData: {
    activity_types: string[];
    aesthetic: string;
    food_preferences: string[];
    price_range: string;
    humour_style: string;
  };
}

export function IdentityCard({ boardName, identityLabel, profileData }: IdentityCardProps) {
  const viewShotRef = useRef<ViewShot>(null);

  const handleShare = async () => {
    try {
      const uri = await viewShotRef.current?.capture?.();
      if (!uri) {
        Alert.alert('Error', 'Could not capture card image');
        return;
      }

      const isAvailable = await Sharing.isAvailableAsync();
      if (!isAvailable) {
        Alert.alert('Sharing not available', 'Sharing is not available on this device');
        return;
      }

      await Sharing.shareAsync(uri, {
        mimeType: 'image/png',
        dialogTitle: 'Share your group identity',
      });
    } catch (error) {
      console.error('[IdentityCard] Share failed:', error);
      Alert.alert('Error', 'Failed to share identity card');
    }
  };

  return (
    <View>
      {/* Capturable card view */}
      <ViewShot
        ref={viewShotRef}
        options={{ format: 'png', quality: 1.0, width: 1080, height: 1080 }}
        style={styles.cardWrapper}
      >
        <View style={styles.card}>
          <Text style={styles.boardName}>{boardName.toUpperCase()}</Text>
          <Text style={styles.identityLabel}>{identityLabel}</Text>

          <View style={styles.attributesContainer}>
            <Text style={styles.aesthetic}>"{profileData.aesthetic}"</Text>

            <View style={styles.pillRow}>
              {profileData.activity_types.slice(0, 3).map((activity, i) => (
                <View key={i} style={styles.pill}>
                  <Text style={styles.pillText}>{activity}</Text>
                </View>
              ))}
            </View>

            <Text style={styles.foodLine}>
              {profileData.food_preferences.slice(0, 3).join(' / ')}
            </Text>

            <Text style={styles.priceRange}>{profileData.price_range}</Text>
          </View>

          <Text style={styles.branding}>sendit</Text>
        </View>
      </ViewShot>

      {/* Share button */}
      <TouchableOpacity style={styles.shareButton} onPress={handleShare}>
        <Text style={styles.shareButtonText}>Share Identity</Text>
      </TouchableOpacity>
    </View>
  );
}
```

**Styling:**

```typescript
const styles = StyleSheet.create({
  cardWrapper: {
    borderRadius: 16,
    overflow: 'hidden',
    marginHorizontal: 16,
    marginVertical: 8,
  },
  card: {
    backgroundColor: '#1a1a2e',
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    aspectRatio: 1,
  },
  boardName: {
    fontSize: 14,
    color: '#8888aa',
    fontWeight: '600',
    letterSpacing: 2,
    marginBottom: 16,
  },
  identityLabel: {
    fontSize: 32,
    fontWeight: '800',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 24,
    textShadowColor: 'rgba(0,0,0,0.3)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  attributesContainer: {
    alignItems: 'center',
    gap: 12,
  },
  aesthetic: {
    fontSize: 16,
    color: '#ccccdd',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  pill: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  pillText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '500',
  },
  foodLine: {
    fontSize: 14,
    color: '#aaaacc',
    textAlign: 'center',
  },
  priceRange: {
    fontSize: 14,
    color: '#66eebb',
    fontWeight: '600',
  },
  branding: {
    position: 'absolute',
    bottom: 16,
    fontSize: 12,
    color: 'rgba(255,255,255,0.3)',
    fontWeight: '700',
    letterSpacing: 3,
  },
  shareButton: {
    backgroundColor: '#6C5CE7',
    marginHorizontal: 16,
    marginTop: 8,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  shareButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
});
```

### Integration into Board Detail Screen

Add the `IdentityCard` component to the board detail screen, conditionally rendered:

```tsx
// In app/(tabs)/board/[id].tsx
import { IdentityCard } from '@/components/board/IdentityCard';
import { useTasteStore } from '@/lib/stores/taste-store';

// Inside the screen component:
const { profile } = useTasteStore();

{profile?.identity_label && profile?.profile_data && (
  <IdentityCard
    boardName={board.name}
    identityLabel={profile.identity_label}
    profileData={profile.profile_data}
  />
)}
```

### Share Flow

1. User taps "Share Identity"
2. `ViewShot` captures the card view as a 1080x1080 PNG
3. `expo-sharing` opens the native share sheet with the PNG file URI
4. User selects target app (WhatsApp, Instagram, etc.)
5. Image is shared

### Fallback Considerations

- If `react-native-view-shot` is not available (e.g., Expo Go limitations), show the card as a visual-only component without the share button, and display a message: "Run on a device build to enable sharing"
- If `expo-sharing` reports not available, show an alert explaining the limitation

## Files to Create/Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| **Create** | `components/board/IdentityCard.tsx` | Shareable identity card component with ViewShot capture and expo-sharing integration |
| **Modify** | `app/(tabs)/board/[id].tsx` | Add IdentityCard component, conditionally rendered when identity label exists |
| **Modify** | `package.json` | Add react-native-view-shot and expo-sharing dependencies (via npx expo install) |

## Definition of Done

- [ ] `IdentityCard.tsx` component renders a visually appealing card with board name, identity label, and key taste attributes
- [ ] Card uses a dark gradient/solid background suitable for social media sharing
- [ ] "Share Identity" button triggers `react-native-view-shot` capture
- [ ] Captured image is at least 1080px wide with PNG format
- [ ] `expo-sharing` opens the native share sheet with the captured image
- [ ] Card is only shown when `identity_label` and `profile_data` exist
- [ ] Button is hidden/disabled when no identity label is available
- [ ] The card preview is visible on-screen before the user taps share
- [ ] Branding watermark ("sendit") appears subtly on the card
- [ ] `react-native-view-shot` and `expo-sharing` are installed as dependencies
- [ ] Manual test: generate an identity card, share to a messaging app, verify the image looks correct
