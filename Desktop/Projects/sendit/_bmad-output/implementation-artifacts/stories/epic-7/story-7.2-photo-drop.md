# Story 7.2: Photo Drop

## Description

As a member who attended an event,
I want to upload photos after the event within a 48-hour window,
So that our group's memories are collected in one place.

## Status

- **Epic:** Memory & Timeline
- **Priority:** P2
- **Branch:** `feature/memory-timeline`
- **Assignee:** Stretch

## Acceptance Criteria

**Given** an event page exists and the current time is within 48 hours of the event's `created_at`
**When** the user views the event page
**Then** an "Add Photos" button is visible and enabled

**Given** the user taps "Add Photos"
**When** the image picker opens via expo-image-picker
**Then** the user can select one or multiple photos from their library
**And** selected photos are uploaded to Supabase Storage in the "event-photos" bucket
**And** the photo URLs are appended to the `events.photos` jsonb array
**And** a progress indicator shows during upload

**Given** photos have been uploaded to an event
**When** any board member views the event page
**Then** all photos are displayed in a grid layout
**And** tapping a photo opens it in a full-screen viewer

**Given** the current time is MORE than 48 hours after the event's `created_at`
**When** the user views the event page
**Then** the "Add Photos" button is hidden or disabled
**And** a message reads "Photo upload window has closed"
**And** existing photos remain visible

**Given** multiple members upload photos
**When** photos are added
**Then** all members' photos appear in a single unified grid on the event page
**And** each photo is attributed to the member who uploaded it

## Technical Context

### Relevant Schema

```sql
events (
  id uuid PK,
  suggestion_id uuid FK,
  board_id uuid FK,
  photos jsonb DEFAULT '[]',   -- Array of { url: string, member_id: string, uploaded_at: string }
  memories jsonb DEFAULT '[]',
  narrative text,
  created_at timestamptz
)
```

**Example photos value:**

```json
[
  {
    "url": "https://ubhbeqnagxbuoikzftht.supabase.co/storage/v1/object/public/event-photos/board123/event456/photo1.jpg",
    "member_id": "member-uuid-1",
    "uploaded_at": "2026-03-29T14:22:00Z"
  },
  {
    "url": "https://ubhbeqnagxbuoikzftht.supabase.co/storage/v1/object/public/event-photos/board123/event456/photo2.jpg",
    "member_id": "member-uuid-2",
    "uploaded_at": "2026-03-29T16:45:00Z"
  }
]
```

**Supabase Storage Bucket:** `event-photos`
- Public read access
- Authenticated write access
- File path format: `{board_id}/{event_id}/{member_id}_{timestamp}.jpg`

### Architecture References

- **Screen:** `app/(tabs)/event/[id].tsx` -- Photo section of the event page
- **Components:** `components/memory/PhotoGrid.tsx`, `components/memory/PhotoViewer.tsx`, `components/memory/AddPhotoButton.tsx`
- **Storage:** Supabase Storage bucket `event-photos`
- **Permissions:** Camera + photo library via expo-image-picker
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

### Dependencies

- **Requires:** Story 7.1 (event page exists)
- **Requires:** `expo-image-picker` installed
- **Requires:** Supabase Storage bucket `event-photos` created
- **Downstream:** Story 7.4 (AI narrative uses photo URLs)

## Implementation Notes

### 48-Hour Window Check

```typescript
const isPhotoWindowOpen = (eventCreatedAt: string): boolean => {
  const created = new Date(eventCreatedAt);
  const windowEnd = new Date(created.getTime() + 48 * 60 * 60 * 1000);
  return new Date() < windowEnd;
};

const getTimeRemaining = (eventCreatedAt: string): string => {
  const created = new Date(eventCreatedAt);
  const windowEnd = new Date(created.getTime() + 48 * 60 * 60 * 1000);
  const remaining = windowEnd.getTime() - Date.now();

  if (remaining <= 0) return 'Window closed';

  const hours = Math.floor(remaining / (1000 * 60 * 60));
  const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
  return `${hours}h ${minutes}m remaining`;
};
```

### Multi-Photo Selection and Upload

```typescript
import * as ImagePicker from 'expo-image-picker';
import { supabase } from '../supabase';

const pickAndUploadPhotos = async (
  eventId: string,
  boardId: string,
  memberId: string
): Promise<string[]> => {
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('Permission needed', 'Please allow photo library access to upload photos.');
    return [];
  }

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsMultipleSelection: true,
    quality: 0.8,
    selectionLimit: 10, // Max 10 photos at once
  });

  if (result.canceled || !result.assets?.length) return [];

  const uploadedUrls: string[] = [];

  for (const asset of result.assets) {
    const timestamp = Date.now();
    const filePath = `${boardId}/${eventId}/${memberId}_${timestamp}.jpg`;

    const response = await fetch(asset.uri);
    const blob = await response.blob();

    const { error } = await supabase.storage
      .from('event-photos')
      .upload(filePath, blob, {
        contentType: 'image/jpeg',
        upsert: false,
      });

    if (error) {
      console.warn(`Failed to upload photo: ${error.message}`);
      continue;
    }

    const { data: urlData } = supabase.storage
      .from('event-photos')
      .getPublicUrl(filePath);

    uploadedUrls.push(urlData.publicUrl);
  }

  return uploadedUrls;
};
```

### Appending Photo URLs to Event

Since `photos` is a jsonb array, use a Supabase RPC or fetch-modify-update pattern:

```typescript
const appendPhotosToEvent = async (
  eventId: string,
  memberId: string,
  photoUrls: string[]
) => {
  // Fetch current photos
  const { data: event } = await supabase
    .from('events')
    .select('photos')
    .eq('id', eventId)
    .single();

  const currentPhotos = (event?.photos as any[]) ?? [];

  const newPhotos = photoUrls.map((url) => ({
    url,
    member_id: memberId,
    uploaded_at: new Date().toISOString(),
  }));

  const updatedPhotos = [...currentPhotos, ...newPhotos];

  const { error } = await supabase
    .from('events')
    .update({ photos: updatedPhotos })
    .eq('id', eventId);

  if (error) throw error;
};
```

**Note on Race Conditions:** If multiple members upload simultaneously, one update could overwrite another. For the hackathon, this is acceptable. In production, use a Supabase RPC with `jsonb_concat` or a server-side function:

```sql
-- Production-safe RPC
CREATE OR REPLACE FUNCTION append_event_photos(
  p_event_id uuid,
  p_new_photos jsonb
) RETURNS void AS $$
BEGIN
  UPDATE events
  SET photos = photos || p_new_photos
  WHERE id = p_event_id;
END;
$$ LANGUAGE plpgsql;
```

### Photo Grid Component

```typescript
// components/memory/PhotoGrid.tsx
import { Image, TouchableOpacity, FlatList, Dimensions } from 'react-native';

interface PhotoItem {
  url: string;
  member_id: string;
  uploaded_at: string;
}

const SCREEN_WIDTH = Dimensions.get('window').width;
const PHOTO_SIZE = (SCREEN_WIDTH - 48) / 3; // 3 columns with spacing

const PhotoGrid = ({
  photos,
  onPhotoPress,
}: {
  photos: PhotoItem[];
  onPhotoPress: (index: number) => void;
}) => (
  <FlatList
    data={photos}
    numColumns={3}
    keyExtractor={(item, index) => `${item.url}-${index}`}
    renderItem={({ item, index }) => (
      <TouchableOpacity onPress={() => onPhotoPress(index)}>
        <Image
          source={{ uri: item.url }}
          style={{ width: PHOTO_SIZE, height: PHOTO_SIZE, margin: 2, borderRadius: 4 }}
        />
      </TouchableOpacity>
    )}
    scrollEnabled={false} // Nested in ScrollView
  />
);
```

### Storage Bucket Setup

```sql
INSERT INTO storage.buckets (id, name, public) VALUES ('event-photos', 'event-photos', true);

CREATE POLICY "Members can upload event photos"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'event-photos');

CREATE POLICY "Anyone can view event photos"
ON storage.objects FOR SELECT
USING (bucket_id = 'event-photos');
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/memory/PhotoGrid.tsx` | 3-column grid layout for event photos |
| `components/memory/PhotoViewer.tsx` | Full-screen photo viewer modal with swipe between photos |
| `components/memory/AddPhotoButton.tsx` | Button that triggers image picker, shows upload progress, handles 48hr window |
| `lib/hooks/use-photo-upload.ts` | Hook encapsulating multi-photo pick, upload, and append logic |

### Modify

| File | Change |
|------|--------|
| `components/memory/EventPage.tsx` | Integrate PhotoGrid and AddPhotoButton into event page layout |
| `lib/hooks/use-event.ts` | Subscribe to Realtime updates on the event's photos field |

## Definition of Done

- [ ] "Add Photos" button visible on event page within 48 hours of event creation
- [ ] Image picker allows multi-photo selection (up to 10 at once)
- [ ] Photos uploaded to Supabase Storage `event-photos` bucket
- [ ] Photo URLs appended to `events.photos` jsonb array with member_id and timestamp
- [ ] Photo grid displays all uploaded photos in a 3-column layout
- [ ] Tapping a photo opens it in a full-screen viewer
- [ ] "Add Photos" button disabled/hidden after 48-hour window closes
- [ ] Time remaining indicator shown while window is open (e.g., "12h 30m remaining")
- [ ] Upload progress indicator shown during multi-photo upload
- [ ] Multiple members' photos merge into a single unified grid
- [ ] Error handling: failed uploads skip gracefully, successful ones still saved
- [ ] Image compression applied (quality 0.8) to manage storage usage
