import { supabase } from "@/lib/supabase";

const BACKEND_URL = "http://localhost:8000";

export async function invokeExtraction(reelId: string, url: string) {
  try {
    // Get the user's access token for the backend
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      console.warn("No session for extraction");
      return null;
    }

    // Call FastAPI backend scrape endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/media/scrape`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      console.warn("Backend scrape failed:", response.status);
      // Fall back to edge function
      return invokeEdgeFunctionFallback(reelId, url);
    }

    const scrapeData = await response.json();

    // Map backend response to extraction_data format and update reel
    const extractionData = {
      title: scrapeData.title,
      description: scrapeData.description,
      thumbnail_url: scrapeData.cover_image_url,
      video_url: scrapeData.video_url,
      creator: scrapeData.user?.username || scrapeData.user?.name,
      duration: scrapeData.duration,
      post_date: scrapeData.post_date,
      media_id: scrapeData.media_id,
      canonical_url: scrapeData.canonical_url || scrapeData.resolved_url,
      venue_name: scrapeData.gemini?.location || null,
      price: scrapeData.gemini?.price || scrapeData.price || null,
      date: scrapeData.gemini?.time || scrapeData.time || null,
      booking_url: null,
      audio_track: null,
      audio_artist: null,
      hashtags: [],
      platform_metadata: {
        channel: scrapeData.user?.name,
        username: scrapeData.user?.username,
        profile_url: scrapeData.user?.profile_url,
        duration: scrapeData.duration,
        embed_url: scrapeData.embed_url,
      },
    };

    // Determine classification from Gemini ratings
    const classification = classifyFromGemini(scrapeData.gemini);

    // Update the reel in Supabase
    await supabase
      .from("reels")
      .update({ extraction_data: extractionData, classification })
      .eq("id", reelId);

    return extractionData;
  } catch (err) {
    console.warn("Backend extraction failed, falling back to edge function:", err);
    return invokeEdgeFunctionFallback(reelId, url);
  }
}

// Classify based on Gemini ratings from the backend
function classifyFromGemini(gemini: any): string | null {
  if (!gemini?.ratings) return null;

  const ratings = gemini.ratings as Record<string, number>;
  const isEvent = gemini.event === true;

  if (isEvent && (ratings.real_event ?? 0) > 0.3) return "real_event";

  // Find highest rated category
  let best: string | null = null;
  let bestScore = 0;
  for (const [key, score] of Object.entries(ratings)) {
    if (typeof score === "number" && score > bestScore) {
      best = key;
      bestScore = score;
    }
  }

  if (best && bestScore > 0.3) return best;
  return null;
}

// Fallback to the edge function if backend is unreachable
async function invokeEdgeFunctionFallback(reelId: string, url: string) {
  try {
    const { data, error } = await supabase.functions.invoke("extract", {
      body: { url, reel_id: reelId },
    });
    if (error) {
      console.warn("Edge function extraction also failed:", error.message);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}
