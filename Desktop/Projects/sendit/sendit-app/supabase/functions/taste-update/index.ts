import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const TASTE_PROFILE_SYSTEM_PROMPT = `You are a cultural analyst for a friend group app called Sendit. You analyze shared video content extractions from a friend group and produce a structured taste profile.

Analyze ALL extractions and produce a JSON object with:
- activity_types: Array of 3-7 activities (e.g., "club nights", "rooftop bars", "dinner spots")
- aesthetic: Short phrase 2-5 words (e.g., "underground, intimate")
- food_preferences: Array of 2-5 cuisines (e.g., "Japanese", "street food")
- location_patterns: Array of 1-4 areas (e.g., "east London", "Shoreditch")
- price_range: Human-readable string (e.g., "~£15/head")
- humour_style: Short phrase (e.g., "dark, absurdist"). Use "not enough data yet" if none
- platform_mix: Object counting reels per platform (e.g., { "tiktok": 5, "instagram": 3 })

Also generate:
- identity_label: A fun 2-4 word group identity (e.g., "The Chaotic Intellectuals", "The Low-Effort Loyalists")

Return ONLY valid JSON with keys: activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix, identity_label. No markdown.`;

const REQUIRED_KEYS = ["activity_types", "aesthetic", "food_preferences", "location_patterns", "price_range", "humour_style", "platform_mix"];

async function callGeminiWithRetry(userPrompt: string, maxRetries = 1): Promise<string> {
  const apiKey = Deno.env.get("GEMINI_API_KEY");
  if (!apiKey) throw new Error("GEMINI_API_KEY not set");

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: TASTE_PROFILE_SYSTEM_PROMPT }] },
          contents: [{ role: "user", parts: [{ text: userPrompt }] }],
          generationConfig: { temperature: 0.3, maxOutputTokens: 1024 },
        }),
      });
      if (!response.ok) throw new Error(`Gemini API ${response.status}`);
      const data = await response.json();
      return data.candidates[0].content.parts[0].text;
    } catch (error) {
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
        continue;
      }
      throw error;
    }
  }
  throw new Error("Exhausted retries");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const { board_id } = await req.json();
    if (!board_id) return new Response(JSON.stringify({ error: "board_id is required" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    const supabaseAdmin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const { data: reels, error: reelsError } = await supabaseAdmin
      .from("reels").select("id, platform, extraction_data, classification")
      .eq("board_id", board_id).not("extraction_data", "is", null);

    if (reelsError) return new Response(JSON.stringify({ error: reelsError.message }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    if (!reels || reels.length < 3) {
      return new Response(JSON.stringify({ data: null, message: "Need at least 3 reels to generate taste profile" }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    const reelData = reels.map(r => ({ platform: r.platform, classification: r.classification, extraction: r.extraction_data }));
    const platformMix: Record<string, number> = {};
    for (const reel of reels) platformMix[reel.platform] = (platformMix[reel.platform] || 0) + 1;

    const userPrompt = `Here are ${reels.length} video extractions shared by a friend group. Analyze them and produce the group taste profile with identity_label.\n\nPlatform distribution: ${JSON.stringify(platformMix)}\n\nEXTRACTIONS:\n${JSON.stringify(reelData, null, 2)}`;

    let response: string;
    try { response = await callGeminiWithRetry(userPrompt); } catch {
      return new Response(JSON.stringify({ error: "Taste profile generation failed", fallback: true }), { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    let profileData: any;
    let identityLabel: string | null = null;
    try {
      const cleaned = response.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
      profileData = JSON.parse(cleaned);
      if (!REQUIRED_KEYS.every(k => k in profileData)) throw new Error("Missing keys");
      profileData.platform_mix = platformMix;
      identityLabel = profileData.identity_label || null;
      delete profileData.identity_label;
    } catch {
      console.error("Malformed response:", response);
      return new Response(JSON.stringify({ error: "Invalid profile format", fallback: true }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    const { data: upserted, error: upsertError } = await supabaseAdmin
      .from("taste_profiles")
      .upsert({ board_id, profile_data: profileData, identity_label: identityLabel, updated_at: new Date().toISOString() }, { onConflict: "board_id" })
      .select().single();

    if (upsertError) return new Response(JSON.stringify({ error: upsertError.message }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    return new Response(JSON.stringify({ data: upserted }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  } catch (error) {
    return new Response(JSON.stringify({ error: (error as Error).message }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});
