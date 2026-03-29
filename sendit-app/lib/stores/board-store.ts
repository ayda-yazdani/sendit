import { create } from "zustand";

import {
  createBoard as createBoardRequest,
  joinBoard as joinBoardRequest,
  listBoardMembers,
  listBoards,
} from "@/lib/api/boards";
import { Board, Member } from "@/lib/api/types";
import { useAuthStore } from "./auth-store";

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

function requireSession() {
  const session = useAuthStore.getState().session;
  if (!session) throw new Error("Not authenticated");
  return session;
}

export type { Board, Member };

export const useBoardStore = create<BoardState>()((set) => ({
  boards: [],
  activeBoard: null,
  activeBoardMembers: [],
  isLoading: false,
  error: null,

  fetchBoards: async () => {
    set({ isLoading: true, error: null });
    try {
      const boards = await listBoards(requireSession());
      set({ boards, isLoading: false });
    } catch (error) {
      set({
        boards: [],
        isLoading: false,
        error: (error as Error).message,
      });
    }
  },

  createBoard: async (name: string, displayName: string) => {
    set({ isLoading: true, error: null });
    try {
      const board = await createBoardRequest(requireSession(), name, displayName);
      set((state) => ({
        boards: [board, ...state.boards],
        isLoading: false,
      }));
      return board;
    } catch (error) {
      const message = (error as Error).message;
      set({ isLoading: false, error: message });
      throw error;
    }
  },

  joinBoard: async (code: string, displayName: string) => {
    set({ isLoading: true, error: null });
    try {
      const board = await joinBoardRequest(requireSession(), code, displayName);
      set((state) => ({
        boards: state.boards.some((item) => item.id === board.id)
          ? state.boards
          : [board, ...state.boards],
        isLoading: false,
      }));
      return board;
    } catch (error) {
      const message = (error as Error).message;
      set({ isLoading: false, error: message });
      throw error;
    }
  },

  setActiveBoard: (board: Board) =>
    set({ activeBoard: board, activeBoardMembers: [] }),

  fetchBoardMembers: async (boardId: string) => {
    try {
      const members = await listBoardMembers(requireSession(), boardId);
      set({ activeBoardMembers: members });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },
}));
