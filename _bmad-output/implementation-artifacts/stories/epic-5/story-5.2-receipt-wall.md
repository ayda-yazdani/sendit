# Story 5.2: Receipt Wall

## Description

As a board member,
I want to upload a screenshot of my ticket purchase or booking confirmation,
So that the group can see who's actually bought tickets and who's still just talking.

## Status

- **Epic:** Commitment & Social Pressure
- **Priority:** P1
- **Branch:** `feature/commitment`
- **Assignee:** Person A

## Acceptance Criteria

**Given** a member has voted "In" on a suggestion
**When** they view the suggestion screen
**Then** an "Add Receipt" button is visible next to their commitment status

**Given** the user taps "Add Receipt"
**When** the image picker opens (via expo-image-picker)
**Then** the user can select a photo from their library or take a new photo
**And** the selected image is uploaded to Supabase Storage in the "receipts" bucket
**And** the public URL is saved to the `commitment.receipt_url` field
**And** a loading indicator shows during upload

**Given** one or more members have uploaded receipts
**When** any member views the suggestion screen
**Then** the receipt wall is displayed showing:
  - Green avatar with checkmark overlay for members who have uploaded a receipt
  - Grey avatar (no checkmark) for members who voted "In" but have not uploaded a receipt
  - Members who voted "Maybe" or "Out" are not shown on the receipt wall

**Given** a member taps on a green-checkmark avatar on the receipt wall
**When** the tap is registered
**Then** the receipt image is displayed in a full-screen modal

**Given** a member has already uploaded a receipt
**When** they tap "Add Receipt" again
**Then** the new image replaces the old one (receipt_url is updated)

## Technical Context

### Relevant Schema

```sql
commitments (
  id uuid PK,
  suggestion_id uuid FK,
  member_id uuid FK,
  status text CHECK (status IN ('in', 'maybe', 'out')),
  receipt_url text,           -- URL to uploaded receipt in Supabase Storage
  updated_at timestamptz,
  UNIQUE(suggestion_id, member_id)
)
```

**Supabase Storage Bucket:** `receipts`
- Public read access (any board member can view receipts)
- Authenticated write access (members can upload)
- File path format: `{board_id}/{suggestion_id}/{member_id}.jpg`

### Architecture References

- **Screen:** `app/(tabs)/suggestion/[id].tsx` -- Receipt wall renders below the commitment tally
- **Store:** `lib/stores/commitment-store.ts` -- Extended with receipt upload logic
- **Components:** `components/commitment/ReceiptWall.tsx`, `components/commitment/ReceiptAvatar.tsx`, `components/commitment/ReceiptModal.tsx`
- **Permissions:** Camera + photo library access via expo-image-picker

### Dependencies

- **Requires:** Story 5.1 (voting) -- commitments must exist before receipts can be attached
- **Requires:** Supabase Storage bucket "receipts" created
- **Requires:** `expo-image-picker` installed (included in project dependencies)
- **Supabase Project:** `https://ubhbeqnagxbuoikzftht.supabase.co`

## Implementation Notes

### Image Picker Setup

```typescript
import * as ImagePicker from 'expo-image-picker';

const pickReceiptImage = async (): Promise<string | null> => {
  // Request permission
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('Permission needed', 'Please allow photo library access to upload receipts.');
    return null;
  }

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: true,
    quality: 0.7, // Compress to reduce upload size
    base64: false,
  });

  if (result.canceled) return null;
  return result.assets[0].uri;
};
```

### Upload to Supabase Storage

```typescript
const uploadReceipt = async (
  localUri: string,
  boardId: string,
  suggestionId: string,
  memberId: string
): Promise<string> => {
  const filePath = `${boardId}/${suggestionId}/${memberId}.jpg`;

  // Read file as blob
  const response = await fetch(localUri);
  const blob = await response.blob();

  const { data, error } = await supabase.storage
    .from('receipts')
    .upload(filePath, blob, {
      contentType: 'image/jpeg',
      upsert: true, // Replace existing receipt
    });

  if (error) throw error;

  // Get public URL
  const { data: urlData } = supabase.storage
    .from('receipts')
    .getPublicUrl(filePath);

  return urlData.publicUrl;
};
```

### Save URL to Commitment Row

```typescript
const saveReceiptUrl = async (
  suggestionId: string,
  memberId: string,
  receiptUrl: string
) => {
  const { error } = await supabase
    .from('commitments')
    .update({
      receipt_url: receiptUrl,
      updated_at: new Date().toISOString(),
    })
    .eq('suggestion_id', suggestionId)
    .eq('member_id', memberId);

  if (error) throw error;
};
```

### Receipt Wall Display Logic

```typescript
// Only show members who voted "in" on the receipt wall
const receiptWallMembers = commitments
  .filter((c) => c.status === 'in')
  .map((c) => ({
    memberId: c.member_id,
    displayName: getMemberName(c.member_id),
    avatarUrl: getMemberAvatar(c.member_id),
    hasReceipt: !!c.receipt_url,
    receiptUrl: c.receipt_url,
  }));
```

### Storage Bucket Setup

The "receipts" bucket needs to be created in Supabase with the following policy:

```sql
-- Create the bucket
INSERT INTO storage.buckets (id, name, public) VALUES ('receipts', 'receipts', true);

-- Allow authenticated uploads
CREATE POLICY "Members can upload receipts"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'receipts');

-- Allow public reads
CREATE POLICY "Anyone can view receipts"
ON storage.objects FOR SELECT
USING (bucket_id = 'receipts');

-- Allow members to update their own receipts
CREATE POLICY "Members can update own receipts"
ON storage.objects FOR UPDATE
USING (bucket_id = 'receipts');
```

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `components/commitment/ReceiptWall.tsx` | Grid/row of member avatars showing receipt status (green checkmark vs grey) |
| `components/commitment/ReceiptAvatar.tsx` | Single avatar component with conditional checkmark overlay |
| `components/commitment/ReceiptModal.tsx` | Full-screen modal to view a receipt image |
| `lib/hooks/use-receipt-upload.ts` | Hook encapsulating image pick, upload, and save logic with loading/error state |

### Modify

| File | Change |
|------|--------|
| `app/(tabs)/suggestion/[id].tsx` | Add ReceiptWall below CommitmentTally; add "Add Receipt" button for "in" voters |
| `lib/stores/commitment-store.ts` | Add `uploadReceipt` action and `receiptUploading` loading state |
| `components/commitment/VoteButtons.tsx` | Show "Add Receipt" button when user's status is "in" |

## Definition of Done

- [ ] "Add Receipt" button appears only for members who voted "In"
- [ ] Tapping "Add Receipt" opens the device image picker (library or camera)
- [ ] Selected image uploads to Supabase Storage "receipts" bucket successfully
- [ ] Upload shows a loading indicator during transfer
- [ ] `receipt_url` is saved to the commitment row after upload
- [ ] Receipt wall displays green avatar + checkmark for members with receipts
- [ ] Receipt wall displays grey avatar (no checkmark) for "In" members without receipts
- [ ] Tapping a green-checkmark avatar opens the receipt in a full-screen modal
- [ ] Re-uploading replaces the previous receipt (upsert in Storage)
- [ ] Members who voted "Maybe" or "Out" do not appear on the receipt wall
- [ ] Image compression applied (quality 0.7) to keep uploads under 1MB
- [ ] Error handling: upload failure shows error toast and does not corrupt commitment state
