import { supabase } from "../supabase";

export interface SuggestionData {
  what: string;
  why: string;
  where: string;
  when: string;
  cost_per_person: string;
  booking_url: string;
  influenced_by: string[];
}

export interface Suggestion {
  id: string;
  board_id: string;
  suggestion_data: SuggestionData;
  status: "active" | "archived" | "completed";
  created_at: string;
}

export async function generateSuggestion(
  boardId: string,
  excludeSummary?: string
): Promise<{ data: Suggestion | null; message?: string; error?: string }> {
  const { data, error } = await supabase.functions.invoke("suggest", {
    body: { board_id: boardId, exclude_summary: excludeSummary },
  });

  if (error) {
    return { data: null, error: `Suggestion failed: ${error.message}` };
  }

  return data;
}

export async function getActiveSuggestion(
  boardId: string
): Promise<Suggestion | null> {
  const { data, error } = await supabase
    .from("suggestions")
    .select("*")
    .eq("board_id", boardId)
    .eq("status", "active")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  if (error || !data) return null;
  return data as Suggestion;
}

export async function archiveSuggestion(suggestionId: string): Promise<void> {
  await supabase
    .from("suggestions")
    .update({ status: "archived" })
    .eq("id", suggestionId);
}
