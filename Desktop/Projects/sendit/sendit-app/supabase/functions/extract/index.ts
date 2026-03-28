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

// ---- SCRAPING VIA MAX'S PYTHON BACKEND (no API keys needed) ----

async function fetchViaScraperBackend(url: string) {
  const backendUrl = Deno.env.get("SCRAPER_BACKEND_URL") || "http://localhost:8000";
  const supabaseKey = Deno.env.get("SUPABASE_ANON_KEY") || "";

  try {
    const response = await fetch(`${backendUrl}/api/v1/media/scrape`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${supabaseKey}`,
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      console.warn(`Scraper backend returned ${response.status}, falling back to OG`);
      return null;
    }

    const data = await response.json();
    return {
      title: data.title || null,
      description: data.description || null,
      thumbnail_url: data.cover_image_url || null,
      video_url: data.video_url || null,
      channel: data.user?.name || data.user?.username || null,
      creator_username: data.user?.username || null,
      duration: data.duration || null,
      post_date: data.post_date || null,
      media_id: data.media_id || null,
      platform: data.platform || null,
      canonical_url: data.canonical_url || null,
    };
  } catch (err) {
    console.warn("Scraper backend unavailable:", err);
    return null;
  }
}

// ---- FALLBACK: Open Graph scraping (no backend needed) ----

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
      thumbnail_url: getOg("image") || null,
      channel: getOg("site_name") || null,
    };
  } catch {
    return { title: null, description: null, thumbnail_url: null, channel: null };
  }
}

// ---- CLAUDE AI EXTRACTION ----

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
  const cleaned = text.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
  return JSON.parse(cleaned);
}

// ---- CLASSIFICATION ----

function guessClassification(data: any): string {
  if (data.date && data.venue_name && data.booking_url) return "real_event";
  if (data.venue_name && data.location) return "real_venue";
  if (data.activity?.toLowerCase().includes("recipe") || data.activity?.toLowerCase().includes("cook")) return "recipe_food";
  if (data.mood?.toLowerCase().includes("funny") || data.vibe?.toLowerCase().includes("meme") || data.vibe?.toLowerCase().includes("brainrot")) return "humour_identity";
  return "vibe_inspiration";
}

// ---- MAIN HANDLER ----

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

    const platform = detectPlatform(url);

    // Step 1: Try Max's scraper backend first (no API keys needed)
    let rawMetadata = await fetchViaScraperBackend(url);

    // Step 2: Fall back to direct OG scraping if backend unavailable
    if (!rawMetadata) {
      rawMetadata = await fetchOpenGraphMetadata(url);
    }

    rawMetadata.source_platform = platform;
    rawMetadata.source_url = url;

    // Step 3: Send to Claude for structured extraction
    let extractionData: any;
    try {
      extractionData = await extractWithClaude(rawMetadata, url, platform);
    } catch {
      // Retry once
      try {
        await new Promise((r) => setTimeout(r, 2000));
        extractionData = await extractWithClaude(rawMetadata, url, platform);
      } catch {
        extractionData = { error: "extraction_failed", raw_url: url };
      }
    }

    // Supplement with raw metadata
    if (rawMetadata.thumbnail_url) extractionData.thumbnail_url = rawMetadata.thumbnail_url;
    if (rawMetadata.title && !extractionData.title) extractionData.title = rawMetadata.title;
    if (rawMetadata.creator_username && !extractionData.creator) extractionData.creator = rawMetadata.creator_username;
    extractionData.platform_metadata = {
      channel: rawMetadata.channel || null,
      duration: rawMetadata.duration || null,
      media_id: rawMetadata.media_id || null,
      post_date: rawMetadata.post_date || null,
    };

    // Update reel row
    await supabaseAdmin
      .from("reels")
      .update({
        extraction_data: extractionData,
        classification: extractionData.activity ? guessClassification(extractionData) : null,
      })
      .eq("id", reel_id);

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
