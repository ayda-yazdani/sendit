import * as SecureStore from "expo-secure-store";

const REACTED_REELS_PREFIX = "sendit-reacted-reels";
const SAFE_KEY_CHARS = /[^a-zA-Z0-9._-]/g;

function getStorageKey(boardId: string) {
  if (!boardId || typeof boardId !== "string") return null;
  const trimmed = boardId.trim();
  if (!trimmed) return null;
  const safe = trimmed.replace(SAFE_KEY_CHARS, "_");
  return `${REACTED_REELS_PREFIX}_${safe}`;
}

function parseReelIds(raw: string | null) {
  if (!raw) return new Set<string>();
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return new Set(parsed.filter((item) => typeof item === "string"));
    }
  } catch {}
  return new Set<string>();
}

export async function loadReactedReelIds(boardId: string) {
  const storageKey = getStorageKey(boardId);
  if (!storageKey) return new Set<string>();
  const raw = await SecureStore.getItemAsync(storageKey);
  return parseReelIds(raw);
}

export async function markReelReacted(boardId: string, reelId: string) {
  const storageKey = getStorageKey(boardId);
  if (!storageKey) return new Set<string>();
  const reelIds = await loadReactedReelIds(boardId);
  if (!reelIds.has(reelId)) {
    reelIds.add(reelId);
    await SecureStore.setItemAsync(storageKey, JSON.stringify(Array.from(reelIds)));
  }
  return reelIds;
}

export async function unmarkReelReacted(boardId: string, reelId: string) {
  const storageKey = getStorageKey(boardId);
  if (!storageKey) return new Set<string>();
  const reelIds = await loadReactedReelIds(boardId);
  if (reelIds.delete(reelId)) {
    await SecureStore.setItemAsync(storageKey, JSON.stringify(Array.from(reelIds)));
  }
  return reelIds;
}
