import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface BusySlot { start: string; end: string; }

function computeFreeWindows(calendarMasks: { busy_slots: BusySlot[] }[], daysAhead = 14): string[] {
  const allBusy: BusySlot[] = calendarMasks.flatMap(m => m.busy_slots || []);
  allBusy.sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime());

  const merged: BusySlot[] = [];
  for (const slot of allBusy) {
    if (merged.length === 0 || new Date(slot.start) > new Date(merged[merged.length - 1].end)) {
      merged.push({ ...slot });
    } else {
      merged[merged.length - 1].end = new Date(Math.max(
        new Date(merged[merged.length - 1].end).getTime(), new Date(slot.end).getTime()
      )).toISOString();
    }
  }

  const now = new Date();
  const end = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);
  const freeWindows: string[] = [];
  let cursor = now;
  for (const slot of merged) {
    const slotStart = new Date(slot.start);
    if (slotStart > cursor) freeWindows.push(`${cursor.toISOString()} to ${slotStart.toISOString()}`);
    cursor = new Date(Math.max(cursor.getTime(), new Date(slot.end).getTime()));
  }
  if (cursor < end) freeWindows.push(`${cursor.toISOString()} to ${end.toISOString()}`);
  return freeWindows;
}

const SUGGESTION_SYSTEM_PROMPT = `You are a plan-making assistant for a friend group app called Sendit. You generate ONE specific, actionable plan suggestion based on their taste profile and shared content.

RULES:
- "what": Concise plan description (e.g., "Club night at Peckham Audio")
- "why": 1-2 sentences explaining WHY this fits the group, referencing their content patterns
- "where": Full venue name and address
- "when": Specific date and time (e.g., "Saturday 5 April, 10pm")
- "cost_per_person": Estimated cost as string (e.g., "£12", "£25-35", "Free")
- "booking_url": Plausible booking URL or "" if unknown
- "influenced_by": Array of 2-4 reel indices (0-based) that most influenced this suggestion

The suggestion must feel personally tailored. Prefer specific, well-known venues in the group's location patterns. The "why" must reference actual patterns from their taste profile or reels.

Return ONLY valid JSON. No markdown, no explanation.`;

async function callClaudeWithRetry(userPrompt: string, maxRetries = 1): Promise<string> {
  const apiKey = Deno.env.get("CLAUDE_API_KEY");
  if (!apiKey) throw new Error("CLAUDE_API_KEY not configured");

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
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
          temperature: 0.5,
          system: SUGGESTION_SYSTEM_PROMPT,
          messages: [{ role: "user", content: userPrompt }],
        }),
      });
      if (!response.ok) throw new Error(`Claude API ${response.status}`);
      const data = await response.json();
      return data.content[0].text;
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
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { board_id, exclude_summary } = await req.json();

    if (!board_id) {
      return new Response(
        JSON.stringify({ error: "board_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabaseAdmin = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Fetch taste profile
    const { data: tasteProfile } = await supabaseAdmin
      .from("taste_profiles")
      .select("*")
      .eq("board_id", board_id)
      .single();

    if (!tasteProfile?.profile_data || Object.keys(tasteProfile.profile_data).length === 0) {
      return new Response(
        JSON.stringify({ data: null, message: "No taste profile exists for this board. Share more reels first." }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Fetch reels
    const { data: reels } = await supabaseAdmin
      .from("reels")
      .select("id, platform, extraction_data, classification, created_at")
      .eq("board_id", board_id)
      .not("extraction_data", "is", null)
      .order("created_at", { ascending: false });

    // Fetch members + calendar masks
    const { data: members } = await supabaseAdmin
      .from("members")
      .select("id")
      .eq("board_id", board_id);

    let freeWindows: string[] = [];
    if (members?.length) {
      const memberIds = members.map(m => m.id);
      const { data: masks } = await supabaseAdmin
        .from("calendar_masks")
        .select("busy_slots")
        .in("member_id", memberIds);

      if (masks?.length) {
        freeWindows = computeFreeWindows(masks);
      }
    }

    // Check for time-sensitive events (dates in next 14 days)
    const now = new Date();
    const twoWeeksOut = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
    const urgentEvents = (reels || []).filter(r => {
      if (r.classification !== "real_event" && r.classification !== "competition") return false;
      const eventDate = r.extraction_data?.date;
      if (!eventDate) return false;
      const d = new Date(eventDate);
      return d >= now && d <= twoWeeksOut;
    });

    // Build prompt
    const reelSummaries = (reels || []).map((r, i) =>
      `[${i}] ${r.platform} | ${r.classification || "unclassified"} | ${r.extraction_data?.title || r.extraction_data?.description?.slice(0, 80) || "no title"}${r.extraction_data?.date ? ` | DATE: ${r.extraction_data.date}` : ""}`
    ).join("\n");

    let userPrompt = `Here is a friend group's taste profile and shared reels. Generate ONE specific plan suggestion.

GROUP TASTE PROFILE:
${JSON.stringify(tasteProfile.profile_data, null, 2)}

GROUP IDENTITY: ${tasteProfile.identity_label || "Not yet generated"}

REELS SHARED (${(reels || []).length} total):
${reelSummaries}`;

    if (freeWindows.length > 0) {
      userPrompt += `\n\nCALENDAR: The group is mutually free during these windows:\n${freeWindows.slice(0, 10).join("\n")}\nSuggest a time within one of these windows.`;
    } else {
      userPrompt += `\n\nNo calendar data available. Suggest a reasonable time based on the activity type.`;
    }

    if (urgentEvents.length > 0) {
      userPrompt += `\n\nURGENT: ${urgentEvents.length} reel(s) are about REAL EVENTS happening in the next 14 days. STRONGLY prefer suggesting one of these time-sensitive events over a general vibe suggestion. These events have dates and will expire.`;
    }

    if (exclude_summary) {
      userPrompt += `\n\nIMPORTANT: Generate a DIFFERENT suggestion from this previous one: "${exclude_summary}". Do not repeat the same venue or activity.`;
    }

    userPrompt += `\n\nReturn JSON with: what, why, where, when, cost_per_person, booking_url, influenced_by (array of reel indices).`;

    // Call Claude
    let claudeResponse: string;
    try {
      claudeResponse = await callClaudeWithRetry(userPrompt);
    } catch {
      return new Response(
        JSON.stringify({ error: "Suggestion generation failed", fallback: true }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Parse response
    let suggestionData: any;
    try {
      const cleaned = claudeResponse.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
      suggestionData = JSON.parse(cleaned);
    } catch {
      return new Response(
        JSON.stringify({ error: "Invalid suggestion format", fallback: true }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Map influenced_by indices to actual reel UUIDs
    if (suggestionData.influenced_by && reels?.length) {
      suggestionData.influenced_by = suggestionData.influenced_by
        .filter((i: number) => i >= 0 && i < reels.length)
        .map((i: number) => reels[i].id);
    }

    // Insert suggestion
    const { data: inserted, error: insertError } = await supabaseAdmin
      .from("suggestions")
      .insert({
        board_id,
        suggestion_data: suggestionData,
        status: "active",
      })
      .select()
      .single();

    if (insertError) {
      return new Response(
        JSON.stringify({ error: `Failed to save suggestion: ${insertError.message}` }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ data: inserted }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Suggest error:", error);
    return new Response(
      JSON.stringify({ error: (error as Error).message, fallback: true }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
