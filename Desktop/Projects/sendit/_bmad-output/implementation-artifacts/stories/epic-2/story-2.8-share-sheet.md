# Story 2.8: Share Sheet Integration

## Description

As a user browsing Instagram/TikTok/YouTube,
I want to share a URL to Sendit via the native share sheet,
So that adding content is as easy as forwarding a reel.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0 (with P1 fallback — see Risk section)
- **Branch:** `feature/ai-extraction`
- **Assignee:** Person C (client/UI)
- **FRs Covered:** FR8, FR9
- **Depends On:** Story 2.1 (reel creation + extraction invocation), Epic 1 (boards, members, auth)

## Acceptance Criteria

**Given** the user is in any app (Instagram, TikTok, YouTube, Safari, etc.) and taps the native Share button
**When** they select "Sendit" from the share sheet
**Then** the Sendit share extension receives the shared URL
**And** a board picker modal appears showing all boards the user belongs to
**And** after selecting a board, the reel is created and extraction begins
**And** the share extension dismisses with a success confirmation

**Given** the user selects a board in the share extension
**When** the reel is submitted
**Then** the reel row is created in Supabase with the correct `board_id`, `added_by`, `url`, and `platform`
**And** the `extract` Edge Function is invoked
**And** the reel appears on the board for all members via Realtime (Story 2.7)

**Given** the user belongs to only one board
**When** the share extension opens
**Then** that board is pre-selected (no picker needed)
**And** the user only needs to confirm with a "Send" button

**Given** the user shares a URL that already exists on the selected board
**When** the duplicate is detected
**Then** the share extension shows "Already shared on this board"
**And** no duplicate row is created

**Given** the share extension requires native code that is incompatible with Expo managed workflow
**When** the Expo config plugin approach fails or is too complex for the hackathon
**Then** the team falls back to paste URL (Story 2.1) as the primary input method
**And** a deep link handler is implemented as an alternative: `sendit://share?url=ENCODED_URL`

## Technical Context

### Share Extension Architecture

There are two approaches for share sheet integration with Expo:

**Approach A: Expo Config Plugin (Recommended Attempt)**
- Uses `expo-share-intent` community package or a custom config plugin
- Adds an iOS Share Extension target and Android intent filter via Expo prebuild
- Requires `npx expo prebuild` to generate native projects
- Share extension runs as a separate process — cannot directly access the React Native app state

**Approach B: Deep Link Fallback (Guaranteed to Work)**
- Register `sendit://` custom URL scheme via Expo Linking
- Users copy URL from any app, then open Sendit (or use a "Share to Sendit" shortcut)
- Less seamless but fully compatible with Expo managed workflow

### Architecture References

- **Board picker component:** `components/board/BoardPicker.tsx` — reusable board selection modal
- **Reel creation flow:** `lib/ai/extraction.ts` and board store from Story 2.1
- **Auth store:** `lib/stores/auth-store.ts` — provides member ID
- **Board store:** `lib/stores/board-store.ts` — provides board list
- **Deep linking:** Expo Router handles `sendit://` and universal links
- **Share extension package:** `expo-share-intent` (community) — handles receiving shared content

### Dependencies

- Story 2.1 (reel creation + platform detection + extraction invocation)
- Story 2.7 (Realtime — so the reel appears on the board for others)
- Epic 1 (boards list, member identity)
- For Approach A: `npx expo prebuild` must be run to generate iOS/Android native projects

## Implementation Notes

### Approach A: expo-share-intent (Primary)

#### 1. Install and Configure

```bash
cd sendit-app
npx expo install expo-share-intent
```

Add to `app.json` / `app.config.ts`:

```json
{
  "expo": {
    "plugins": [
      [
        "expo-share-intent",
        {
          "iosActivationRules": {
            "NSExtensionActivationSupportsWebURLWithMaxCount": 1
          },
          "androidIntentFilters": [
            "text/plain"
          ]
        }
      ]
    ],
    "scheme": "sendit"
  }
}
```

Run prebuild to generate native code:

```bash
npx expo prebuild
```

#### 2. Share Intent Handler

Create a hook that listens for incoming share intents:

**File:** `lib/hooks/use-share-intent.ts`

```typescript
import { useEffect, useState } from 'react';
import { useShareIntent } from 'expo-share-intent';

interface SharedContent {
  url: string | null;
  text: string | null;
}

export function useIncomingShare() {
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();
  const [sharedUrl, setSharedUrl] = useState<string | null>(null);

  useEffect(() => {
    if (hasShareIntent && shareIntent) {
      // Extract URL from shared content
      let url: string | null = null;

      if (shareIntent.webUrl) {
        url = shareIntent.webUrl;
      } else if (shareIntent.text) {
        // Try to extract URL from shared text
        const urlMatch = shareIntent.text.match(
          /https?:\/\/[^\s]+/
        );
        if (urlMatch) {
          url = urlMatch[0];
        }
      }

      if (url) {
        setSharedUrl(url);
      }
    }
  }, [hasShareIntent, shareIntent]);

  const clearSharedUrl = () => {
    setSharedUrl(null);
    resetShareIntent();
  };

  return { sharedUrl, clearSharedUrl };
}
```

#### 3. Share Sheet Entry Point

When the app receives a share intent, show a board picker modal immediately. This should be handled at the root layout level.

**File:** `app/_layout.tsx` (modification)

```typescript
import { useIncomingShare } from '@/lib/hooks/use-share-intent';
import { ShareToBoard } from '@/components/board/ShareToBoard';

export default function RootLayout() {
  const { sharedUrl, clearSharedUrl } = useIncomingShare();

  return (
    <>
      <Stack>
        {/* existing screens */}
      </Stack>

      {/* Share sheet modal — shown when URL is received from share intent */}
      {sharedUrl && (
        <ShareToBoard
          url={sharedUrl}
          onDismiss={clearSharedUrl}
        />
      )}
    </>
  );
}
```

#### 4. ShareToBoard Component (Board Picker + Submit)

**File:** `components/board/ShareToBoard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  FlatList,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '@/lib/supabase';
import { detectPlatform } from '@/lib/utils/platform-detect';
import { PLATFORM_ICONS } from '@/lib/utils/platform-icons';
import { invokeExtraction } from '@/lib/ai/extraction';

interface ShareToBoardProps {
  url: string;
  onDismiss: () => void;
}

interface Board {
  id: string;
  name: string;
}

export function ShareToBoard({ url, onDismiss }: ShareToBoardProps) {
  const [boards, setBoards] = useState<Board[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const platform = detectPlatform(url);
  const platformInfo = PLATFORM_ICONS[platform];

  // Fetch user's boards
  useEffect(() => {
    async function fetchBoards() {
      // Get current member's device_id from auth store
      const deviceId = await getDeviceId(); // from auth-store

      const { data: memberRows } = await supabase
        .from('members')
        .select('board_id, boards(id, name)')
        .eq('device_id', deviceId);

      if (memberRows) {
        const boardList = memberRows
          .map((m: any) => m.boards)
          .filter(Boolean) as Board[];
        setBoards(boardList);

        // Auto-select if only one board
        if (boardList.length === 1) {
          setSelectedBoardId(boardList[0].id);
        }
      }
      setLoading(false);
    }

    fetchBoards();
  }, []);

  async function handleSubmit() {
    if (!selectedBoardId) return;

    setSubmitting(true);
    setError(null);

    try {
      // Get member ID for this board
      const deviceId = await getDeviceId();
      const { data: member } = await supabase
        .from('members')
        .select('id')
        .eq('board_id', selectedBoardId)
        .eq('device_id', deviceId)
        .single();

      if (!member) throw new Error('Not a member of this board');

      // Insert reel
      const { data: reel, error: insertError } = await supabase
        .from('reels')
        .insert({
          board_id: selectedBoardId,
          added_by: member.id,
          url: url.trim(),
          platform,
        })
        .select()
        .single();

      if (insertError) {
        if (insertError.code === '23505') {
          setError('Already shared on this board');
          setSubmitting(false);
          return;
        }
        throw insertError;
      }

      // Trigger extraction
      invokeExtraction(reel.id, url).catch(console.error);

      setSuccess(true);

      // Auto-dismiss after short delay
      setTimeout(() => {
        onDismiss();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to share. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      visible
      transparent
      animationType="slide"
      onRequestClose={onDismiss}
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Share to Sendit</Text>
            <Pressable onPress={onDismiss}>
              <Ionicons name="close" size={24} color="#666" />
            </Pressable>
          </View>

          {/* URL Preview */}
          <View style={styles.urlPreview}>
            <Ionicons
              name={platformInfo?.name || 'link'}
              size={20}
              color={platformInfo?.color || '#666'}
            />
            <Text style={styles.urlText} numberOfLines={1}>
              {url}
            </Text>
          </View>

          {/* Board List */}
          {loading ? (
            <ActivityIndicator style={{ marginTop: 20 }} />
          ) : boards.length === 0 ? (
            <Text style={styles.emptyText}>No boards yet. Create one first!</Text>
          ) : (
            <FlatList
              data={boards}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <Pressable
                  style={[
                    styles.boardRow,
                    selectedBoardId === item.id && styles.boardRowSelected,
                  ]}
                  onPress={() => setSelectedBoardId(item.id)}
                >
                  <Ionicons
                    name={selectedBoardId === item.id ? 'radio-button-on' : 'radio-button-off'}
                    size={20}
                    color={selectedBoardId === item.id ? '#4ECDC4' : '#CCC'}
                  />
                  <Text style={styles.boardName}>{item.name}</Text>
                </Pressable>
              )}
              style={styles.boardList}
            />
          )}

          {/* Error */}
          {error && <Text style={styles.errorText}>{error}</Text>}

          {/* Success */}
          {success && (
            <View style={styles.successRow}>
              <Ionicons name="checkmark-circle" size={20} color="#34D399" />
              <Text style={styles.successText}>Shared!</Text>
            </View>
          )}

          {/* Submit Button */}
          {!success && (
            <Pressable
              style={[
                styles.submitButton,
                (!selectedBoardId || submitting) && styles.submitButtonDisabled,
              ]}
              onPress={handleSubmit}
              disabled={!selectedBoardId || submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={styles.submitText}>Send</Text>
              )}
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
}

// getDeviceId helper — reads from SecureStore (same as auth-store)
async function getDeviceId(): Promise<string> {
  const SecureStore = require('expo-secure-store');
  const deviceId = await SecureStore.getItemAsync('device_id');
  if (!deviceId) throw new Error('No device session');
  return deviceId;
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '60%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  urlPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F5F5F5',
    padding: 10,
    borderRadius: 8,
    marginBottom: 16,
  },
  urlText: {
    fontSize: 13,
    color: '#666',
    flex: 1,
  },
  boardList: {
    maxHeight: 200,
  },
  boardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  boardRowSelected: {
    backgroundColor: '#F0FDFA',
  },
  boardName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#1A1A1A',
  },
  emptyText: {
    textAlign: 'center',
    color: '#888',
    marginTop: 20,
    fontSize: 14,
  },
  errorText: {
    color: '#FF4444',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 8,
  },
  successRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 16,
  },
  successText: {
    color: '#34D399',
    fontSize: 16,
    fontWeight: '600',
  },
  submitButton: {
    backgroundColor: '#4ECDC4',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 16,
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
```

### Approach B: Deep Link Fallback

If Approach A fails (expo-share-intent is too complex, prebuild breaks something, or the share extension doesn't work on simulator), implement deep link handling as the fallback.

#### 1. URL Scheme Configuration

Already configured in `app.json`:

```json
{
  "expo": {
    "scheme": "sendit"
  }
}
```

#### 2. Deep Link Handler

**File:** `app/_layout.tsx` (modification for deep links)

```typescript
import * as Linking from 'expo-linking';
import { useEffect, useState } from 'react';

export default function RootLayout() {
  const [sharedUrl, setSharedUrl] = useState<string | null>(null);

  // Handle incoming deep links
  useEffect(() => {
    // Handle URL that launched the app
    Linking.getInitialURL().then(handleDeepLink);

    // Handle URLs while app is running
    const subscription = Linking.addEventListener('url', (event) => {
      handleDeepLink(event.url);
    });

    return () => subscription.remove();
  }, []);

  function handleDeepLink(url: string | null) {
    if (!url) return;

    // Parse sendit://share?url=ENCODED_URL
    const parsed = Linking.parse(url);
    if (parsed.path === 'share' && parsed.queryParams?.url) {
      const decodedUrl = decodeURIComponent(parsed.queryParams.url as string);
      setSharedUrl(decodedUrl);
    }
  }

  return (
    <>
      <Stack>{/* screens */}</Stack>
      {sharedUrl && (
        <ShareToBoard url={sharedUrl} onDismiss={() => setSharedUrl(null)} />
      )}
    </>
  );
}
```

#### 3. iOS Shortcut (Alternative to Share Extension)

If the share extension cannot be built, create a simple iOS Shortcut that users can add to their share sheet:

1. Open the Shortcuts app
2. Create a shortcut: "Share to Sendit"
3. Action: Open URL → `sendit://share?url=[Shortcut Input]`
4. Enable "Show in Share Sheet"

This provides share sheet presence without native code. Document this as a setup step for testers.

### Approach Decision Tree

```
Can we install expo-share-intent and run prebuild?
├── YES → Use Approach A (native share extension)
│   ├── Does it work on iOS simulator? → Ship it
│   └── Simulator fails? → Use Approach B for demo
└── NO → Use Approach B (deep link + Shortcuts workaround)
    └── Always works, less seamless
```

### 5. Testing the Share Extension

If using Approach A, test on a physical device or a simulator that supports share extensions:

```bash
# Build for iOS simulator with native share extension
npx expo run:ios

# Build for Android emulator
npx expo run:android
```

Note: Expo Go does NOT support share extensions. A development build is required.

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `lib/hooks/use-share-intent.ts` | Hook for receiving URLs from native share sheet |
| `components/board/ShareToBoard.tsx` | Board picker modal for share sheet flow |
| `components/board/BoardPicker.tsx` | Reusable board selection list (extracted from ShareToBoard if needed elsewhere) |

### Modify

| File | Change |
|------|--------|
| `app/_layout.tsx` | Add share intent listener and deep link handler, render `ShareToBoard` modal when URL received |
| `app.json` or `app.config.ts` | Add `expo-share-intent` plugin config, URL scheme `sendit` |
| `package.json` | Add `expo-share-intent` dependency |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `expo-share-intent` incompatible with current Expo SDK version | Medium | High | Check compatibility before starting. Fallback to Approach B. |
| Share extension does not work in iOS simulator | High | Medium | Test on physical device. For demo, use paste URL (Story 2.1). |
| Prebuild breaks existing Expo managed workflow | Low | High | Run prebuild on a branch. If it breaks, revert and use Approach B. |
| Android intent filter receives unexpected content types | Low | Low | Validate incoming content, ignore non-URL shares. |
| User has no boards when share extension opens | Low | Medium | Show "Create a board first" message with link to open the app. |

**Hackathon Strategy:** Attempt Approach A first (spend max 2 hours). If it works, it is the "zero new behaviour" differentiator for the demo. If it fails, fall back to paste URL immediately and note share sheet as "implemented, requires physical device" in the presentation.

## Testing Guidance

### Approach A Testing (Native Share Extension)

1. **Build development client:** `npx expo run:ios` (requires Xcode)
2. **Open Safari** on the simulator, navigate to a YouTube Shorts URL
3. **Tap Share** and look for "Sendit" in the share sheet
4. **Select Sendit** and verify the board picker appears
5. **Select a board** and tap "Send"
6. **Open Sendit app** and verify the reel appears on the selected board

### Approach B Testing (Deep Link)

1. **Open Safari** on the simulator
2. **Navigate to:** `sendit://share?url=https%3A%2F%2Fyoutube.com%2Fshorts%2Fabc123`
3. **Verify** the Sendit app opens with the ShareToBoard modal showing the URL
4. **Select a board** and submit

### Both Approaches

- [ ] URL is correctly parsed from share intent / deep link
- [ ] Board picker shows all user's boards
- [ ] Single board auto-selected
- [ ] Reel created in Supabase with correct board_id, url, platform
- [ ] Extraction triggered after reel creation
- [ ] Duplicate URL shows error, no duplicate row
- [ ] Dismiss button closes the modal without side effects
- [ ] Success state shows checkmark and auto-dismisses

## Definition of Done

- [ ] Share sheet integration attempted via expo-share-intent (Approach A)
- [ ] If Approach A succeeds: Sendit appears in native share sheet on iOS and Android
- [ ] If Approach A fails: Deep link fallback (Approach B) implemented and working
- [ ] `ShareToBoard` component created with board picker, URL preview, submit flow
- [ ] Board list fetched and displayed in the picker
- [ ] Single-board users get auto-selection (no picker needed)
- [ ] Reel created in Supabase with correct data
- [ ] Extraction invoked after reel creation
- [ ] Duplicate URL handled with user-friendly error
- [ ] Share intent / deep link handler integrated into root layout
- [ ] URL scheme `sendit://` registered in app config
- [ ] Success confirmation shown after sharing
- [ ] Fallback approach documented if primary approach not viable
- [ ] Tested on at least one platform (iOS or Android)
