import { generateSuggestions } from "@/lib/api/boards";
import { GeneratedSuggestion } from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth-store";

export interface SuggestionData extends GeneratedSuggestion {}

export interface Suggestion {
  id: string;
  board_id: string;
  suggestion_data: SuggestionData;
  status: "active";
  created_at: string;
}

export async function generateSuggestion(
  boardId: string,
  category?: string
): Promise<{ data: Suggestion | null; message?: string; error?: string }> {
  const session = useAuthStore.getState().session;
  if (!session) {
    return { data: null, error: "Not authenticated." };
  }

  try {
    const suggestions = await generateSuggestions(session, boardId, {
      category,
      count: 1,
    });
    const suggestion = suggestions[0];
    if (!suggestion) {
      return { data: null, message: "No suggestion returned." };
    }

    return {
      data: {
        id: `generated-${Date.now()}`,
        board_id: boardId,
        suggestion_data: suggestion,
        status: "active",
        created_at: new Date().toISOString(),
      },
    };
  } catch (error) {
    return { data: null, error: (error as Error).message };
  }
}

export async function getActiveSuggestion(): Promise<Suggestion | null> {
  return null;
}

export async function archiveSuggestion(): Promise<void> {
  return;
}
