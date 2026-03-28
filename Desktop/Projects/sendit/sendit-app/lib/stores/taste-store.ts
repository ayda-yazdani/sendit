import { create } from "zustand";
import { supabase } from "../supabase";
import { TasteProfile, TasteProfileData, updateTasteProfile } from "../ai/taste-engine";

interface TasteState {
  profile: TasteProfile | null;
  isLoading: boolean;
  error: string | null;
  fetchProfile: (boardId: string) => Promise<void>;
  regenerateProfile: (boardId: string) => Promise<void>;
  setProfile: (profile: TasteProfile) => void;
}

export const useTasteStore = create<TasteState>()((set) => ({
  profile: null,
  isLoading: false,
  error: null,

  fetchProfile: async (boardId: string) => {
    set({ isLoading: true, error: null });
    const { data, error } = await supabase
      .from("taste_profiles")
      .select("*")
      .eq("board_id", boardId)
      .single();

    if (error || !data) {
      set({ profile: null, isLoading: false });
      return;
    }
    set({ profile: data as TasteProfile, isLoading: false });
  },

  regenerateProfile: async (boardId: string) => {
    set({ isLoading: true, error: null });
    const result = await updateTasteProfile(boardId);
    if (result.error) {
      set({ isLoading: false, error: result.error });
      return;
    }
    if (result.data) {
      set({ profile: result.data, isLoading: false });
    } else {
      set({ isLoading: false, error: result.message || null });
    }
  },

  setProfile: (profile: TasteProfile) => set({ profile }),
}));
