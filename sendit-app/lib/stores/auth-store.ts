import { create } from "zustand";

import {
  getCurrentUser,
  loadSession,
  loadSurveyCompleted,
  logIn,
  logOut,
  saveSession,
  saveSurveyCompleted,
  signUp,
} from "@/lib/api/auth";
import { PersistedAuthSession } from "@/lib/api/types";

interface AuthState {
  session: PersistedAuthSession | null;
  isLoading: boolean;
  isInitialized: boolean;
  surveyCompleted: boolean;
  initialize: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName: string) => Promise<void>;
  signOut: () => Promise<void>;
  markSurveyCompleted: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set) => ({
  session: null,
  isLoading: false,
  isInitialized: false,
  surveyCompleted: false,

  initialize: async () => {
    set({ isLoading: true });

    try {
      const [storedSession, storedSurveyCompleted] = await Promise.all([
        loadSession(),
        loadSurveyCompleted(),
      ]);

      if (!storedSession) {
        set({
          session: null,
          surveyCompleted: storedSurveyCompleted,
          isInitialized: true,
          isLoading: false,
        });
        return;
      }

      const me = await getCurrentUser(storedSession);
      const session = { ...storedSession, user: me.user };
      const surveyCompleted =
        Boolean(me.user.user_metadata?.survey_completed) || storedSurveyCompleted;

      await saveSession(session);

      set({
        session,
        surveyCompleted,
        isInitialized: true,
        isLoading: false,
      });
    } catch (error) {
      console.error("Failed to initialize auth store:", error);
      await saveSession(null);
      set({
        session: null,
        surveyCompleted: false,
        isInitialized: true,
        isLoading: false,
      });
    }
  },

  signIn: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await logIn(email.trim(), password);
      if (!response.user || !response.session) {
        throw new Error(response.message || "Login failed.");
      }

      const session = { user: response.user, session: response.session };
      await saveSession(session);

      set({
        session,
        surveyCompleted: Boolean(response.user.user_metadata?.survey_completed),
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  signUp: async (email, password, displayName) => {
    set({ isLoading: true });
    try {
      const response = await signUp(email.trim(), password, displayName.trim());
      if (!response.user || !response.session) {
        throw new Error(
          response.message ||
            "Account created, but no active session was returned."
        );
      }

      const session = { user: response.user, session: response.session };
      await saveSession(session);

      set({
        session,
        surveyCompleted: Boolean(response.user.user_metadata?.survey_completed),
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  signOut: async () => {
    const current = useAuthStore.getState().session;
    if (current) {
      try {
        await logOut(current);
      } catch (error) {
        console.warn("Logout request failed:", error);
      }
    }

    await Promise.all([saveSession(null), saveSurveyCompleted(false)]);
    set({ session: null, surveyCompleted: false });
  },

  markSurveyCompleted: async () => {
    await saveSurveyCompleted(true);
    set({ surveyCompleted: true });
  },
}));
