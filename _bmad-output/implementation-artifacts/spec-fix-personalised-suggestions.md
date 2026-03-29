---
title: 'Fix personalised suggestions — stuck loading'
type: 'bugfix'
created: '2026-03-29'
status: 'done'
baseline_commit: '0544e04'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The "Recommended for you" section is stuck on "Generating personalised suggestions..." because: (a) the frontend never sends liked/disliked reel IDs to the backend — the backend queries a `swipes` table that doesn't exist, so all reels are treated as neutral; (b) `_load_gemini_api_key()` only reads from a local `.env` file, which fails on Vercel; (c) the UI shows the loading text even after generation fails.

**Approach:** Pass liked/disliked reel IDs from the frontend in the generate request. Update the backend to use these instead of querying the missing `swipes` table. Fix the Gemini key loader to fall back to `os.environ`. Fix UI to show error/retry state.

## Boundaries & Constraints

**Always:** Keep the existing `SuggestionsService` architecture. Use the same Gemini prompt structure. Maintain backward compatibility (empty `liked_reel_ids` = all reels neutral).

**Ask First:** Creating the `swipes` table for persistent swipe storage (out of scope for this fix — swipe data is passed per-request instead).

**Never:** Change the AI model or prompt logic. Add new dependencies. Refactor the suggestion display component beyond fixing the stuck state.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — 2 liked reels | User swipes right on 2 reels, all swiped | Suggestion generated with liked reels weighted higher | N/A |
| No likes | User skips/dislikes all reels | UI shows "Swipe to unlock activity suggestions" | N/A |
| API error | Gemini key missing or API timeout | UI shows "Couldn't generate — tap to retry" | Catch error, show retry button |
| No reels with extraction data | All reels have null extraction_data | Suggestion still generated from taste profile | Prompt handles empty reel data |

</frozen-after-approval>

## Code Map

- `backend/app/schemas/suggestions.py` -- Add `liked_reel_ids` / `disliked_reel_ids` to request schema
- `backend/app/services/suggestions.py` -- Use request-provided IDs instead of `_fetch_swipes()`; fix `_load_gemini_api_key()` to check `os.environ`
- `sendit-app/lib/api/boards.ts` -- Pass liked/disliked reel IDs in the generate request
- `sendit-app/lib/ai/suggestion-engine.ts` -- Accept and forward liked/disliked reel IDs
- `sendit-app/app/(tabs)/flashcards/[category].tsx` -- Pass swiped reel IDs to engine; fix stuck UI text; add retry on error

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/suggestions.py` -- Fix `_load_gemini_api_key()` to check `os.environ.get("GEMINI_API_KEY")` before file read -- production Vercel env vars won't be in a local file
- [x] `backend/app/schemas/suggestions.py` -- Add optional `liked_reel_ids: list[str]` and `disliked_reel_ids: list[str]` fields to `SuggestionsGenerateRequest` -- frontend passes swipe context per-request
- [x] `backend/app/services/suggestions.py` -- Replace `_fetch_swipes()` usage in `generate()` with request-provided IDs; build `swipe_map` from these IDs in `_build_prompt()` -- eliminates dependency on missing `swipes` table
- [x] `sendit-app/lib/ai/suggestion-engine.ts` -- Add `likedReelIds` and `dislikedReelIds` params to `generateSuggestion()` and forward to API call
- [x] `sendit-app/lib/api/boards.ts` -- Add `liked_reel_ids` and `disliked_reel_ids` to the POST payload in `generateSuggestions()`
- [x] `sendit-app/app/(tabs)/flashcards/[category].tsx` -- Pass swiped reel IDs when calling `generateSuggestion()`; fix the fallback text to show "Couldn't load suggestions" + retry; add `suggestionError` state

**Acceptance Criteria:**
- Given a user has liked 2+ reels, when all reels are swiped, then a personalised suggestion appears within 30s referencing the liked content
- Given generation fails, when the user sees the error state, then tapping retries the generation
- Given no reels are liked, when the user views the feed, then it shows "Swipe to unlock activity suggestions"

## Verification

**Manual checks (if no CLI):**
- Open the Vibes flashcards screen, swipe right on 2 reels, confirm suggestion loads
- Kill network, confirm error/retry UI appears

## Suggested Review Order

**Gemini API key fix**

- Check env var first, file fallback for local dev only
  [`suggestions.py:25`](../../backend/app/services/suggestions.py#L25)

**Swipe data pipeline (backend → frontend)**

- New request fields accept liked/disliked reel IDs from client
  [`suggestions.py:13`](../../backend/app/schemas/suggestions.py#L13)

- Build swipe map from request IDs instead of removed `_fetch_swipes()`
  [`suggestions.py:68`](../../backend/app/services/suggestions.py#L68)

- Forward IDs in the POST body to backend
  [`boards.ts:133`](../../sendit-app/lib/api/boards.ts#L133)

- Engine accepts and passes through liked/disliked ID params
  [`suggestion-engine.ts:16`](../../sendit-app/lib/ai/suggestion-engine.ts#L16)

**UI trigger + error/retry**

- `triggerSuggestion` callback collects swiped IDs from local state
  [`[category].tsx:103`](../../sendit-app/app/(tabs)/flashcards/[category].tsx#L103)

- Strips 'uncategorised' to avoid Pydantic 422 (review patch)
  [`[category].tsx:110`](../../sendit-app/app/(tabs)/flashcards/[category].tsx#L110)

- Fixed stuck text + retry button when generation fails
  [`[category].tsx:247`](../../sendit-app/app/(tabs)/flashcards/[category].tsx#L247)
