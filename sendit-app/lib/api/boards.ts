import { apiRequest } from "./client";
import {
  Board,
  GeneratedSuggestion,
  Member,
  PersistedAuthSession,
  Reel,
  TasteProfile,
} from "./types";

export async function listBoards(session: PersistedAuthSession) {
  const response = await apiRequest<{ boards: Board[] }>(
    "/api/v1/boards",
    { method: "GET" },
    session
  );
  return response.boards;
}

export async function createBoard(
  session: PersistedAuthSession,
  name: string,
  displayName: string
) {
  return apiRequest<Board>(
    "/api/v1/boards",
    {
      method: "POST",
      body: JSON.stringify({ name, display_name: displayName }),
    },
    session
  );
}

export async function joinBoard(
  session: PersistedAuthSession,
  joinCode: string,
  displayName: string
) {
  return apiRequest<Board>(
    "/api/v1/boards/join",
    {
      method: "POST",
      body: JSON.stringify({ join_code: joinCode, display_name: displayName }),
    },
    session
  );
}

export async function updateBoard(
  session: PersistedAuthSession,
  boardId: string,
  name: string
) {
  return apiRequest<Board>(
    `/api/v1/boards/${boardId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ name }),
    },
    session
  );
}

export async function deleteBoard(
  session: PersistedAuthSession,
  boardId: string
) {
  return apiRequest<{ success: boolean; message: string }>(
    `/api/v1/boards/${boardId}`,
    { method: "DELETE" },
    session
  );
}

export async function listBoardMembers(
  session: PersistedAuthSession,
  boardId: string
) {
  const response = await apiRequest<{ members: Member[] }>(
    `/api/v1/boards/${boardId}/members`,
    { method: "GET" },
    session
  );
  return response.members;
}

export async function listBoardReels(
  session: PersistedAuthSession,
  boardId: string,
  memberId: string
) {
  const response = await apiRequest<{ reels: Reel[] }>(
    `/api/v1/boards/${boardId}/reels`,
    {
      method: "GET",
      headers: { "x-member-id": memberId },
    },
    session
  );
  return response.reels;
}

export async function addBoardReel(
  session: PersistedAuthSession,
  boardId: string,
  memberId: string,
  payload: { url: string; platform: string }
) {
  const response = await apiRequest<{ success: boolean; reel: Reel }>(
    `/api/v1/boards/${boardId}/reels`,
    {
      method: "POST",
      headers: { "x-member-id": memberId },
      body: JSON.stringify(payload),
    },
    session
  );
  return response.reel;
}

export async function getTasteProfile(
  session: PersistedAuthSession,
  boardId: string
) {
  return apiRequest<TasteProfile>(
    `/api/v1/boards/${boardId}/taste-profile`,
    { method: "GET" },
    session
  );
}

export async function syncTasteProfile(
  session: PersistedAuthSession,
  boardId: string
) {
  return apiRequest<TasteProfile>(
    `/api/v1/boards/${boardId}/taste-profile/sync`,
    {
      method: "POST",
      body: JSON.stringify({ force: true }),
    },
    session
  );
}

export async function generateSuggestions(
  session: PersistedAuthSession,
  boardId: string,
  payload: { category?: string; count?: number; liked_reel_ids?: string[]; disliked_reel_ids?: string[] } = {}
) {
  const response = await apiRequest<{ suggestions: GeneratedSuggestion[] }>(
    `/api/v1/boards/${boardId}/suggestions/generate`,
    {
      method: "POST",
      body: JSON.stringify({
        count: payload.count ?? 1,
        ...(payload.category ? { category: payload.category } : {}),
        liked_reel_ids: payload.liked_reel_ids ?? [],
        disliked_reel_ids: payload.disliked_reel_ids ?? [],
      }),
    },
    session
  );
  return response.suggestions;
}

export async function scrapeMedia(
  session: PersistedAuthSession,
  url: string
) {
  return apiRequest<Record<string, unknown>>(
    "/api/v1/media/scrape",
    {
      method: "POST",
      body: JSON.stringify({ url }),
    },
    session
  );
}

export async function extractReel(
  session: PersistedAuthSession,
  boardId: string,
  reelId: string
) {
  return apiRequest<{ reel_id: string; classification: string | null; extraction_data: Record<string, unknown> }>(
    `/api/v1/boards/${boardId}/reels/${reelId}/extract`,
    { method: "POST" },
    session
  );
}
