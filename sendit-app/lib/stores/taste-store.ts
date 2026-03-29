import { create } from "zustand";

import { getTasteProfile, syncTasteProfile } from "@/lib/api/boards";
import { mapTasteProfile, TasteProfile } from "@/lib/ai/taste-engine";
import { useAuthStore } from "./auth-store";

interface TasteState {
  profile: TasteProfile | null;
  isLoading: boolean;
  error: string | null;
  fetchProfile: (boardId: string) => Promise<void>;
  regenerateProfile: (boardId: string) => Promise<void>;
  setProfile: (profile: TasteProfile) => void;
}

function requireSession() {
  const session = useAuthStore.getState().session;
  if (!session) throw new Error("Not authenticated");
  return session;
}

export const useTasteStore = create<TasteState>()((set) => ({
  profile: null,
  isLoading: false,
  error: null,

  fetchProfile: async (boardId: string) => {
    set({ isLoading: true, error: null });
    try {
      const profile = await getTasteProfile(requireSession(), boardId);
      set({ profile: mapTasteProfile(profile), isLoading: false });
    } catch {
      set({ profile: null, isLoading: false });
    }
  },

  regenerateProfile: async (boardId: string) => {
    set({ isLoading: true, error: null });
    try {
      const profile = await syncTasteProfile(requireSession(), boardId);
      set({ profile: mapTasteProfile(profile), isLoading: false });
    } catch (error) {
      set({ isLoading: false, error: (error as Error).message });
    }
  },

  setProfile: (profile: TasteProfile) => set({ profile }),
}));
