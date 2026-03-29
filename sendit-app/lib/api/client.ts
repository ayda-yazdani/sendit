import { PersistedAuthSession } from "./types";

const DEFAULT_API_BASE_URL = "https://sendit-henna.vercel.app";

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "");
}

export function getApiBaseUrl() {
  return trimTrailingSlash(
    process.env.EXPO_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL
  );
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildHeaders(session?: PersistedAuthSession | null, extra?: HeadersInit) {
  return {
    "Content-Type": "application/json",
    ...(session?.session.access_token
      ? { Authorization: `Bearer ${session.session.access_token}` }
      : {}),
    ...extra,
  };
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  session?: PersistedAuthSession | null
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: buildHeaders(session, options.headers),
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      message =
        (typeof data?.detail === "string" && data.detail) ||
        (typeof data?.message === "string" && data.message) ||
        message;
    } catch {
      // Ignore parse failures and keep the fallback message.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
