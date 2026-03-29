import { create } from "zustand";
import { supabase } from "../supabase";
import { generateJoinCode } from "../utils/join-code";
import { useAuthStore } from "./auth-store";

export interface Board {
  id: string;
  name: string;
  join_code: string;
  created_at: string;
}

export interface Member {
  id: string;
  board_id: string;
  display_name: string;
  user_id: string;
  avatar_url: string | null;
  push_token: string | null;
}

interface BoardState {
  boards: Board[];
  activeBoard: Board | null;
  activeBoardMembers: Member[];
  isLoading: boolean;
  error: string | null;
  fetchBoards: () => Promise<void>;
  createBoard: (name: string, displayName: string) => Promise<Board>;
  joinBoard: (code: string, displayName: string) => Promise<Board>;
  setActiveBoard: (board: Board) => void;
  fetchBoardMembers: (boardId: string) => Promise<void>;
}

function getUserId(): string {
  const session = useAuthStore.getState().session;
  if (!session) throw new Error("Not authenticated");
  return session.user.id;
}

function getDisplayName(): string {
  const session = useAuthStore.getState().session;
  return session?.user.user_metadata?.display_name || "User";
}

export const useBoardStore = create<BoardState>()((set, get) => ({
  boards: [],
  activeBoard: null,
  activeBoardMembers: [],
  isLoading: false,
  error: null,

  fetchBoards: async () => {
    const userId = getUserId();
    set({ isLoading: true, error: null });

    const { data: memberRows, error: memberError } = await supabase
      .from("members")
      .select("board_id")
      .eq("user_id", userId);

    if (memberError || !memberRows?.length) {
      set({ boards: [], isLoading: false });
      return;
    }

    const boardIds = memberRows.map((m: { board_id: string }) => m.board_id);
    const { data: boards, error: boardError } = await supabase
      .from("boards")
      .select("*")
      .in("id", boardIds)
      .order("created_at", { ascending: false });

    if (boardError) {
      set({ isLoading: false, error: boardError.message });
      return;
    }
    set({ boards: boards ?? [], isLoading: false });
  },

  createBoard: async (name: string, displayName: string): Promise<Board> => {
    set({ isLoading: true, error: null });
    const userId = getUserId();

    let board: Board | null = null;
    let attempts = 0;

    while (attempts < 3) {
      const joinCode = generateJoinCode();
      const { data, error } = await supabase
        .from("boards")
        .insert({ name: name.trim(), join_code: joinCode })
        .select()
        .single();

      if (error) {
        if (error.code === "23505" && attempts < 2) { attempts++; continue; }
        set({ isLoading: false, error: error.message });
        throw new Error(error.message);
      }
      board = data;
      break;
    }

    if (!board) {
      set({ isLoading: false, error: "Failed to generate unique join code" });
      throw new Error("Failed to generate unique join code");
    }

    const { error: memberError } = await supabase.from("members").insert({
      board_id: board.id,
      display_name: displayName.trim() || getDisplayName(),
      user_id: userId,
    });

    if (memberError) {
      await supabase.from("boards").delete().eq("id", board.id);
      set({ isLoading: false, error: memberError.message });
      throw new Error(memberError.message);
    }

    set((state) => ({ boards: [board!, ...state.boards], isLoading: false }));
    return board;
  },

  joinBoard: async (code: string, displayName: string): Promise<Board> => {
    set({ isLoading: true, error: null });
    const userId = getUserId();

    const { data: board, error: boardError } = await supabase
      .from("boards")
      .select("*")
      .ilike("join_code", code.trim())
      .single();

    if (boardError || !board) {
      set({ isLoading: false, error: "Board not found" });
      throw new Error("Board not found");
    }

    const { error: memberError } = await supabase.from("members").insert({
      board_id: board.id,
      display_name: displayName.trim() || getDisplayName(),
      user_id: userId,
    });

    if (memberError) {
      if (memberError.code === "23505") {
        set((state) => ({
          boards: state.boards.some((b) => b.id === board.id)
            ? state.boards : [board, ...state.boards],
          isLoading: false,
        }));
        return board;
      }
      set({ isLoading: false, error: memberError.message });
      throw new Error(memberError.message);
    }

    set((state) => ({ boards: [board, ...state.boards], isLoading: false }));
    return board;
  },

  setActiveBoard: (board: Board) => set({ activeBoard: board, activeBoardMembers: [] }),

  fetchBoardMembers: async (boardId: string) => {
    const { data, error } = await supabase.from("members").select("*").eq("board_id", boardId);
    if (!error && data) set({ activeBoardMembers: data });
  },
}));
