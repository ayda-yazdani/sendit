---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
workflowType: 'architecture'
project_name: 'sendit'
user_name: 'Ayday'
date: '2026-03-28'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
54 FRs across 9 capability areas: Board Management (7), Content Input (5), AI Content Processing (7), Group Taste Intelligence (6), Plan Suggestions (6), Commitment & Social Pressure (7), Memory & Timeline (8), Authentication & Identity (5), Shared Objects — Stretch (3). The AI Content Processing and Group Taste Intelligence areas are the most architecturally complex — they require multi-step AI pipelines, external API orchestration, and real-time state management.

**Non-Functional Requirements:**
18 NFRs driving architecture: sub-3-second AI extraction latency (NFR1), sub-1-second real-time propagation (NFR2), calendar data privacy (NFR6-7), Supabase RLS for board-scoped access control (NFR10), graceful degradation on API failure (NFR12), extraction caching (NFR15), and WebSocket persistence with auto-reconnect (NFR16-17).

**Scale & Complexity:**

- Primary domain: Full-stack mobile (React Native + Supabase + AI services)
- Complexity level: Medium-High
- Estimated architectural components: ~12 (app shell, board module, content input, extraction pipeline, classification engine, taste engine, suggestion engine, commitment module, memory module, auth module, notification service, real-time layer)

### Technical Constraints & Dependencies

- **React Native + Expo** — managed workflow preferred, but share sheet extension may force config plugin or eject
- **Supabase** — PostgreSQL for relational data, Realtime for WebSocket sync, Edge Functions for server-side logic, Storage for images
- **Claude API** — single AI provider for extraction classification, taste profiling, suggestion generation, and narrative writing
- **YouTube Data API v3** — primary extraction source; Instagram and TikTok via third-party scraping APIs
- **Google OAuth + Calendar API** — progressive auth, free/busy only
- **24-hour hackathon** — architecture must be simple enough for 4 developers to work independently without blocking each other

### Cross-Cutting Concerns

1. **Real-time synchronization** — affects boards, reels, commitments, taste profiles. Supabase Realtime subscriptions must be managed consistently across all screens.
2. **AI integration pattern** — 6 of 9 capability areas call Claude API. Need a consistent AI service layer with structured prompts, response parsing, error handling, and caching.
3. **Authentication state** — two user states (anonymous device session vs Google OAuth) affect what features are available. Must be handled at routing, API, and RLS levels.
4. **Caching strategy** — extraction results (NFR15), taste profiles, and suggestion data should be cached to reduce API calls and improve perceived performance.
5. **Graceful degradation** — each external API can fail independently. Architecture must handle partial failures without crashing the app.

## Starter Template Evaluation

### Primary Technology Domain

React Native mobile app with Expo managed workflow, based on PRD requirements for cross-platform iOS + Android with share sheet integration, real-time sync, and AI pipeline.

### Starter Options Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| `create-expo-app --template tabs` | Expo Router, tab navigation, TypeScript, fast setup | Basic — no Supabase, no state management | **Selected** — add what we need |
| `create-expo-app --template blank-typescript` | Minimal, full control | Too bare — have to build navigation from scratch | Too slow for hackathon |
| Custom Expo + Supabase template | Pre-wired auth + database | Not officially maintained, version drift risk | Unnecessary complexity |

### Selected Starter: Expo with Tabs Template

**Rationale:** Fastest path to a working app shell with file-based routing (Expo Router). Tab navigation matches our screen structure (Boards, Board Detail, Suggestions, Profile). TypeScript included. We add Supabase client, AI service layer, and state management ourselves — minimal additions, maximum control.

**Initialization Command:**

```bash
npx create-expo-app@latest sendit-app --template tabs
cd sendit-app
npx expo install @supabase/supabase-js expo-secure-store expo-sharing expo-linking expo-image-picker expo-notifications expo-auth-session expo-crypto
```

**Architectural Decisions Provided by Starter:**

- **Language & Runtime:** TypeScript, React Native 0.76+, Expo SDK 52+
- **Routing:** Expo Router (file-based routing, nested layouts)
- **Styling:** React Native StyleSheet (can add NativeWind/Tailwind if desired)
- **Build Tooling:** Expo CLI, Metro bundler, EAS Build for native builds
- **Testing:** Jest pre-configured
- **Code Organization:** `app/` directory for routes, `components/` for shared components
- **Development Experience:** Expo Go for rapid dev, hot reload, OTA updates

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
All 5 decisions below are critical — teammates are blocked without them.

**Deferred Decisions (Post-Hackathon):**
CI/CD pipeline, monitoring/logging, scaling strategy, testing infrastructure beyond Jest defaults.

### Data Architecture

- **Database:** Supabase PostgreSQL (decided in PRD)
- **Real-time:** Supabase Realtime subscriptions on boards, reels, commitments tables
- **Caching:** Extraction results cached in Supabase — re-submitting same URL returns cached row. Taste profiles cached in Zustand store with invalidation on new reel.
- **Migration:** SQL schema applied directly via Supabase dashboard or CLI for hackathon speed

**Schema:**

```sql
boards          (id uuid PK, name text, join_code text unique, created_at timestamptz)
members         (id uuid PK, board_id uuid FK, display_name text, device_id text, google_id text nullable, avatar_url text, push_token text)
reels           (id uuid PK, board_id uuid FK, added_by uuid FK, url text unique, platform text, extraction_data jsonb, classification text, created_at timestamptz)
taste_profiles  (id uuid PK, board_id uuid FK unique, profile_data jsonb, identity_label text, updated_at timestamptz)
suggestions     (id uuid PK, board_id uuid FK, suggestion_data jsonb, status text default 'active', created_at timestamptz)
commitments     (id uuid PK, suggestion_id uuid FK, member_id uuid FK, status text check (status in ('in','maybe','out')), receipt_url text, updated_at timestamptz)
events          (id uuid PK, suggestion_id uuid FK, board_id uuid FK, photos jsonb, memories jsonb, narrative text, created_at timestamptz)
calendar_masks  (id uuid PK, member_id uuid FK, busy_slots jsonb, synced_at timestamptz)
```

**RLS Policies:** Members can only read/write data for boards they belong to. All tables enforce board-scoped access via `board_id` membership check.

### Authentication & Security

- **Anonymous sessions:** Device ID generated on first launch, stored in Expo SecureStore. Used as `device_id` in members table.
- **Progressive auth:** Google OAuth via `expo-auth-session` when user wants calendar integration. Updates `google_id` on existing member row.
- **API key security:** All sensitive keys (Claude API, YouTube API, Google Client Secret) stored as Supabase secrets, accessed only by Edge Functions. Client app only has `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- **RLS:** Supabase Row Level Security enforces board membership on all queries.

### API & Communication Patterns

- **Client → Supabase:** Direct Supabase client (`@supabase/supabase-js`) for CRUD and Realtime subscriptions.
- **AI Pipeline:** Client calls Supabase Edge Functions → Edge Functions call Claude API, YouTube API, Google Places API → return structured JSON to client.
- **Edge Functions:**
  - `extract` — accepts URL, detects platform, fetches metadata, calls Claude for structured extraction
  - `classify` — accepts extraction data, returns one of 5 content types
  - `suggest` — accepts board_id, reads taste profile + calendar masks, calls Claude for plan suggestion
  - `taste-update` — accepts board_id, reads all reels, calls Claude to regenerate taste profile
- **Error handling:** Edge Functions return structured error responses `{ error: string, fallback: boolean }`. Client shows user-friendly message and uses fallback data if available.

### Frontend Architecture

- **State Management:** Zustand — lightweight, no boilerplate, works well with Supabase Realtime subscriptions. One store per domain (board-store, auth-store, taste-store).
- **Component Architecture:** Feature-based folders (`components/board/`, `components/extraction/`, `components/commitment/`, `components/shared/`).
- **Routing:** Expo Router file-based routing with tab layout. Dynamic routes for board detail `board/[id]` and suggestion detail `suggestion/[id]`.
- **Real-time:** Custom `useRealtime` hook wrapping Supabase subscription lifecycle. Used in board screen for live reel/commitment updates.

**Folder Structure:**

```
app/                        # Expo Router screens
  (tabs)/
    index.tsx               # Board list
    board/[id].tsx          # Board detail (reels + taste profile)
    suggestion/[id].tsx     # Suggestion + commitment board
    profile.tsx             # Settings + calendar connect
  join/[code].tsx           # Deep link board join
lib/
  supabase.ts              # Supabase client init
  ai/
    extraction.ts           # Call extract Edge Function
    classification.ts       # Call classify Edge Function
    taste-engine.ts         # Call taste-update Edge Function
    suggestion-engine.ts    # Call suggest Edge Function
  stores/
    board-store.ts          # Board list + active board state
    auth-store.ts           # Device session + Google OAuth state
    taste-store.ts          # Taste profile + identity label
  hooks/
    use-realtime.ts         # Supabase Realtime subscription hook
    use-board.ts            # Board data + members hook
    use-auth.ts             # Auth state + calendar hook
components/
  board/                    # Board list, board card, member avatars
  extraction/               # Extraction card, classification badge
  commitment/               # Vote buttons, tally, receipt wall
  suggestion/               # Suggestion card, reasoning display
  memory/                   # Event page, photo grid, timeline
  shared/                   # Button, Input, Modal, Loading
supabase/
  functions/                # Edge Functions source
    extract/index.ts
    classify/index.ts
    suggest/index.ts
    taste-update/index.ts
  migrations/               # SQL schema files
```

### Infrastructure & Deployment

- **Hosting:** Supabase handles all backend (database, real-time, edge functions, storage). No separate server needed.
- **Mobile builds:** Expo Go for development. EAS Build if native share sheet extension is needed.
- **Environment config:** `.env` with `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY`. All other secrets in Supabase Edge Function secrets.
- **Monitoring:** Supabase dashboard for database and edge function logs. Console logging in app for hackathon.

### Decision Impact Analysis

**Implementation Sequence:**
1. Supabase project + schema + RLS policies (Person B — first, unblocks everyone)
2. Expo project scaffold + folder structure + Supabase client init (Person A — parallel with B)
3. Edge Functions for extraction + classification (Person C — needs Supabase from B)
4. Zustand stores + Realtime hooks (Person A — after scaffold)
5. AI taste engine + suggestion engine (Person D — after Edge Functions pattern established)
6. Screen UI integration (All — after stores and Edge Functions exist)

**Cross-Component Dependencies:**
- All screens depend on Zustand stores and Supabase client
- AI service layer (`lib/ai/`) depends on Edge Functions being deployed
- Taste engine depends on extraction + classification being complete
- Suggestion engine depends on taste engine
- Commitment UI depends on Realtime subscriptions working
