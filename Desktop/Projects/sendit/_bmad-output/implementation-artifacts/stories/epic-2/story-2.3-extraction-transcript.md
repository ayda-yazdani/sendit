# Story 2.3: AI Extraction — Transcript & Vision Analysis

## Description

As the system,
I want to process video transcripts and analyse video thumbnails with vision AI,
So that extraction captures what is actually said and shown in the video, not just metadata.

## Status

- **Epic:** Epic 2 — Content Sharing & AI Extraction
- **Priority:** P0
- **Branch:** `feature/supabase-edge-functions`
- **Assignee:** Person B (backend — transcript/vision) + Person C (prompt engineering)
- **FRs Covered:** FR13, FR14
- **Depends On:** Story 2.2 (extract Edge Function exists and works for metadata)

## Acceptance Criteria

**Given** a YouTube Shorts URL is submitted to the `extract` Edge Function
**When** the video has auto-generated or manual captions available
**Then** the transcript text is fetched via the YouTube captions endpoint or the `youtube-transcript` npm approach
**And** the transcript is included in the Claude API prompt alongside metadata
**And** `extraction_data.transcript_summary` contains a 1-2 sentence summary of what was said

**Given** a YouTube Shorts URL is submitted to the `extract` Edge Function
**When** the video has a thumbnail available
**Then** the thumbnail image URL is sent to Claude's vision API (multi-modal message)
**And** Claude describes any on-screen text overlays, location names, prices, or dates visible in the thumbnail
**And** this visual context is included in the extraction prompt for richer results

**Given** a YouTube video has no captions available
**When** the transcript fetch fails
**Then** extraction proceeds without transcript data (graceful degradation)
**And** `extraction_data.transcript_summary` is set to `null`
**And** extraction still completes using metadata + vision analysis only

**Given** a non-YouTube URL (Instagram, TikTok)
**When** the Edge Function processes it
**Then** transcript extraction is skipped (platform does not expose captions API)
**And** vision analysis is still attempted if a thumbnail URL is available from OG metadata
**And** extraction completes with whatever data is available

**Given** all extraction layers complete
**When** the final Claude prompt is constructed
**Then** it includes: (1) raw metadata, (2) transcript text if available, (3) vision description of thumbnail if available
**And** the overall extraction completes within 3 seconds (NFR1)

## Technical Context

### Relevant Schema

```sql
reels.extraction_data jsonb — specifically the fields:
  "transcript_summary": "Creator recommends Peckham Audio as the best warehouse venue...",
  "visual_context": "On-screen text: 'BEST CLUB IN SOUTH LONDON', price overlay: '£12 entry'"
```

### Architecture References

- **Edge Function:** `supabase/functions/extract/index.ts` — enhance the existing function from Story 2.2
- **YouTube captions:** No official REST API for captions without OAuth. Use the `youtube-transcript` approach: fetch the video page HTML and parse the `timedtext` track URL, or use the unofficial transcript endpoint.
- **Claude vision:** The Anthropic Messages API supports `image` content blocks with `type: "image"` and `source: { type: "url", url: "..." }` (or base64). Use the thumbnail URL directly.

### Dependencies

- Story 2.2 must be complete — the `extract` Edge Function must exist with metadata extraction working
- `CLAUDE_API_KEY` must support Claude models with vision capabilities (claude-sonnet-4-20250514 supports vision)
- YouTube videos must have a thumbnail URL in the API response (virtually all do)

## Implementation Notes

### 1. YouTube Transcript Fetching

YouTube does not expose a public REST API for captions. The standard workaround is to fetch the video page and extract the transcript data from the `playerCaptionsTracklistRenderer` in the initial page data.

Add this function to the `extract` Edge Function:

```typescript
async function fetchYouTubeTranscript(videoId: string): Promise<string | null> {
  try {
    // Fetch the YouTube watch page
    const pageUrl = `https://www.youtube.com/watch?v=${videoId}`;
    const response = await fetch(pageUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });

    const html = await response.text();

    // Extract captions track URL from the page data
    const captionTrackMatch = html.match(/"captionTracks":\[(\{.*?\})\]/);
    if (!captionTrackMatch) {
      console.log('No caption tracks found for video:', videoId);
      return null;
    }

    // Parse the first caption track (usually auto-generated English)
    const trackData = JSON.parse(`[${captionTrackMatch[1]}]`);
    const englishTrack = trackData.find(
      (t: { languageCode: string }) =>
        t.languageCode === 'en' || t.languageCode?.startsWith('en')
    ) || trackData[0];

    if (!englishTrack?.baseUrl) {
      return null;
    }

    // Fetch the actual transcript XML
    const transcriptResponse = await fetch(englishTrack.baseUrl);
    const transcriptXml = await transcriptResponse.text();

    // Parse XML to extract text segments
    const textSegments: string[] = [];
    const textMatches = transcriptXml.matchAll(/<text[^>]*>(.*?)<\/text>/gs);
    for (const match of textMatches) {
      const decoded = match[1]
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&#39;/g, "'")
        .replace(/&quot;/g, '"')
        .replace(/\n/g, ' ')
        .trim();
      if (decoded) textSegments.push(decoded);
    }

    const fullTranscript = textSegments.join(' ');

    // Truncate to ~1500 chars to stay within prompt limits
    if (fullTranscript.length > 1500) {
      return fullTranscript.substring(0, 1500) + '...';
    }

    return fullTranscript || null;
  } catch (err) {
    console.warn('Transcript fetch failed:', err);
    return null;
  }
}
```

### 2. Vision Analysis via Claude

Send the video thumbnail to Claude's vision API to describe on-screen text. This uses the multi-modal message format.

```typescript
async function analyseImageWithClaude(imageUrl: string): Promise<string | null> {
  if (!imageUrl) return null;

  const claudeApiKey = Deno.env.get('CLAUDE_API_KEY');

  try {
    // First, fetch the image and convert to base64 (more reliable than URL for thumbnails)
    const imageResponse = await fetch(imageUrl);
    if (!imageResponse.ok) return null;

    const imageBuffer = await imageResponse.arrayBuffer();
    const base64Image = btoa(
      String.fromCharCode(...new Uint8Array(imageBuffer))
    );

    const contentType = imageResponse.headers.get('content-type') || 'image/jpeg';

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': claudeApiKey!,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 300,
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'image',
                source: {
                  type: 'base64',
                  media_type: contentType,
                  data: base64Image,
                },
              },
              {
                type: 'text',
                text: `Describe any on-screen text overlays, venue names, prices, dates, locations, or event details visible in this video thumbnail. Be concise and factual. If there is no relevant text or information visible, respond with "No relevant text visible." Do not describe the visual aesthetics or people — only text and factual details.`,
              },
            ],
          },
        ],
      }),
    });

    if (!response.ok) {
      console.warn('Vision analysis failed:', response.status);
      return null;
    }

    const result = await response.json();
    const description = result.content[0]?.text;

    if (description?.includes('No relevant text visible')) {
      return null;
    }

    return description || null;
  } catch (err) {
    console.warn('Vision analysis error:', err);
    return null;
  }
}
```

### 3. Enhanced Extraction Prompt

Update the main `extractWithClaude` function from Story 2.2 to accept transcript and vision context:

```typescript
async function extractWithClaude(
  rawMetadata: Record<string, unknown>,
  url: string,
  platform: string,
  transcript: string | null,
  visionDescription: string | null
) {
  const claudeApiKey = Deno.env.get('CLAUDE_API_KEY');

  const systemPrompt = `You are a content extraction engine for Sendit, an app that turns shared social media content into structured data about real-world activities, venues, and events.

Your job: Given raw metadata, transcript, and visual context from a social media video, extract structured information that helps a friend group decide what to do together.

You have up to THREE sources of information:
1. RAW METADATA — title, description, tags from the platform API
2. TRANSCRIPT — what the creator actually says in the video (may be null)
3. VISUAL CONTEXT — text overlays and details visible in the video thumbnail (may be null)

PRIORITISE information from the transcript and visual context over metadata, as creators often mention specific details verbally or in text overlays that don't appear in the title/description.

IMPORTANT RULES:
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
- If a field cannot be determined from ANY source, set it to null.
- For prices, include the currency symbol (e.g., "£12", "$25", "€15").
- For dates, use ISO 8601 format (YYYY-MM-DD). If only a day of week is mentioned, estimate the next occurrence from today (2026-03-28).
- For location, be as specific as possible (neighbourhood + city).
- For vibe, use 2-4 comma-separated descriptive words.
- For hashtags, include the # prefix.
- For booking_url, only include if a real booking/ticket link is explicitly mentioned.
- For transcript_summary, write 1-2 sentences summarising the key points the creator makes. If no transcript, set to null.
- The "creator" field should be the @handle of the content creator.`;

  let userPrompt = `Extract structured data from this ${platform} video.

URL: ${url}

=== RAW METADATA ===
${JSON.stringify(rawMetadata, null, 2)}`;

  if (transcript) {
    userPrompt += `

=== TRANSCRIPT (what the creator says) ===
${transcript}`;
  }

  if (visionDescription) {
    userPrompt += `

=== VISUAL CONTEXT (on-screen text from thumbnail) ===
${visionDescription}`;
  }

  userPrompt += `

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
  "transcript_summary": string | null,
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

  const parsed = JSON.parse(content);

  // Ensure thumbnail_url is populated from metadata if Claude didn't include it
  if (!parsed.thumbnail_url && rawMetadata.thumbnail_url) {
    parsed.thumbnail_url = rawMetadata.thumbnail_url as string;
  }

  // Ensure platform_metadata is populated
  if (!parsed.platform_metadata) {
    parsed.platform_metadata = {
      channel: rawMetadata.channel || null,
      duration: rawMetadata.duration || null,
      view_count: rawMetadata.view_count || null,
    };
  }

  return parsed;
}
```

### 4. Updated Main Flow in extract/index.ts

Update the main handler to orchestrate all three extraction layers:

```typescript
// Inside the main serve handler, replace the simple metadata -> Claude flow with:

// 1. Fetch platform metadata (from Story 2.2)
const rawMetadata = await fetchMetadata(platform, url);

// 2. Fetch transcript (YouTube only)
let transcript: string | null = null;
if (platform === 'youtube') {
  const videoId = extractYouTubeVideoId(url);
  if (videoId) {
    transcript = await fetchYouTubeTranscript(videoId);
  }
}

// 3. Vision analysis of thumbnail (any platform with thumbnail)
const thumbnailUrl = rawMetadata.thumbnail_url as string | null;
let visionDescription: string | null = null;
if (thumbnailUrl) {
  visionDescription = await analyseImageWithClaude(thumbnailUrl);
}

// 4. Combined Claude extraction with all three layers
const extractionData = await callWithRetry(() =>
  extractWithClaude(rawMetadata, url, platform, transcript, visionDescription)
);

// 5. Add visual_context to extraction data for traceability
if (visionDescription) {
  extractionData.visual_context = visionDescription;
}
```

### 5. Parallel Fetching for Performance (NFR1)

To stay within the 3-second target, run transcript fetch and vision analysis in parallel where possible:

```typescript
// Parallel execution
const [transcript, visionDescription] = await Promise.all([
  platform === 'youtube' && videoId
    ? fetchYouTubeTranscript(videoId)
    : Promise.resolve(null),
  thumbnailUrl
    ? analyseImageWithClaude(thumbnailUrl)
    : Promise.resolve(null),
]);
```

Note: The vision analysis call goes to Claude API, so this adds latency. If the 3-second budget is tight, the vision analysis can be made optional (skip it if metadata + transcript already provide rich data). Add a performance flag:

```typescript
const ENABLE_VISION_ANALYSIS = true; // Toggle for performance tuning
```

### 6. Latency Budget

Target: 3 seconds total (NFR1).

| Step | Estimated Latency |
|------|-------------------|
| YouTube Data API v3 | ~300ms |
| Transcript fetch (page parse) | ~500ms |
| Vision analysis (Claude) | ~1000ms |
| Main extraction (Claude) | ~1200ms |
| Supabase update | ~100ms |
| **Total (sequential)** | **~3100ms** |
| **Total (parallel transcript + vision)** | **~2100ms** |

Parallel execution is critical. If latency is still too high, drop vision analysis for the hackathon demo and rely on transcript + metadata only.

## Files to Create/Modify

### Modify

| File | Change |
|------|--------|
| `supabase/functions/extract/index.ts` | Add `fetchYouTubeTranscript()`, `analyseImageWithClaude()`, update `extractWithClaude()` to accept transcript and vision context, parallelise fetching |

### No New Files

All changes are enhancements to the existing Edge Function from Story 2.2.

## Testing Guidance

### Test Cases

1. **YouTube Shorts with captions:** Submit a popular YouTube Shorts URL that has auto-generated captions. Verify `transcript_summary` is populated in extraction_data.

2. **YouTube Shorts without captions:** Submit a YouTube Shorts URL for a music-only video with no speech. Verify extraction still completes, `transcript_summary` is null.

3. **YouTube Shorts with on-screen text:** Submit a YouTube Shorts URL where the thumbnail has text overlays (price, venue name). Verify `visual_context` captures the text.

4. **Instagram reel:** Submit an Instagram reel URL. Verify transcript is null (skipped), vision analysis attempted on OG image thumbnail.

5. **TikTok URL:** Same as Instagram — transcript skipped, vision attempted.

6. **Performance test:** Time the extraction from request to response. Must be under 3 seconds for YouTube URLs.

### Verification

```sql
-- Check that transcript_summary is populated
SELECT id, url,
  extraction_data->>'transcript_summary' as transcript,
  extraction_data->>'visual_context' as vision
FROM reels
WHERE platform = 'youtube'
ORDER BY created_at DESC
LIMIT 5;
```

### Local Testing

```bash
supabase functions serve extract --env-file .env.local

# Test with a real YouTube Shorts URL
curl -X POST http://localhost:54321/functions/v1/extract \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"url": "https://youtube.com/shorts/REAL_VIDEO_ID", "reel_id": "test-uuid"}'
```

## Definition of Done

- [ ] `fetchYouTubeTranscript()` function added to extract Edge Function
- [ ] Transcript parsing extracts text segments from YouTube caption tracks
- [ ] `analyseImageWithClaude()` function sends thumbnail to Claude vision API
- [ ] Vision analysis extracts on-screen text, prices, venue names from thumbnails
- [ ] Claude extraction prompt updated to include transcript and vision context as separate sections
- [ ] Transcript and vision analysis run in parallel for performance
- [ ] Graceful degradation: extraction works with any combination of metadata/transcript/vision (all nullable)
- [ ] `extraction_data.transcript_summary` populated for YouTube videos with captions
- [ ] `extraction_data.visual_context` populated when relevant text is detected in thumbnails
- [ ] Extraction for YouTube Shorts completes within 3 seconds (NFR1)
- [ ] Edge Function re-deployed with enhanced extraction
- [ ] Tested with at least 3 YouTube Shorts URLs: one with captions, one without, one with visible text overlays
