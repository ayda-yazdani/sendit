# Story 8.3: Group Playlist

## Description

As a board member,
I want a playlist generated from the music signals detected in our shared reels,
So that the group has a soundtrack that reflects our collective taste.

## Status

- **Epic:** Shared Objects
- **Priority:** P2
- **Branch:** `feature/shared-objects`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** reels on the board have audio track names in their `extraction_data` (e.g., from TikTok audio tags, Instagram music tags, YouTube video soundtracks)
**When** the user taps "Generate Playlist"
**Then** the system extracts all song/artist names from all reels' extraction_data
**And** deduplicates the list
**And** displays a Spotify-compatible playlist (list of "Song - Artist" entries)

**Given** a playlist has been generated
**When** the user views the playlist screen
**Then** each track is displayed with song name and artist
**And** a "Copy to Clipboard" button copies the full playlist as text
**And** a "Open in Spotify" button launches a Spotify search for the playlist (or uses Spotify URI scheme)

**Given** a board has no reels with audio track data
**When** the user tries to generate a playlist
**Then** a message reads: "No music signals detected yet. Share some reels with music!"

**Given** the board has 20+ reels with audio data
**When** the playlist is generated
**Then** Claude curates and orders the playlist for listening flow (not just a raw dump)
**And** the playlist has a generated title that reflects the group's vibe

**Given** new reels with audio data are added after a playlist was generated
**When** the user taps "Refresh Playlist"
**Then** a new playlist is generated incorporating the new tracks

## Technical Context

### Relevant Schema

```sql
reels (
  id uuid PK,
  board_id uuid FK,
  url text,
  platform text,
  extraction_data jsonb,   -- May contain: { audio_track, audio_artist, music_name, ... }
  classification text,
  created_at timestamptz
)

taste_profiles (
  id uuid PK,
  board_id uuid FK UNIQUE,
  profile_data jsonb,      -- Can store playlist data here
  identity_label text,
  updated_at timestamptz
)
```

**Audio signal fields in extraction_data (varies by platform):**

- TikTok: `audio_name`, `audio_artist` (from TikTok's audio tag system)
- Instagram: `music_name`, `music_artist` (from Instagram's music sticker/audio)
- YouTube: `audio_track` (from video description or auto-detected music)
- General: `hashtags` may contain song names, artist mentions in `description`

**Playlist Storage:** Store in `taste_profiles.profile_data.playlist`:

```json
{
  "playlist": {
    "title": "Summer Friends Soundtrack",
    "generated_at": "2026-03-28T12:00:00Z",
    "tracks": [
      { "song": "HUMBLE.", "artist": "Kendrick Lamar", "source_reel_id": "uuid" },
      { "song": "Espresso", "artist": "Sabrina Carpenter", "source_reel_id": "uuid" }
    ]
  }
}
```

### Architecture References

- **Edge Function:** `supabase/functions/generate-playlist/index.ts`
- **Claude API:** Used for curating and ordering tracks when there are enough signals
- **Screen:** Dedicated playlist screen or section within board detail
- **Components:** `components/shared/PlaylistCard.tsx`, `components/shared/TrackItem.tsx`
- **External:** Spotify URI scheme (`spotify:search:`) for "Open in Spotify" functionality
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Epic 2 (reels with extraction_data containing audio signals)
- **Requires:** Claude API key as Supabase secret (`CLAUDE_API_KEY`) -- for curation
- **Optional:** Spotify API for richer integration (out of scope for hackathon; use search URI instead)

## Implementation Notes

### Extracting Audio Signals from Reels

```typescript
interface AudioSignal {
  song: string;
  artist: string;
  reelId: string;
  platform: string;
}

const extractAudioSignals = (reels: any[]): AudioSignal[] => {
  const signals: AudioSignal[] = [];

  for (const reel of reels) {
    const data = reel.extraction_data as any;
    if (!data) continue;

    // TikTok audio tags
    if (data.audio_name || data.audio_track) {
      signals.push({
        song: data.audio_name ?? data.audio_track ?? '',
        artist: data.audio_artist ?? 'Unknown',
        reelId: reel.id,
        platform: reel.platform,
      });
      continue;
    }

    // Instagram music stickers
    if (data.music_name) {
      signals.push({
        song: data.music_name,
        artist: data.music_artist ?? 'Unknown',
        reelId: reel.id,
        platform: reel.platform,
      });
      continue;
    }

    // YouTube audio detection (from description or metadata)
    if (data.audio_track) {
      const parts = data.audio_track.split(' - ');
      signals.push({
        song: parts[0]?.trim() ?? data.audio_track,
        artist: parts[1]?.trim() ?? 'Unknown',
        reelId: reel.id,
        platform: reel.platform,
      });
      continue;
    }

    // Fallback: check hashtags for music-related signals
    if (data.hashtags) {
      const musicHashtags = (data.hashtags as string[]).filter(
        (tag) => tag.toLowerCase().includes('song') ||
                 tag.toLowerCase().includes('music') ||
                 tag.toLowerCase().includes('track')
      );
      // These are weaker signals, skip unless no other audio data
    }
  }

  return signals;
};

// Deduplicate by song+artist (case-insensitive)
const deduplicateSignals = (signals: AudioSignal[]): AudioSignal[] => {
  const seen = new Set<string>();
  return signals.filter((s) => {
    const key = `${s.song.toLowerCase()}|${s.artist.toLowerCase()}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};
```

### Claude Prompt for Playlist Curation

When there are enough tracks (5+), use Claude to curate the order and generate a playlist title:

```typescript
const buildPlaylistPrompt = (
  boardName: string,
  identityLabel: string,
  tracks: AudioSignal[],
  tasteProfile: any
): string => {
  const trackList = tracks
    .map((t, i) => `${i + 1}. "${t.song}" by ${t.artist} (from ${t.platform})`)
    .join('\n');

  return `You are a music curator building a playlist for a friend group called "${boardName}" (aka "${identityLabel}"). These are the songs that appeared in the reels and videos they share with each other -- it's their group's musical DNA.

DETECTED TRACKS:
${trackList}

GROUP TASTE PROFILE:
- Aesthetic: ${tasteProfile?.aesthetic ?? 'unknown'}
- Vibe: ${tasteProfile?.humour_style ?? 'unknown'}
- Activities they're into: ${JSON.stringify(tasteProfile?.activity_types ?? [])}

TASKS:
1. Generate a playlist TITLE that captures the group's musical vibe (max 5 words, should feel like a Spotify playlist name that would make them laugh or nod).

2. REORDER the tracks for optimal listening flow:
   - Open with energy
   - Build and vary the mood
   - End with something memorable
   - If genres clash, create intentional transitions

3. If any tracks seem like obvious memes/jokes (e.g., a song used ironically in TikTok), keep them but place them as palette cleansers between serious tracks.

4. Add UP TO 5 bonus track recommendations that would fit this group's vibe based on the detected tracks. Mark these clearly as "[BONUS]".

RESPONSE FORMAT (use this exact format):
TITLE: [playlist title]

TRACKLIST:
1. [Song] - [Artist]
2. [Song] - [Artist]
...
[BONUS]
N. [Song] - [Artist] (Recommended because: [brief reason])

VIBE SUMMARY: [One sentence describing the playlist's energy]`;
};
```

### Edge Function: generate-playlist

```typescript
// supabase/functions/generate-playlist/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CLAUDE_API_KEY = Deno.env.get('CLAUDE_API_KEY')!;
const CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { board_id } = await req.json();

  if (!board_id) {
    return new Response(JSON.stringify({ error: 'board_id required' }), { status: 400 });
  }

  // Fetch board and taste profile
  const { data: board } = await supabase
    .from('boards')
    .select('name')
    .eq('id', board_id)
    .single();

  const { data: tasteProfile } = await supabase
    .from('taste_profiles')
    .select('profile_data, identity_label')
    .eq('board_id', board_id)
    .single();

  // Fetch all reels with extraction data
  const { data: reels } = await supabase
    .from('reels')
    .select('id, url, platform, extraction_data')
    .eq('board_id', board_id)
    .not('extraction_data', 'is', null);

  // Extract audio signals
  const rawSignals = extractAudioSignals(reels ?? []);
  const signals = deduplicateSignals(rawSignals);

  if (signals.length === 0) {
    return new Response(
      JSON.stringify({ error: 'No music signals detected. Share some reels with music!' }),
      { status: 400 }
    );
  }

  // If fewer than 5 tracks, return raw list without Claude curation
  if (signals.length < 5) {
    const playlist = {
      title: `${board?.name ?? 'Group'} Mix`,
      generated_at: new Date().toISOString(),
      tracks: signals.map((s) => ({
        song: s.song,
        artist: s.artist,
        source_reel_id: s.reelId,
        is_bonus: false,
      })),
      vibe_summary: 'A growing collection from your shared reels.',
    };

    await savePlaylist(supabase, board_id, playlist, tasteProfile);

    return new Response(JSON.stringify(playlist), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Use Claude to curate the playlist
  const prompt = buildPlaylistPrompt(
    board?.name ?? 'This Group',
    tasteProfile?.identity_label ?? 'Unknown Identity',
    signals,
    tasteProfile?.profile_data
  );

  const claudeResponse = await fetch(CLAUDE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': CLAUDE_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 600,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!claudeResponse.ok) {
    // Retry once
    const retryResponse = await fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 600,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!retryResponse.ok) {
      // Fallback: return raw list
      const fallbackPlaylist = {
        title: `${board?.name ?? 'Group'} Mix`,
        generated_at: new Date().toISOString(),
        tracks: signals.map((s) => ({
          song: s.song,
          artist: s.artist,
          source_reel_id: s.reelId,
          is_bonus: false,
        })),
        vibe_summary: 'Tracks from your shared reels.',
      };

      await savePlaylist(supabase, board_id, fallbackPlaylist, tasteProfile);
      return new Response(JSON.stringify(fallbackPlaylist), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const retryData = await retryResponse.json();
    const parsed = parsePlaylistResponse(retryData.content[0].text, signals);
    await savePlaylist(supabase, board_id, parsed, tasteProfile);
    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const claudeData = await claudeResponse.json();
  const parsed = parsePlaylistResponse(claudeData.content[0].text, signals);

  await savePlaylist(supabase, board_id, parsed, tasteProfile);

  return new Response(JSON.stringify(parsed), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
});

function parsePlaylistResponse(text: string, originalSignals: AudioSignal[]) {
  // Parse title
  const titleMatch = text.match(/TITLE:\s*(.*)/);
  const title = titleMatch?.[1]?.trim() ?? 'Group Playlist';

  // Parse tracklist
  const tracklistMatch = text.match(/TRACKLIST:\s*([\s\S]*?)(?=\n\s*VIBE SUMMARY|$)/);
  const trackLines = tracklistMatch?.[1]?.split('\n').filter((l) => l.trim()) ?? [];

  const tracks = trackLines.map((line) => {
    const isBonus = line.includes('[BONUS]');
    const cleaned = line.replace(/^\d+\.\s*/, '').replace('[BONUS]', '').trim();
    const parts = cleaned.split(' - ');
    const song = parts[0]?.trim() ?? cleaned;
    const artistPart = parts[1]?.trim() ?? 'Unknown';
    // Strip recommendation reason if present
    const artist = artistPart.replace(/\s*\(Recommended because:.*\)/, '').trim();

    // Try to match back to original signal for source reel ID
    const matchedSignal = originalSignals.find(
      (s) => s.song.toLowerCase() === song.toLowerCase()
    );

    return {
      song,
      artist,
      source_reel_id: matchedSignal?.reelId ?? null,
      is_bonus: isBonus,
    };
  });

  // Parse vibe summary
  const vibeMatch = text.match(/VIBE SUMMARY:\s*(.*)/);
  const vibeSummary = vibeMatch?.[1]?.trim() ?? '';

  return {
    title,
    generated_at: new Date().toISOString(),
    tracks,
    vibe_summary: vibeSummary,
    raw_text: text,
  };
}

async function savePlaylist(supabase: any, boardId: string, playlist: any, tasteProfile: any) {
  await supabase
    .from('taste_profiles')
    .update({
      profile_data: {
        ...(tasteProfile?.profile_data as object),
        playlist,
      },
    })
    .eq('board_id', boardId);
}

// Include utility functions (extractAudioSignals, deduplicateSignals, buildPlaylistPrompt)
// in the same file -- full implementations shown above in Implementation Notes
function extractAudioSignals(reels: any[]): AudioSignal[] {
  const signals: AudioSignal[] = [];
  for (const reel of reels) {
    const data = reel.extraction_data as any;
    if (!data) continue;
    if (data.audio_name || data.audio_track) {
      signals.push({
        song: data.audio_name ?? data.audio_track ?? '',
        artist: data.audio_artist ?? 'Unknown',
        reelId: reel.id,
        platform: reel.platform,
      });
    } else if (data.music_name) {
      signals.push({
        song: data.music_name,
        artist: data.music_artist ?? 'Unknown',
        reelId: reel.id,
        platform: reel.platform,
      });
    }
  }
  return signals;
}

interface AudioSignal {
  song: string;
  artist: string;
  reelId: string;
  platform: string;
}

function deduplicateSignals(signals: AudioSignal[]): AudioSignal[] {
  const seen = new Set<string>();
  return signals.filter((s) => {
    const key = `${s.song.toLowerCase()}|${s.artist.toLowerCase()}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function buildPlaylistPrompt(
  boardName: string,
  identityLabel: string,
  tracks: AudioSignal[],
  tasteProfile: any
): string {
  const trackList = tracks
    .map((t, i) => `${i + 1}. "${t.song}" by ${t.artist} (from ${t.platform})`)
    .join('\n');

  return `You are a music curator building a playlist for a friend group called "${boardName}" (aka "${identityLabel}"). These are the songs that appeared in the reels and videos they share with each other -- it's their group's musical DNA.

DETECTED TRACKS:
${trackList}

GROUP TASTE PROFILE:
- Aesthetic: ${tasteProfile?.aesthetic ?? 'unknown'}
- Vibe: ${tasteProfile?.humour_style ?? 'unknown'}
- Activities they're into: ${JSON.stringify(tasteProfile?.activity_types ?? [])}

TASKS:
1. Generate a playlist TITLE that captures the group's musical vibe (max 5 words, should feel like a Spotify playlist name that would make them laugh or nod).

2. REORDER the tracks for optimal listening flow:
   - Open with energy
   - Build and vary the mood
   - End with something memorable
   - If genres clash, create intentional transitions

3. If any tracks seem like obvious memes/jokes (e.g., a song used ironically in TikTok), keep them but place them as palette cleansers between serious tracks.

4. Add UP TO 5 bonus track recommendations that would fit this group's vibe based on the detected tracks. Mark these clearly as "[BONUS]".

RESPONSE FORMAT (use this exact format):
TITLE: [playlist title]

TRACKLIST:
1. [Song] - [Artist]
2. [Song] - [Artist]
...
[BONUS]
N. [Song] - [Artist] (Recommended because: [brief reason])

VIBE SUMMARY: [One sentence describing the playlist's energy]`;
}
```

### Playlist Screen Component

```typescript
// components/shared/PlaylistCard.tsx
import { View, Text, TouchableOpacity, FlatList, Linking, Share, StyleSheet } from 'react-native';

interface Track {
  song: string;
  artist: string;
  source_reel_id: string | null;
  is_bonus: boolean;
}

interface PlaylistData {
  title: string;
  generated_at: string;
  tracks: Track[];
  vibe_summary: string;
}

const PlaylistCard = ({ playlist }: { playlist: PlaylistData }) => {
  const handleCopyPlaylist = async () => {
    const text = playlist.tracks
      .map((t, i) => `${i + 1}. ${t.song} - ${t.artist}${t.is_bonus ? ' [Bonus]' : ''}`)
      .join('\n');

    const fullText = `${playlist.title}\n\n${text}\n\n${playlist.vibe_summary}`;

    await Share.share({ message: fullText });
  };

  const handleOpenSpotify = () => {
    // Open Spotify search with the first track to seed discovery
    const firstTrack = playlist.tracks[0];
    if (firstTrack) {
      const searchQuery = encodeURIComponent(`${firstTrack.song} ${firstTrack.artist}`);
      Linking.openURL(`spotify:search:${searchQuery}`).catch(() => {
        // Fallback to web search
        Linking.openURL(`https://open.spotify.com/search/${searchQuery}`);
      });
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>{playlist.title}</Text>
        <Text style={styles.trackCount}>{playlist.tracks.length} tracks</Text>
        <Text style={styles.vibeSummary}>{playlist.vibe_summary}</Text>
      </View>

      {/* Track list */}
      <FlatList
        data={playlist.tracks}
        keyExtractor={(item, index) => `${item.song}-${index}`}
        renderItem={({ item, index }) => (
          <TrackItem track={item} index={index + 1} />
        )}
        scrollEnabled={false}
      />

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity style={styles.spotifyButton} onPress={handleOpenSpotify}>
          <Text style={styles.spotifyText}>Open in Spotify</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.copyButton} onPress={handleCopyPlaylist}>
          <Text style={styles.copyText}>Share Playlist</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const TrackItem = ({ track, index }: { track: Track; index: number }) => (
  <View style={[styles.trackRow, track.is_bonus && styles.bonusTrack]}>
    <Text style={styles.trackNumber}>{index}</Text>
    <View style={styles.trackInfo}>
      <Text style={styles.songName}>
        {track.song}
        {track.is_bonus && <Text style={styles.bonusBadge}> BONUS</Text>}
      </Text>
      <Text style={styles.artistName}>{track.artist}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: { margin: 16 },
  header: {
    backgroundColor: '#1DB954', // Spotify green
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  trackCount: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 8,
  },
  vibeSummary: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.9)',
    fontStyle: 'italic',
  },
  trackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    backgroundColor: '#fff',
  },
  bonusTrack: {
    backgroundColor: '#F0FDF4',
  },
  trackNumber: {
    width: 28,
    fontSize: 14,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  trackInfo: { flex: 1 },
  songName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111827',
  },
  bonusBadge: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1DB954',
  },
  artistName: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
    justifyContent: 'center',
  },
  spotifyButton: {
    backgroundColor: '#1DB954',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
  },
  spotifyText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
  },
  copyButton: {
    backgroundColor: '#E5E7EB',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
  },
  copyText: {
    color: '#374151',
    fontWeight: '600',
    fontSize: 15,
  },
});
```

### Spotify Integration (Lightweight)

For the hackathon, full Spotify API integration (creating actual playlists) is out of scope. Instead, the "Open in Spotify" button uses Spotify's URI scheme to search:

```typescript
// Open Spotify app to search for a specific track
Linking.openURL(`spotify:search:${encodeURIComponent('song artist')}`);

// Fallback to Spotify web
Linking.openURL(`https://open.spotify.com/search/${encodeURIComponent('song artist')}`);
```

For a more complete integration post-hackathon, use the Spotify Web API to create an actual playlist:
- Authenticate via Spotify OAuth
- `POST /v1/users/{user_id}/playlists`
- `POST /v1/playlists/{playlist_id}/tracks` with track URIs

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `supabase/functions/generate-playlist/index.ts` | Edge Function: extracts audio signals from reels, calls Claude for curation, saves playlist |
| `components/shared/PlaylistCard.tsx` | Styled playlist display with track list, Spotify button, and share button |
| `lib/hooks/use-playlist.ts` | Hook for generating, fetching, and sharing the playlist |
| `app/playlist.tsx` | Dedicated screen for viewing the group playlist |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/board/[id].tsx` | Add "Group Playlist" section/link on board detail screen |

## Definition of Done

- [ ] Edge Function `generate-playlist` deployed and callable
- [ ] Audio signals extracted from all reels' `extraction_data` (TikTok audio_name, Instagram music_name, YouTube audio_track)
- [ ] Duplicate tracks deduplicated (case-insensitive match on song+artist)
- [ ] For 5+ tracks, Claude curates the order and generates a playlist title and up to 5 bonus recommendations
- [ ] For fewer than 5 tracks, raw list returned without AI curation
- [ ] Playlist stored in `taste_profiles.profile_data.playlist`
- [ ] Playlist displayed with song name, artist, and track number
- [ ] Bonus tracks clearly marked as "[BONUS]"
- [ ] "Open in Spotify" button launches Spotify search (URI scheme with web fallback)
- [ ] "Share Playlist" button copies/shares the full playlist as text
- [ ] Empty state when no audio signals detected in any reels
- [ ] "Refresh Playlist" regenerates with any new tracks added since last generation
- [ ] Retry logic on Claude API failure; fallback to raw list if curation fails
- [ ] Vibe summary displayed below playlist title
