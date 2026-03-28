import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

type Platform = "youtube" | "instagram" | "tiktok" | "x" | "other";

function detectPlatform(url: string): Platform {
  if (/youtube\.com\/shorts\/|youtu\.be\/|youtube\.com\/watch/.test(url)) return "youtube";
  if (/instagram\.com\/(reel|p)\//.test(url)) return "instagram";
  if (/tiktok\.com\/@.*\/video\/|vm\.tiktok\.com\//.test(url)) return "tiktok";
  if (/x\.com\/.*\/status\/|twitter\.com\/.*\/status\//.test(url)) return "x";
  return "other";
}

function extractYouTubeVideoId(url: string): string | null {
  const shortsMatch = url.match(/youtube\.com\/shorts\/([a-zA-Z0-9_-]+)/);
  if (shortsMatch) return shortsMatch[1];
  const shortUrlMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
  if (shortUrlMatch) return shortUrlMatch[1];
  const watchMatch = url.match(/youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/);
  if (watchMatch) return watchMatch[1];
  return null;
}

async function fetchYouTubeMetadata(url: string) {
  const videoId = extractYouTubeVideoId(url);
  if (!videoId) throw new Error("Could not extract YouTube video ID");

  const apiKey = Deno.env.get("YOUTUBE_API_KEY");
  if (!apiKey) throw new Error("YOUTUBE_API_KEY not configured");

  const apiUrl = `https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id=${videoId}&key=${apiKey}`;
  const response = await fetch(apiUrl);
  if (!response.ok) throw new Error(`YouTube API error: ${response.status}`);

  const data = await response.json();
  if (!data.items?.length) throw new Error("Video not found on YouTube");

  const video = data.items[0];
  return {
    title: video.snippet.title,
    description: video.snippet.description,
    tags: video.snippet.tags || [],
    channel: video.snippet.channelTitle,
    published_at: video.snippet.publishedAt,
    thumbnail_url: video.snippet.thumbnails?.high?.url || video.snippet.thumbnails?.default?.url,
    duration: video.contentDetails?.duration,
    view_count: video.statistics?.viewCount,
  };
}

async function fetchOpenGraphMetadata(url: string) {
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; Sendit/1.0)" },
      redirect: "follow",
    });
    const html = await response.text();

    const getOg = (property: string): string | null => {
      const match = html.match(new RegExp(`<meta[^>]*property=["']og:${property}["'][^>]*content=["']([^"']+)["']`, "i"))
        || html.match(new RegExp(`<meta[^>]*content=["']([^"']+)["'][^>]*property=["']og:${property}["']`, "i"));
      return match ? match[1] : null;
    };

    return {
      title: getOg("title") || html.match(/<title[^>]*>([^<]+)<\/title>/i)?.[1] || null,
      description: getOg("description") || null,
      image: getOg("image") || null,
      site_name: getOg("site_name") || null,
    };
  } catch {
    return { title: null, description: null, image: null, site_name: null };
  }
}

const EXTRACTION_SYSTEM_PROMPT = `You are an AI extraction engine for Sendit, an app where friend groups share short-form video URLs. Your job is to extract structured metadata from video content.

Analyze the provided metadata and produce a JSON object with these fields:
- venue_name: string | null — specific venue, restaurant, bar, or place mentioned
- location: string | null — city, neighbourhood, or area mentioned
- price: string | null — ticket price, cost per person, or price range mentioned
- date: string | null — specific date of an event (ISO format YYYY-MM-DD if possible)
- vibe: string | null — 2-5 word description of the overall vibe/aesthetic
- activity: string | null — what type of activity (e.g., "club night", "dinner", "rooftop bar", "recipe", "comedy show")
- mood: string | null — emotional register (e.g., "high energy", "chill", "chaotic", "intimate")
- hashtags: string[] — relevant hashtags from the content
- booking_url: string | null — any booking or ticket link mentioned
- creator: string | null — the content creator's handle or channel name
- audio_track: string | null — name of the background song/audio if identifiable
- audio_artist: string | null — artist of the audio track if identifiable

Return ONLY valid JSON. No markdown, no explanation. Every field must be present (use null if unknown).`;

async function extractWithClaude(metadata: any, url: string, platform: Platform) {
  const apiKey = Deno.env.get("CLAUDE_API_KEY");
  if (!apiKey) throw new Error("CLAUDE_API_KEY not configured");

  const userPrompt = `Extract structured data from this ${platform} video URL.

URL: ${url}

METADATA:
${JSON.stringify(metadata, null, 2)}

Return the extraction as JSON with keys: venue_name, location, price, date, vibe, activity, mood, hashtags, booking_url, creator, audio_track, audio_artist.`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      temperature: 0.2,
      system: EXTRACTION_SYSTEM_PROMPT,
      messages: [{ role: "user", content: userPrompt }],
    }),
  });

  if (!response.ok) throw new Error(`Claude API error: ${response.status}`);

  const data = await response.json();
  const text = data.content[0].text;

  // Strip markdown fences if present
  const cleaned = text.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
  return JSON.parse(cleaned);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { url, reel_id } = await req.json();

    if (!url || !reel_id) {
      return new Response(
        JSON.stringify({ error: "url and reel_id are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabaseAdmin = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Check cache
    const { data: existingReel } = await supabaseAdmin
      .from("reels")
      .select("extraction_data")
      .eq("id", reel_id)
      .single();

    if (existingReel?.extraction_data && !existingReel.extraction_data.error) {
      return new Response(
        JSON.stringify(existingReel.extraction_data),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Detect platform and fetch metadata
    const platform = detectPlatform(url);
    let rawMetadata: any;

    if (platform === "youtube") {
      rawMetadata = await fetchYouTubeMetadata(url);
    } else {
      rawMetadata = await fetchOpenGraphMetadata(url);
    }

    // Add platform context
    rawMetadata.source_platform = platform;
    rawMetadata.source_url = url;

    // Extract with Claude
    let extractionData: any;
    try {
      extractionData = await extractWithClaude(rawMetadata, url, platform);
    } catch (claudeError) {
      // Retry once
      try {
        await new Promise((r) => setTimeout(r, 2000));
        extractionData = await extractWithClaude(rawMetadata, url, platform);
      } catch {
        extractionData = { error: "extraction_failed", raw_url: url };
      }
    }

    // Add metadata that Claude might miss
    if (rawMetadata.thumbnail_url) extractionData.thumbnail_url = rawMetadata.thumbnail_url;
    if (rawMetadata.title && !extractionData.title) extractionData.title = rawMetadata.title;
    extractionData.platform_metadata = {
      channel: rawMetadata.channel || rawMetadata.site_name || null,
      duration: rawMetadata.duration || null,
      view_count: rawMetadata.view_count || null,
    };

    // Update reel row
    const { error: updateError } = await supabaseAdmin
      .from("reels")
      .update({
        extraction_data: extractionData,
        classification: extractionData.activity ? guessClassification(extractionData) : null,
      })
      .eq("id", reel_id);

    if (updateError) {
      console.error("Failed to update reel:", updateError);
    }

    return new Response(
      JSON.stringify(extractionData),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Extraction error:", error);
    return new Response(
      JSON.stringify({ error: (error as Error).message, fallback: true }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

// Quick classification based on extraction data (refined in Story 2.4)
function guessClassification(data: any): string {
  if (data.date && data.venue_name && data.booking_url) return "real_event";
  if (data.venue_name && data.location) return "real_venue";
  if (data.activity?.toLowerCase().includes("recipe") || data.activity?.toLowerCase().includes("cook")) return "recipe_food";
  if (data.mood?.toLowerCase().includes("funny") || data.vibe?.toLowerCase().includes("meme") || data.vibe?.toLowerCase().includes("brainrot")) return "humour_identity";
  return "vibe_inspiration";
}
