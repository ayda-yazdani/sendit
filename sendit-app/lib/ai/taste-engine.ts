import { TasteProfile as ApiTasteProfile } from "@/lib/api/types";

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

export function mapTasteProfile(apiProfile: ApiTasteProfile): TasteProfile {
  return {
    id: apiProfile.id,
    board_id: apiProfile.board_id,
    identity_label: apiProfile.identity_label,
    updated_at: apiProfile.updated_at,
    profile_data: {
      activity_types: apiProfile.activity_types || [],
      aesthetic: apiProfile.aesthetic_register?.join(", ") || "",
      food_preferences: apiProfile.food_preferences || [],
      location_patterns: apiProfile.location_patterns || [],
      price_range: apiProfile.price_range || "",
      humour_style: apiProfile.vibe_tags?.join(", ") || "",
      platform_mix: {},
    },
  };
}
