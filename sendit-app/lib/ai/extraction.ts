import { scrapeMedia } from "@/lib/api/boards";
import { useAuthStore } from "@/lib/stores/auth-store";

export async function invokeExtraction(_reelId: string, url: string) {
  const session = useAuthStore.getState().session;
  if (!session) return null;

  try {
    return await scrapeMedia(session, url);
  } catch (error) {
    console.warn("Media scrape failed:", error);
    return null;
  }
}
