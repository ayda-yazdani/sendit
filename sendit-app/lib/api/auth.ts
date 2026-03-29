import * as SecureStore from "expo-secure-store";

import { apiRequest } from "./client";
import { AuthResponse, PersistedAuthSession } from "./types";

const SESSION_STORAGE_KEY = "sendit.auth.session";
const SURVEY_STORAGE_KEY = "sendit.survey.completed";

export async function signUp(email: string, password: string, displayName: string) {
  return apiRequest<AuthResponse>("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      metadata: { display_name: displayName },
    }),
  });
}

export async function logIn(email: string, password: string) {
  return apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(session: PersistedAuthSession) {
  return apiRequest<{ user: PersistedAuthSession["user"] }>(
    "/api/v1/auth/me",
    { method: "GET" },
    session
  );
}

export async function logOut(session: PersistedAuthSession) {
  return apiRequest<void>("/api/v1/auth/logout", { method: "POST" }, session);
}

export async function saveSession(session: PersistedAuthSession | null) {
  if (!session) {
    await SecureStore.deleteItemAsync(SESSION_STORAGE_KEY);
    return;
  }
  await SecureStore.setItemAsync(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export async function loadSession() {
  const raw = await SecureStore.getItemAsync(SESSION_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PersistedAuthSession;
  } catch {
    await SecureStore.deleteItemAsync(SESSION_STORAGE_KEY);
    return null;
  }
}

export async function saveSurveyCompleted(value: boolean) {
  if (value) {
    await SecureStore.setItemAsync(SURVEY_STORAGE_KEY, "true");
    return;
  }
  await SecureStore.deleteItemAsync(SURVEY_STORAGE_KEY);
}

export async function loadSurveyCompleted() {
  return (await SecureStore.getItemAsync(SURVEY_STORAGE_KEY)) === "true";
}
