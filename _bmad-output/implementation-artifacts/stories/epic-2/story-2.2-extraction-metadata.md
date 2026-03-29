# Story 2.2: AI Extraction Edge Function — Metadata

## Description

As the system,
I want to extract metadata from a video URL and produce structured data via Claude AI,
So that every shared reel becomes a rich, queryable extraction card.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B (backend/Edge Functions)
- **FRs Covered:** FR15, FR18
- **Depends On:** Supabase project configured with secrets (`CLAUDE_API_KEY`, `YOUTUBE_API_KEY`)

## Acceptance Criteria

**Given** a URL is submitted to the `extract` Edge Function via `POST /functions/v1/extract`
**When** the URL is a YouTube Shorts or YouTube watch URL
**Then** the YouTube Data API v3 is called with the video ID to fetch snippet (title, description, tags, channelTitle, thumbnails) and contentDetails (duration)
**And** the raw metadata is sent to Claude API with a structured extraction prompt
**And** Claude returns a JSON object matching the `extraction_data` schema
**And** the `reels` row is updated with the `extraction_data` jsonb
**And** the response is returned to the calling client

**Given** a URL is submitted and the platform is Instagram or TikTok
**When** the Edge Function processes it
**Then** the function attempts to fetch the page HTML and extract Open Graph metadata (og:title, og:description, og:image)
**And** the OG metadata is sent to Claude for structured extraction
**And** Claude returns best-effort extraction (some fields may be null)

**Given** a URL is submitted and the platform is `other`
**When** the Edge Function processes it
**Then** Open Graph metadata is fetched from the page
**And** Claude attempts extraction from whatever metadata is available

**Given** the YouTube Data API returns an error or the URL is invalid
**When** the API call fails
**Then** the Edge Function returns `{ error: string, fallback: true }` with HTTP 200
**And** the reel row is updated with `extraction_data: { error: "extraction_failed", raw_url: url }`

**Given** the same URL has already been extracted (reel row has `extraction_data` that is not null and not an error)
**When** the Edge Function is called
**Then** the cached `extraction_data` is returned immediately without calling any external API

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK -> boards(id),
  added_by uuid FK -> members(id),
  url text NOT NULL,
  platform text NOT NULL,
  extraction_data jsonb,       -- THIS IS WHAT WE POPULATE
  classification text,
  created_at timestamptz,
  UNIQUE(board_id, url)
)
```

### extraction_data Target Structure

```json
{
  "type": null,
  "venue_name": "Peckham Audio",
  "location": "Peckham, London",
  "price": "£12",
  "date": "2026-04-05",
  "vibe": "underground, warehouse",
  "activity": "club night",
  "mood": "high energy",
  "hashtags": ["#warehouse", "#techno", "#londonnights"],
  "booking_url": "https://ra.co/events/...",
  "transcript_summary": null,
  "creator": "@londonclubscene",
  "title": "Best club night in South London rn",
  "thumbnail_url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
  "platform_metadata": {
    "channel": "London Club Scene",
    "duration": "PT58S",
    "view_count": "45000"
  }
}
```

Note: `type` is null here because classification happens in Story 2.4. `transcript_summary` is null here because transcript extraction happens in Story 2.3.

### Architecture References

- **Edge Function location:** `supabase/functions/extract/index.ts`
- **Supabase project:** `https://ubhbeqnagxbuoikzftht.supabase.co`
- **Secrets required:** `CLAUDE_API_KEY`, `YOUTUBE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (auto-available in Edge Functions)
- **Client calling pattern:** `supabase.functions.invoke('extract', { body: { url, reel_id } })`

### Dependencies

- Supabase project must be provisioned with Edge Functions enabled
- `CLAUDE_API_KEY` must be set as a Supabase secret: `supabase secrets set CLAUDE_API_KEY=sk-ant-...`
- `YOUTUBE_API_KEY` must be set as a Supabase secret: `supabase secrets set YOUTUBE_API_KEY=AIza...`
- The `reels` table must be deployed

## Implementation Notes

### 1. Edge Function Entry Point

**File:** `supabase/functions/extract/index.ts`

```typescript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req: Request) => {
  // CORS headers for client calls
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    });
  }

  try {
    const { url, reel_id } = await req.json();

    if (!url || !reel_id) {
      return new Response(JSON.stringify({ error: 'url and reel_id are required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Initialize Supabase admin client (for updating reel row)
    const supabaseAdmin = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );

    // Check cache — if reel already has extraction_data, return it
    const { data: existingReel } = await supabaseAdmin
      .from('reels')
      .select('extraction_data')
      .eq('id', reel_id)
      .single();

    if (existingReel?.extraction_data && !existingReel.extraction_data.error) {
      return new Response(JSON.stringify(existingReel.extraction_data), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Detect platform and fetch metadata
    const platform = detectPlatform(url);
    const rawMetadata = await fetchMetadata(platform, url);

    // Call Claude for structured extraction
    const extractionData = await extractWithClaude(rawMetadata, url, platform);

    // Update reel row with extraction_data
    await supabaseAdmin
      .from('reels')
      .update({ extraction_data: extractionData })
      .eq('id', reel_id);

    return new Response(JSON.stringify(extractionData), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('Extraction error:', err);
    return new Response(JSON.stringify({ error: err.message, fallback: true }), {
      status: 200, // Return 200 so client doesn't crash — fallback flag indicates failure
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
```

### 2. Platform Detection (Server-Side)

Duplicate the platform detection logic server-side (Edge Functions run in Deno, not React Native):

```typescript
type Platform = 'youtube' | 'instagram' | 'tiktok' | 'x' | 'other';

function detectPlatform(url: string): Platform {
  if (/youtube\.com\/shorts\/|youtu\.be\/|youtube\.com\/watch/.test(url)) return 'youtube';
  if (/instagram\.com\/(reel|p)\//.test(url)) return 'instagram';
  if (/tiktok\.com\/@.*\/video\/|vm\.tiktok\.com\//.test(url)) return 'tiktok';
  if (/x\.com\/.*\/status\/|twitter\.com\/.*\/status\//.test(url)) return 'x';
  return 'other';
}
```

### 3. YouTube Metadata Fetching

```typescript
async function fetchYouTubeMetadata(url: string) {
  const videoId = extractYouTubeVideoId(url);
  if (!videoId) throw new Error('Could not extract YouTube video ID');

  const apiKey = Deno.env.get('YOUTUBE_API_KEY');
  const apiUrl = `https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id=${videoId}&key=${apiKey}`;

  const response = await fetch(apiUrl);
  if (!response.ok) {
    throw new Error(`YouTube API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  if (!data.items || data.items.length === 0) {
    throw new Error('Video not found on YouTube');
  }

  const video = data.items[0];
  return {
    title: video.snippet.title,
    description: video.snippet.description,
    tags: video.snippet.tags || [],
    channel: video.snippet.channelTitle,
    published_at: video.snippet.publishedAt,
    thumbnail_url: video.snippet.thumbnails?.high?.url || video.snippet.thumbnails?.default?.url,
    duration: video.contentDetails.duration,
    view_count: video.statistics?.viewCount,
  };
}

function extractYouTubeVideoId(url: string): string | null {
  // Handle youtube.com/shorts/VIDEO_ID
  const shortsMatch = url.match(/youtube\.com\/shorts\/([a-zA-Z0-9_-]+)/);
  if (shortsMatch) return shortsMatch[1];

  // Handle youtu.be/VIDEO_ID
  const shortUrlMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
  if (shortUrlMatch) return shortUrlMatch[1];

  // Handle youtube.com/watch?v=VIDEO_ID
  const watchMatch = url.match(/youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/);
  if (watchMatch) return watchMatch[1];

  return null;
}
```

### 4. Open Graph Metadata Fetching (Instagram, TikTok, X, Other)

```typescript
async function fetchOpenGraphMetadata(url: string) {
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; Sendit/1.0; +https://sendit.app)',
      },
      redirect: 'follow',
    });

    const html = await response.text();

    const ogTitle = html.match(/<meta\s+property="og:title"\s+content="([^"]*)"/)
      ?.[1] || null;
    const ogDescription = html.match(/<meta\s+property="og:description"\s+content="([^"]*)"/)
      ?.[1] || null;
    const ogImage = html.match(/<meta\s+property="og:image"\s+content="([^"]*)"/)
      ?.[1] || null;
    const ogUrl = html.match(/<meta\s+property="og:url"\s+content="([^"]*)"/)
      ?.[1] || null;

    // Try to extract creator handle from URL or page
    const creator = extractCreatorFromUrl(url);

    return {
      title: ogTitle,
      description: ogDescription,
      thumbnail_url: ogImage,
      canonical_url: ogUrl,
      creator,
    };
  } catch {
    return { title: null, description: null, thumbnail_url: null, canonical_url: null, creator: null };
  }
}

function extractCreatorFromUrl(url: string): string | null {
  // Instagram: instagram.com/reel/... -> try to get from page
  // TikTok: tiktok.com/@username/video/... -> extract @username
  const tiktokMatch = url.match(/tiktok\.com\/@([^/]+)/);
  if (tiktokMatch) return `@${tiktokMatch[1]}`;

  // X/Twitter: x.com/username/status/... -> extract username
  const xMatch = url.match(/(?:x\.com|twitter\.com)\/([^/]+)\/status/);
  if (xMatch) return `@${xMatch[1]}`;

  return null;
}
```

### 5. Metadata Router

```typescript
async function fetchMetadata(platform: Platform, url: string) {
  switch (platform) {
    case 'youtube':
      return { platform, ...(await fetchYouTubeMetadata(url)) };
    case 'instagram':
    case 'tiktok':
    case 'x':
    case 'other':
      return { platform, ...(await fetchOpenGraphMetadata(url)) };
  }
}
```

### 6. Claude API Structured Extraction

This is the core AI call. The prompt must produce consistent JSON output.

```typescript
async function extractWithClaude(
  rawMetadata: Record<string, unknown>,
  url: string,
  platform: Platform
) {
  const claudeApiKey = Deno.env.get('CLAUDE_API_KEY');

  const systemPrompt = `You are a content extraction engine for Sendit, an app that turns shared social media content into structured data about real-world activities, venues, and events.

Your job: Given raw metadata from a social media video, extract structured information that helps a friend group decide what to do together.

IMPORTANT RULES:
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
- If a field cannot be determined from the metadata, set it to null.
- For prices, include the currency symbol (e.g., "£12", "$25", "€15").
- For dates, use ISO 8601 format (YYYY-MM-DD). If only a day of week is mentioned, estimate the next occurrence.
- For location, be as specific as possible (neighbourhood + city).
- For vibe, use 2-4 comma-separated descriptive words.
- For hashtags, include the # prefix.
- For booking_url, only include if a real booking/ticket link is mentioned or can be inferred.
- The "creator" field should be the @handle of the content creator.`;

  const userPrompt = `Extract structured data from this ${platform} video.

URL: ${url}

Raw metadata:
${JSON.stringify(rawMetadata, null, 2)}

Return a JSON object with exactly these fields:
{
  "venue_name": string | null,
  "location": string | null,
  "price": string | null,
  "date": string | null,
  "vibe": string | null,
  "activity": string | null,
  "mood": string | null,
  "hashtags": string[] | null,
  "booking_url": string | null,
  "transcript_summary": null,
  "creator": string | null,
  "title": string | null,
  "thumbnail_url": string | null,
  "platform_metadata": object | null
}`;

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': claudeApiKey!,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      system: systemPrompt,
      messages: [
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Claude API error: ${response.status} — ${errorBody}`);
  }

  const result = await response.json();
  const content = result.content[0]?.text;

  if (!content) {
    throw new Error('Claude returned empty response');
  }

  // Parse Claude's JSON response
  try {
    const parsed = JSON.parse(content);
    // Merge in thumbnail_url from raw metadata if Claude didn't set it
    if (!parsed.thumbnail_url && rawMetadata.thumbnail_url) {
      parsed.thumbnail_url = rawMetadata.thumbnail_url;
    }
    // Merge platform metadata
    if (!parsed.platform_metadata) {
      parsed.platform_metadata = {
        channel: rawMetadata.channel || null,
        duration: rawMetadata.duration || null,
        view_count: rawMetadata.view_count || null,
      };
    }
    return parsed;
  } catch {
    throw new Error(`Claude returned invalid JSON: ${content.substring(0, 200)}`);
  }
}
```

### 7. Retry Logic (NFR13)

Wrap the Claude API call with a single retry on transient failures:

```typescript
async function callWithRetry<T>(fn: () => Promise<T>, retries = 1): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (retries > 0 && isTransientError(err)) {
      const delay = 1000 * (2 - retries); // Exponential backoff: 1s
      await new Promise((resolve) => setTimeout(resolve, delay));
      return callWithRetry(fn, retries - 1);
    }
    throw err;
  }
}

function isTransientError(err: unknown): boolean {
  if (err instanceof Error) {
    return err.message.includes('429') || err.message.includes('503') || err.message.includes('timeout');
  }
  return false;
}
```

### 8. Deployment

Deploy via Supabase CLI:

```bash
supabase functions deploy extract --project-ref ubhbeqnagxbuoikzftht
```

Set secrets (if not already):

```bash
supabase secrets set CLAUDE_API_KEY=sk-ant-api03-... --project-ref ubhbeqnagxbuoikzftht
supabase secrets set YOUTUBE_API_KEY=AIza... --project-ref ubhbeqnagxbuoikzftht
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/extract/index.ts` | Main Edge Function — URL intake, platform routing, metadata fetch, Claude extraction, reel update |

### No Modifications Required

This is a self-contained Edge Function. The client-side caller (`lib/ai/extraction.ts`) is created in Story 2.1.

## Testing Guidance

### Local Testing with Supabase CLI

```bash
# Start Edge Functions locally
supabase functions serve extract --env-file .env.local

# Test with curl
curl -X POST http://localhost:54321/functions/v1/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"url": "https://youtube.com/shorts/abc123", "reel_id": "some-uuid"}'
```

### Test Cases

- YouTube Shorts URL: returns structured extraction with `venue_name`, `activity`, etc. from video metadata
- YouTube watch URL: same as above
- Instagram reel URL: returns best-effort extraction from OG metadata
- TikTok URL: returns best-effort extraction from OG metadata
- Invalid URL: returns error response with `fallback: true`
- Already-extracted reel: returns cached `extraction_data` without calling any API
- YouTube API failure: returns graceful error, reel updated with error extraction_data
- Claude API failure: retries once, then returns error

### Verification Queries

After extraction, verify in Supabase SQL editor:

```sql
SELECT id, url, platform, extraction_data
FROM reels
WHERE extraction_data IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;
```

## Definition of Done

- [ ] `supabase/functions/extract/index.ts` created and deployable
- [ ] Edge Function accepts `{ url, reel_id }` and returns structured extraction JSON
- [ ] YouTube Data API v3 integration works for Shorts and watch URLs
- [ ] Open Graph fallback works for Instagram, TikTok, X, and unknown URLs
- [ ] Claude API produces structured `extraction_data` matching the target schema
- [ ] Retry logic (1 retry with exponential backoff) implemented for Claude API calls
- [ ] Caching: already-extracted reels return cached data without API calls
- [ ] Error handling: API failures return `{ error, fallback: true }` with HTTP 200
- [ ] Reel row is updated with `extraction_data` after successful extraction
- [ ] Edge Function deployed to `https://ubhbeqnagxbuoikzftht.supabase.co/functions/v1/extract`
- [ ] Secrets configured: `CLAUDE_API_KEY`, `YOUTUBE_API_KEY`
- [ ] Tested with at least 3 different YouTube Shorts URLs and 1 Instagram reel URL
- [ ] Extraction completes within 3 seconds for YouTube URLs (NFR1)
