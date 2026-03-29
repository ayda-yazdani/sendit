import { create } from "zustand";
import { supabase } from "@/lib/supabase";
import { Session } from "@supabase/supabase-js";

interface AuthState {
  session: Session | null;
  isLoading: boolean;
  isInitialized: boolean;
  initialize: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  session: null,
  isLoading: false,
  isInitialized: false,

  initialize: async () => {
    if (get().isInitialized) return;
    set({ isLoading: true });

    try {
      const { data: { session } } = await supabase.auth.getSession();
      set({ session, isInitialized: true, isLoading: false });

      // Listen for auth changes
      supabase.auth.onAuthStateChange((_event, session) => {
        set({ session });
      });
    } catch (error) {
      console.error("Failed to initialize auth store:", error);
      set({ isInitialized: true, isLoading: false });
    }
  },

  signOut: async () => {
    await supabase.auth.signOut();
    set({ session: null });
  },
}));
