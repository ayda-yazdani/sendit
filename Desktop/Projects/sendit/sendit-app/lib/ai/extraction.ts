import { supabase } from "@/lib/supabase";

export async function invokeExtraction(reelId: string, url: string) {
  try {
    const { data, error } = await supabase.functions.invoke("extract", {
      body: { url, reel_id: reelId },
    });

    if (error) {
      console.warn("Extraction failed:", error.message);
      return null;
    }

    return data;
  } catch (err) {
    console.warn("Extraction service unavailable:", err);
    return null;
  }
}
