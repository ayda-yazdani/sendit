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

// ---- SCRAPING VIA MAX'S PYTHON BACKEND (no API keys needed, no Claude needed) ----

async function fetchViaScraperBackend(url: string): Promise<any | null> {
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
      console.warn(`Scraper backend returned ${response.status}`);
      return null;
    }

    return await response.json();
  } catch (err) {
    console.warn("Scraper backend unavailable:", err);
    return null;
  }
}

// ---- FALLBACK: Direct OG scraping (if Max's backend is down) ----

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
      cover_image_url: getOg("image") || null,
      user: { name: getOg("site_name") || null, username: null },
    };
  } catch {
    return { title: null, description: null, cover_image_url: null, user: null };
  }
}

// ---- HTML ENTITY DECODING ----

function decodeEntities(text: string | null): string | null {
  if (!text) return null;
  return text
    .replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&#x2019;/g, '\u2019').replace(/&#x2018;/g, '\u2018')
    .replace(/&#x201C;/g, '\u201C').replace(/&#x201D;/g, '\u201D')
    .replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n)))
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
}

// ---- MAP SCRAPER RESPONSE TO extraction_data ----

function mapToExtractionData(scraperData: any, url: string, platform: Platform) {
  return {
    title: decodeEntities(scraperData.title),
    description: decodeEntities(scraperData.description),
    thumbnail_url: scraperData.cover_image_url || null,
    video_url: scraperData.video_url || null,
    creator: scraperData.user?.username || scraperData.user?.name || null,
    duration: scraperData.duration || null,
    post_date: scraperData.post_date || null,
    media_id: scraperData.media_id || null,
    canonical_url: scraperData.canonical_url || scraperData.resolved_url || null,
    // These fields are populated later by Claude (classification / taste / suggestion steps)
    venue_name: null,
    location: null,
    price: null,
    date: scraperData.post_date || null,
    vibe: null,
    activity: null,
    mood: null,
    hashtags: [],
    booking_url: null,
    audio_track: null,
    audio_artist: null,
    platform_metadata: {
      channel: scraperData.user?.name || null,
      username: scraperData.user?.username || null,
      profile_url: scraperData.user?.profile_url || null,
      duration: scraperData.duration || null,
      embed_url: scraperData.embed_url || null,
    },
  };
}

// ---- CLASSIFICATION: Gemini ratings first, keyword fallback ----

function classifyFromGemini(gemini: any): string | null {
  if (!gemini) return null;

  const ratings = gemini.ratings || {};

  // Direct event flag from Gemini
  if (gemini.event === true) return "real_event";

  // Event-adjacent: high party/music/culture scores
  const eventScore = Math.max(ratings["Party"] || 0, ratings["Music"] || 0, ratings["Culture"] || 0);
  if (eventScore >= 0.75) return "real_event";

  // Venue: high restaurant/gym/zoo + location context
  if ((ratings["Restaurant"] || 0) >= 0.75) return "real_venue";
  const venueScore = Math.max(ratings["Restaurant"] || 0, ratings["Gym"] || 0, ratings["Zoo"] || 0, ratings["Beach"] || 0);
  const locationScore = Math.max(ratings["City"] || 0, ratings["Island"] || 0);
  if (venueScore >= 0.5 && locationScore >= 0.5) return "real_venue";

  // Food/recipe: high food but NOT a restaurant review
  if ((ratings["Food"] || 0) >= 0.75 && (ratings["Restaurant"] || 0) < 0.5) return "recipe_food";

  // Vibe/inspiration: travel, fashion, aesthetic content
  const vibeScore = Math.max(ratings["Travel"] || 0, ratings["Fashion"] || 0, ratings["Ocean"] || 0, ratings["Mountain"] || 0);
  if (vibeScore >= 0.75) return "vibe_inspiration";

  return null;
}

function classifyFromKeywords(data: any): string | null {
  const text = `${data.title || ""} ${data.description || ""}`.toLowerCase();
  if (!text.trim() || text.length < 10) return null;

  // Events — expanded keywords
  if (/ticket|book now|get tickets|event|tonight|this saturday|this friday|doors open|live show|festival|gig|concert|sold out|rsvp|free entry|guest list|lineup|performing/i.test(text)) return "real_event";

  // Venues — relaxed: no longer requires both venue AND action keywords
  if (/restaurant|bar |cafe|café|club|rooftop|pub|venue|lounge|bistro|brewery|winery|speakeasy|cocktail bar|brunch spot|izakaya|trattoria|taqueria|diner/i.test(text)) return "real_venue";
  if (/best spots|hidden gem|must visit|where to eat|where to go|food spot|date night spot|new opening|place to be/i.test(text)) return "real_venue";

  // Food/recipe
  if (/recipe|cook|ingredient|how to make|easy meal|homemade|meal prep|air fryer|what i eat|grocery haul|food hack|baking|sous vide/i.test(text)) return "recipe_food";

  // Humour/identity — expanded
  if (/meme|brainrot|pov:|npc|slay|delulu|unhinged|real ones|political|satire|relatable|crying|i can't|no way|send this to|tag someone|emotional damage|rent free/i.test(text)) return "humour_identity";

  // Vibe/inspiration — only match clearly aesthetic content
  if (/travel vlog|sunset|aesthetic|dreamy|wanderlust|bucket list|golden hour|cinematic|drone shot|nature escape/i.test(text)) return "vibe_inspiration";

  return null;
}

function guessClassification(data: any, scraperData: any): string | null {
  // Priority 1: Use Gemini vision classification from the backend
  const geminiResult = classifyFromGemini(scraperData?.gemini);
  if (geminiResult) return geminiResult;

  // Priority 2: Expanded keyword matching on title + description
  return classifyFromKeywords(data);
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

    // Step 1: Try Max's scraper backend (no API keys, no Claude)
    let scraperData = await fetchViaScraperBackend(url);

    // Step 2: Fallback to OG scraping
    if (!scraperData) {
      scraperData = await fetchOpenGraphMetadata(url);
    }

    // Step 3: Map to extraction_data format
    const extractionData = mapToExtractionData(scraperData, url, platform);

    // Step 4: Classify using Gemini ratings + keyword fallback
    const classification = guessClassification(extractionData, scraperData);

    // Step 5: Update reel row
    const { error: updateError } = await supabaseAdmin
      .from("reels")
      .update({
        extraction_data: extractionData,
        classification,
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
