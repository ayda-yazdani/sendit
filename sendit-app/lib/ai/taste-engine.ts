import { supabase } from "../supabase";

export interface TasteProfileData {
  activity_types: string[];
  aesthetic: string;
  food_preferences: string[];
  location_patterns: string[];
  price_range: string;
  humour_style: string;
  platform_mix: Record<string, number>;
}

export interface TasteProfile {
  id: string;
  board_id: string;
  profile_data: TasteProfileData;
  identity_label: string | null;
  updated_at: string;
}

export interface TasteUpdateResult {
  data: TasteProfile | null;
  message?: string;
  error?: string;
  fallback?: boolean;
}

export async function updateTasteProfile(boardId: string): Promise<TasteUpdateResult> {
  const { data, error } = await supabase.functions.invoke("taste-update", {
    body: { board_id: boardId },
  });
  if (error) return { data: null, error: `Taste update failed: ${error.message}`, fallback: true };
  return data as TasteUpdateResult;
}

export async function getTasteProfile(boardId: string): Promise<TasteProfile | null> {
  const { data, error } = await supabase.from("taste_profiles").select("*").eq("board_id", boardId).single();
  if (error || !data) return null;
  return data as TasteProfile;
}
