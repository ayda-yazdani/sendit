export type Platform = "youtube" | "instagram" | "tiktok" | "x" | "other";

const PLATFORM_PATTERNS: Record<Exclude<Platform, "other">, RegExp> = {
  youtube: /youtube\.com\/shorts\/|youtu\.be\/|youtube\.com\/watch/,
  instagram: /instagram\.com\/(reel|p)\//,
  tiktok: /tiktok\.com\/@.*\/video\/|vm\.tiktok\.com\//,
  x: /x\.com\/.*\/status\/|twitter\.com\/.*\/status\//,
};

export function detectPlatform(url: string): Platform {
  for (const [platform, pattern] of Object.entries(PLATFORM_PATTERNS)) {
    if (pattern.test(url)) {
      return platform as Platform;
    }
  }
  return "other";
}

export function isValidUrl(text: string): boolean {
  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export const PLATFORM_DISPLAY: Record<Platform, { emoji: string; label: string; color: string }> = {
  youtube: { emoji: "▶️", label: "YouTube", color: "#FF0000" },
  instagram: { emoji: "📸", label: "Instagram", color: "#E4405F" },
  tiktok: { emoji: "🎵", label: "TikTok", color: "#00F2EA" },
  x: { emoji: "𝕏", label: "X", color: "#000000" },
  other: { emoji: "🔗", label: "Link", color: "#666666" },
};
