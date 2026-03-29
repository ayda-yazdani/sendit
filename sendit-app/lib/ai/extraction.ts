import { extractReel } from "@/lib/api/boards";
import { useAuthStore } from "@/lib/stores/auth-store";

export async function invokeExtraction(reelId: string, _url: string, boardId: string) {
  const session = useAuthStore.getState().session;
  if (!session) return null;

  try {
    return await extractReel(session, boardId, reelId);
  } catch (error) {
    console.warn("Reel extraction failed:", error);
    return null;
  }
}
