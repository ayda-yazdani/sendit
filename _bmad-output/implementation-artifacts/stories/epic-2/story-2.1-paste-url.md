# Story 2.1: Paste URL & Platform Detection

## Description

As a board member,
I want to paste a URL into the board and have the platform auto-detected,
So that I can share content without worrying about format.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/ai-extraction`
- **Assignee:** Person C (client/UI/prompts)
- **FRs Covered:** FR10, FR11, FR12 (partial)
- **Depends On:** Epic 1 complete (boards, members, Supabase client, device auth)

## Acceptance Criteria

**Given** the user is on a board detail screen (`app/(tabs)/board/[id].tsx`)
**When** they paste a URL into the text input field and tap "Send"
**Then** the system detects the platform from the URL pattern using regex matching
**And** a new row is inserted into the `reels` table with `url`, `platform`, `board_id`, and `added_by`
**And** the extract Edge Function is invoked with the URL
**And** a loading indicator is shown while extraction is in progress
**And** the extraction card appears when the Edge Function responds

**Given** the user submits a URL that already exists for this board
**When** the `UNIQUE(board_id, url)` constraint is violated
**Then** the user sees an inline error: "This link has already been shared on this board"
**And** the existing reel's extraction card is scrolled into view

**Given** the user submits text that is not a valid URL
**When** the input is validated before submission
**Then** the user sees an inline error: "Please paste a valid URL"
**And** no Supabase insert or Edge Function call is made

**Given** the user submits a URL from an unsupported platform
**When** no regex pattern matches
**Then** the platform is set to `"other"`
**And** extraction still proceeds (Edge Function handles graceful degradation)

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK DEFAULT gen_random_uuid(),
  board_id uuid FK -> boards(id),
  added_by uuid FK -> members(id),
  url text NOT NULL,
  platform text NOT NULL,
  extraction_data jsonb,
  classification text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(board_id, url)
)
```

### Architecture References

- **Supabase client:** `lib/supabase.ts` — already initialized with `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- **Board detail screen:** `app/(tabs)/board/[id].tsx` — this is where the URL input lives
- **Extraction service:** `lib/ai/extraction.ts` — client-side wrapper for calling the `extract` Edge Function
- **Auth store:** `lib/stores/auth-store.ts` — provides current `member_id` for `added_by` field
- **Board store:** `lib/stores/board-store.ts` — provides current `board_id`

### Dependencies

- Epic 1 must be complete: boards table, members table, Supabase client, auth store with device session
- The `reels` table must be deployed in Supabase (part of initial schema migration)
- The `extract` Edge Function does NOT need to be deployed yet — this story handles the client-side flow and can stub the extraction call initially

## Implementation Notes

### 1. Platform Detection Utility

Create a pure utility function for platform detection. This must be deterministic and have no side effects.

**File:** `lib/utils/platform-detect.ts`

```typescript
export type Platform = 'youtube' | 'instagram' | 'tiktok' | 'x' | 'other';

const PLATFORM_PATTERNS: Record<Exclude<Platform, 'other'>, RegExp> = {
  youtube: /youtube\.com\/shorts\/|youtu\.be\/|youtube\.com\/watch/,
  instagram: /instagram\.com\/(reel|p)\//,
  tiktok: /tiktok\.com\/@.*\/video\/|vm\.tiktok\.com\//,
  x: /x\.com\/.*\/status\/|twitter\.com\/.*\/status\//,
};

export function detectPlatform(url: string): Platform {
  for (const [platform, pattern] of Object.entries(PLATFORM_PATTERNS)) {
    if (pattern.test(url)) {
      return platform as Platform;
    }
  }
  return 'other';
}

export function isValidUrl(text: string): boolean {
  try {
    const url = new URL(text);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}
```

### 2. URL Input Component

Create a dedicated component for the paste URL input bar. It should sit at the bottom of the board detail screen, similar to a chat input.

**File:** `components/board/UrlInput.tsx`

Key implementation details:
- `TextInput` with `autoCapitalize="none"`, `autoCorrect={false}`, `keyboardType="url"`, `placeholder="Paste a link..."`
- Submit button (arrow icon) to the right of the input, disabled when input is empty
- Inline error text below the input for validation failures
- Loading state: replace the submit button with `ActivityIndicator` while extraction is running
- Clear the input after successful submission
- Use `Keyboard.dismiss()` after submission

### 3. Reel Creation Flow

The submission flow in the board detail screen:

```typescript
// In the board detail screen or a custom hook
import { detectPlatform, isValidUrl } from '@/lib/utils/platform-detect';
import { invokeExtraction } from '@/lib/ai/extraction';

async function handleSubmitUrl(url: string, boardId: string, memberId: string) {
  // 1. Validate URL
  if (!isValidUrl(url)) {
    throw new Error('Please paste a valid URL');
  }

  // 2. Detect platform
  const platform = detectPlatform(url);

  // 3. Insert reel row into Supabase
  const { data: reel, error } = await supabase
    .from('reels')
    .insert({
      board_id: boardId,
      added_by: memberId,
      url: url.trim(),
      platform,
    })
    .select()
    .single();

  if (error) {
    if (error.code === '23505') {
      // Unique constraint violation
      throw new Error('This link has already been shared on this board');
    }
    throw new Error('Failed to share link. Please try again.');
  }

  // 4. Invoke extraction Edge Function (fire and forget — reel row exists,
  //    extraction_data will be updated asynchronously)
  invokeExtraction(reel.id, url).catch(console.error);

  return reel;
}
```

### 4. Extraction Service Stub

Create the extraction service wrapper that calls the Supabase Edge Function. For this story, the Edge Function may not be deployed yet — handle that gracefully.

**File:** `lib/ai/extraction.ts`

```typescript
import { supabase } from '@/lib/supabase';

export async function invokeExtraction(reelId: string, url: string) {
  try {
    const { data, error } = await supabase.functions.invoke('extract', {
      body: { url, reel_id: reelId },
    });

    if (error) {
      console.warn('Extraction failed, will retry:', error.message);
      return null;
    }

    // The Edge Function updates the reel row directly with extraction_data.
    // The client receives the update via Realtime subscription (Story 2.7).
    return data;
  } catch (err) {
    console.warn('Extraction service unavailable:', err);
    return null;
  }
}
```

### 5. Duplicate URL Handling

When a duplicate URL is detected (Postgres error code `23505`), query for the existing reel and scroll to it:

```typescript
const { data: existingReel } = await supabase
  .from('reels')
  .select('id')
  .eq('board_id', boardId)
  .eq('url', url.trim())
  .single();
```

### 6. Platform Icon Mapping

Create a utility for displaying the correct platform icon next to the input or on the reel card:

```typescript
// lib/utils/platform-icons.ts
export const PLATFORM_ICONS: Record<string, { name: string; color: string }> = {
  youtube: { name: 'logo-youtube', color: '#FF0000' },
  instagram: { name: 'logo-instagram', color: '#E4405F' },
  tiktok: { name: 'logo-tiktok', color: '#000000' },
  x: { name: 'logo-twitter', color: '#1DA1F2' },
  other: { name: 'link', color: '#666666' },
};
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `lib/utils/platform-detect.ts` | Platform detection regex + URL validation |
| `lib/utils/platform-icons.ts` | Platform icon/color mapping |
| `components/board/UrlInput.tsx` | URL paste input component with validation |
| `lib/ai/extraction.ts` | Client-side extraction service (Edge Function wrapper) |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Add `<UrlInput />` component at bottom of board detail screen |
| `lib/stores/board-store.ts` | Add `addReel` action and `reels` state for the active board |

## Testing Guidance

### Unit Tests (Jest)

- `platform-detect.test.ts`:
  - YouTube Shorts URL returns `'youtube'`
  - YouTube watch URL returns `'youtube'`
  - `youtu.be` short URL returns `'youtube'`
  - Instagram reel URL returns `'instagram'`
  - Instagram post URL returns `'instagram'`
  - TikTok video URL returns `'tiktok'`
  - TikTok short URL (`vm.tiktok.com`) returns `'tiktok'`
  - X/Twitter status URL returns `'x'`
  - Twitter legacy URL returns `'x'`
  - Random URL returns `'other'`
  - Empty string returns `'other'`
  - `isValidUrl` returns `false` for non-URL text
  - `isValidUrl` returns `false` for `ftp://` URLs
  - `isValidUrl` returns `true` for `https://` URLs

### Manual Testing Checklist

- [ ] Paste a YouTube Shorts URL — platform detected as `youtube`, reel row created
- [ ] Paste an Instagram reel URL — platform detected as `instagram`
- [ ] Paste a TikTok URL — platform detected as `tiktok`
- [ ] Paste a random blog URL — platform detected as `other`, extraction still triggered
- [ ] Paste the same URL twice — error message shown, no duplicate row
- [ ] Paste invalid text (e.g., "hello world") — validation error shown, no insert
- [ ] Submit with empty input — submit button is disabled
- [ ] Verify reel row appears in Supabase dashboard after submission
- [ ] Verify loading indicator shows during extraction call

## Definition of Done

- [ ] `lib/utils/platform-detect.ts` created with `detectPlatform()` and `isValidUrl()` functions
- [ ] `components/board/UrlInput.tsx` created with text input, submit button, loading state, and error display
- [ ] `lib/ai/extraction.ts` created with `invokeExtraction()` wrapper (graceful failure if Edge Function not deployed)
- [ ] Board detail screen renders `<UrlInput />` at the bottom of the screen
- [ ] Submitting a valid URL creates a `reels` row in Supabase with correct `board_id`, `added_by`, `url`, and `platform`
- [ ] Duplicate URL shows user-friendly error message
- [ ] Invalid URL shows validation error without making any API call
- [ ] Platform detection unit tests pass for all 5 platform types plus edge cases
- [ ] No TypeScript errors (`npx tsc --noEmit` passes)
- [ ] Component renders correctly on both iOS and Android simulators
