import { create } from "zustand";
import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";

const DEVICE_ID_KEY = "sendit_device_id";

interface AuthState {
  deviceId: string | null;
  googleId: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  deviceId: null,
  googleId: null,
  isLoading: false,
  isInitialized: false,

  initialize: async () => {
    if (get().isInitialized) return;
    set({ isLoading: true });

    try {
      let deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
      if (!deviceId) {
        deviceId = Crypto.randomUUID();
        await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId);
      }
      set({ deviceId, isInitialized: true, isLoading: false });
    } catch (error) {
      console.error("Failed to initialize auth store:", error);
      set({ isLoading: false });
    }
  },
}));
