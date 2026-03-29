export interface ApiUser {
  id: string;
  email?: string | null;
  user_metadata?: Record<string, unknown> | null;
}

export interface ApiSession {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in?: number | null;
  expires_at?: number | null;
}

export interface AuthResponse {
  user: ApiUser | null;
  session: ApiSession | null;
  message?: string | null;
}

export interface PersistedAuthSession {
  user: ApiUser;
  session: ApiSession;
}

export interface Board {
  id: string;
  name: string;
  join_code: string;
  member_count?: number;
  created_at?: string;
}

export interface Member {
  id: string;
  board_id: string;
  display_name: string;
  device_id: string;
  avatar_url?: string | null;
  created_at?: string | null;
}

export interface Reel {
  id: string;
  board_id: string;
  added_by: string;
  url: string;
  platform: string;
  classification: string | null;
  extraction_data: Record<string, unknown> | null;
  created_at: string;
}

export interface TasteProfile {
  id: string;
  board_id: string;
  activity_types: string[];
  aesthetic_register: string[];
  food_preferences: string[];
  location_patterns: string[];
  price_range: string | null;
  vibe_tags: string[];
  identity_label: string | null;
  reel_count: number;
  updated_at: string;
  created_at: string;
}

export interface GeneratedSuggestion {
  what: string;
  why: string;
  where?: string | null;
  when?: string | null;
  cost_per_person?: string | null;
  booking_url?: string | null;
  influenced_by: string[];
  category: string;
  confidence: number;
}
