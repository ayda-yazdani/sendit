---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
  - "_bmad-output/planning-artifacts/epics.md"
---

# UX Design Specification — sendit

**Author:** Ayday
**Date:** 2026-03-28

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

Sendit transforms dead group chat links into real plans. Friends share reel URLs (YouTube, Instagram, TikTok), a 4-layer AI extraction pipeline pulls structured data (venue, price, date, vibe), reels cluster into floating gradient blobs by vibe similarity, the system builds a live group taste profile, generates specific plan suggestions, and uses social commitment mechanics to make plans actually happen.

The UX vision is centred on a **dreamy, floating, cloud-like graph view** — soft gradient blobs with reel cards scattered inside, tappable to expand into swipeable flashcards. The aesthetic is warm, glowing, 3D-feeling, with shadowing and depth — not flat or clinical.

### Target Users

18-30, urban friend groups who constantly share reels in group chats but never follow through. Tech-savvy daily Instagram/TikTok users. The core insight: everyone has a group chat full of dead plans.

### Screen Flow

1. **Auth** — Google OAuth + email/password login/signup
2. **Personality Survey** — 10 tag-picker screens (hobbies, activities, energy level, music vs partying, reading preferences, etc.) building an individual taste embedding vector
3. **Board List** — dark theme card list (ref: reactnativecomponents.com news-tab style, single tab), custom cover images, board name + member count, bottom tab navigation (boards + profile), create board button
4. **Create Board** — name, cover image (custom or random default), generates join code/link
5. **Board Detail (Blob Graph View)** — 5 soft gradient blobs (ref: Korean seasons poster aesthetic — radial gradients, gaussian blur, 50% opacity, overlapping glow), sized by engagement/like count within each cluster, reel cards as rounded rectangles floating at different angles inside each blob with drop shadows, vibe label below each blob, glowing low-opacity URL input at bottom, board management icon (edit name/cover/access, invite via code) in top corner
6. **Flashcard Screen** — tap blob triggers expand animation (blob grows, cards fly out smoothly), transitions to new screen with swipeable flashcards showing extraction data, suggestion + commitment voting lives here per cluster
7. **Profile Tab** — personality profile from survey, cross-group vibe analysis showing how user's personality shifts across different friend groups, taste signal visualization

### Key Design Challenges

- **The blob graph view is the hero moment** — must feel dreamy, floating, alive. Implemented with React Native Skia (radial gradients, blur, blend modes) + d3-force (positioning) + Reanimated (60fps floating animation). Fake 3D depth via scale, blur, and opacity layering.
- **Blob-to-flashcard transition** — needs to feel magical and smooth. Blob expands, cards scatter outward, screen transitions seamlessly.
- **Information density** — extraction cards pack venue/price/date/vibe/tags/booking. Must be scannable as flashcards, not overwhelming.
- **Dark theme with warm palette** — #D8A48F (blush), #94C595 (sage), #982649 (berry), #3C6E71 (teal), #284B63 (navy). Tentative — will be refined with 3D shadowing and specific component references.

### Design Opportunities

- **The blob view is the viral differentiator** — nobody has a vibe-clustered floating graph as their core navigation. This wins "Hacker's Choice."
- **Cross-group personality analysis** in profile — showing how your vibe shifts between friend groups is deeply personal and shareable.
- **Individual taste vector from onboarding** — the app knows you before you even share a reel, making first-session suggestions possible.

### Technical Implementation Notes

- **Logic layer is ~70% complete** — board management, extraction, taste profiling, suggestions, voting all working. UI needs complete rebuild.
- **Component sourcing:** Specific screens reference reactnativecomponents.com (news-tab card list for board list), reactbits.dev (general component/animation library), and the frontend-design skill for non-referenced components.
- **New features needed:** Google OAuth (replacing device-ID auth), personality survey with vector embedding, blob graph visualization.
- **Blob rendering stack:** React Native Skia (GPU gradients/blur) + d3-force (physics layout) + Reanimated (animation) + Gesture Handler (interaction)

### Existing Codebase — Reusable Logic

| Feature | Status | Reuse |
|---------|--------|-------|
| Board create/join/list | Working | Keep stores + Supabase calls, rebuild UI |
| URL input + platform detection | Working | Keep logic, restyle as glowing bottom input |
| Content extraction (edge function) | Working | No changes needed |
| Content classification | Working | No changes needed |
| Taste profile generation (Gemini) | Working | No changes needed |
| Suggestion generation (Claude) | Working | No changes needed |
| In/Maybe/Out voting | Working | Keep logic, rebuild UI for flashcard screen |
| Receipt wall + upload | Working | Keep logic, rebuild UI |
| Real-time subscriptions | Working | No changes needed |
| Database schema (8 tables) | Deployed | No changes needed |
| Google OAuth | Not started | New — needed for auth screen |
| Personality survey + vector | Not started | New — full implementation needed |
| Blob graph visualization | Not started | New — full implementation needed |

### UI Component References

| Screen | Reference | Notes |
|--------|-----------|-------|
| Board List | reactnativecomponents.com/components/tabs/news-tab | Single tab only, extract card list view |
| Blob Graph | Korean seasons gradient poster (attached) | Soft radial gradients, blur, 50% opacity, overlapping |
| Blob 3D Feel | Spline 3D blob tutorial (attached video) | Glassy, distorted, animated — fake with Skia |
| General Components | reactbits.dev | Animations, interactions, effects for all screens |
| Colour Palette | Coolors palette (attached) | #D8A48F, #94C595, #982649, #3C6E71, #284B63 — tentative |

## Core User Experience

### Defining Experience

Sendit's core experience operates on two layers that reinforce each other:

**Passive discovery (the sell):** Opening a board and seeing your friend group's shared content floating as soft gradient blobs, clustered by vibe. This is the first impression — dreamy, alive, unlike anything else. Users drift between clouds, visually absorbing what their group is collectively into. This is what wins over judges and makes other hackathon teams say "I want this."

**Active engagement (the loop):** Tapping a blob, watching cards fly out, and swiping through flashcards. Each card reveals what AI extracted from a reel — venue, price, date, vibe. This is where users spend the most time. The swipe interaction leads naturally to suggestions and commitment voting, closing the loop from "cool reel" to "we're actually going."

**The core loop:** Share link → blob absorbs it → browse blobs → tap → swipe flashcards → see suggestion → vote In/Maybe/Out → plan happens.

### Platform Strategy

- **Cross-platform mobile app** — React Native + Expo, iOS and Android
- **Touch-first** — all interactions designed for thumb navigation: swipe flashcards, tap blobs, drift by panning
- **Always-connected** — real-time sync is core to the experience (offline deferred post-hackathon)
- **Demo context** — optimised for Expo Go on 4 team members' devices simultaneously, no native builds required
- **Share sheet integration** — native iOS/Android share sheet is the ideal input method; URL paste as demo fallback

### Effortless Interactions

- **Sharing content** should feel identical to forwarding a reel in a group chat — same effort, different destination
- **Navigating blobs** should feel like drifting through clouds — no deliberate menu selection, just smooth spatial movement
- **Understanding an extraction card** should take under 2 seconds of scanning — venue, price, vibe, done
- **Voting on a plan** should be a single tap — In/Maybe/Out, no confirmation dialog, optimistic update
- **Seeing who's committed** should be instant and ambient — avatar rings update in real-time without refreshing
- **Classification and clustering** should happen automatically — user shares a link, AI handles the rest, reel appears in the right blob

### Critical Success Moments

1. **"Whoa" moment** — user opens the board and sees floating gradient blobs for the first time. Must feel magical, not like a loading screen. The blobs should already be gently drifting.
2. **"It actually works" moment** — user shares a reel URL, the extraction card appears with accurate venue name, price, and date. The AI understood the actual content, not just hashtags.
3. **"That's literally us" moment** — after 3-5 reels, the blob clusters start making sense. "Japanese food" blob is bigger because that's what the group shares most. The vibe labels feel accurate.
4. **"It's happening" moment** — a suggestion appears based on real group taste, someone votes In, the tally updates live on everyone's screen. The plan feels inevitable.
5. **"I want this for my friends" moment** — the demo viewer (judge, other team) sees the full flow and immediately imagines their own friend group using it.

### Experience Principles

1. **Drift, don't click** — navigation should feel spatial and continuous, not menu-driven. Users explore by moving through a space, not selecting from lists.
2. **AI is invisible** — extraction, classification, clustering, suggestions all happen automatically. The user's only job is to share links and react to plans. Intelligence is felt, not seen.
3. **Beauty carries meaning** — the gradient blobs aren't decoration. Size = engagement, proximity = similarity, colour = vibe. Every visual choice communicates data.
4. **Social pressure by design** — commitment mechanics (live tallies, avatar rings, nudges) create gentle urgency without guilt. The UI makes inaction visible without being aggressive.
5. **One tap, not two** — every primary action (vote, share, regenerate) is a single interaction. No confirmation modals, no "are you sure." Trust the user.

## Desired Emotional Response

### Primary Emotional Goals

- **Wonder** — the blob graph view should stop users in their tracks. The first time they open a board, the reaction should be visceral: "this is beautiful." The soft gradients, floating motion, and glowing opacity create an experience that feels more like entering a space than opening an app.
- **Curiosity** — the blobs should invite exploration. Different sizes, different colours, gentle drifting — users should instinctively want to tap and discover what's inside each cluster. The UI should feel explorable, not instructional.
- **Belonging** — the blobs represent your friend group's collective taste. Seeing "Japanese Food" as the biggest blob because that's what everyone shares should make users feel seen. This is your group's world, visualised.
- **Excitement + social momentum** — when a suggestion drops and votes start coming in, the energy should build. Live tally updates, avatar rings turning green — it should feel like something is happening right now and you want to be part of it.

### Emotional Journey Mapping

| Stage | Desired Feeling | Design Driver |
|-------|----------------|---------------|
| First open (auth) | Warm, inviting, low friction | Clean auth screen, warm palette |
| Personality survey | Playful, self-expressive | Tag-picker format, fun categories |
| First board (empty) | Anticipation, potential | Subtle animation hinting at what blobs will become |
| Board with blobs | Wonder, curiosity, belonging | Floating gradient blobs, gentle drift, spatial navigation |
| Tap a blob | Delight, discovery | Expand animation, cards flying out smoothly |
| Swipe flashcards | Engagement, "this is smart" | Clean extraction data, accurate AI insights |
| Suggestion appears | Excitement, momentum | Contextual recommendation tied to real group taste |
| Friends vote In | Social energy, inevitability | Live tally, avatar rings, the plan feels real |
| Returning to app | Familiarity, "what's new" | Blobs may have shifted, new reels absorbed |

### Micro-Emotions

**Critical to get right:**
- **Confidence over confusion** — the blob view is novel, so users must intuitively understand they can tap to explore. No tutorial needed, just clear affordances (subtle pulse, label text, card edges peeking out).
- **Delight over mere satisfaction** — every transition should have a moment of magic. Blob expand, card fly-out, flashcard swipe — these should feel crafted, not default.
- **Belonging over isolation** — even before the group has shared much, the personality survey seeds a sense of identity. "The app already knows me."

**Critical to avoid:**
- **No guilt** — commitment mechanics must feel like momentum, not pressure. "3 friends are In" is exciting. "You haven't responded" is guilt. The UI should never shame.
- **No overwhelm** — extraction cards have dense data. The flashcard format keeps it to one card at a time, scannable in 2 seconds. No walls of text.
- **No anxiety** — missing a suggestion or not voting shouldn't feel punishing. Archived plans can be revived. There's always another suggestion.

### Design Implications

| Emotion | UX Design Approach |
|---------|-------------------|
| Wonder | Soft gradients, gaussian blur, floating animation, parallax depth — the blob view must feel like a living artwork |
| Curiosity | Blobs at different sizes with visible card edges peeking out, subtle pulse on untapped blobs, labels hinting at content |
| Belonging | Group identity label prominent, taste profile feels personal, blob clusters reflect what the group actually shares |
| Excitement | Smooth transitions, real-time updates that feel alive, suggestion cards that feel urgent but not stressful |
| No guilt | Voting uses neutral language (In/Maybe/Out, not Yes/No), no "you haven't responded" copy, grey = pending not failure |
| No overwhelm | One flashcard at a time, extraction data prioritised (venue > price > vibe > tags), progressive disclosure |
| No anxiety | Archived plans show as "Plans you never took" (nostalgic, not judgemental), regenerate button always available |

### Emotional Design Principles

1. **Atmosphere over interface** — sendit should feel like entering a space, not using a tool. The blob view is a place you drift through, not a screen you navigate.
2. **Momentum over pressure** — social features should create forward energy ("3 friends are in, let's go") not backward guilt ("you haven't responded"). Positive framing always.
3. **Magic in the transitions** — every state change is an opportunity for delight. Blob expand, card fly-out, vote confirmation — these micro-moments are what users screenshot and share.
4. **The graph view is the brand** — the floating gradient blobs are what makes someone screenshot the app and send it to their group chat. This is the visual identity of sendit. It must be stunning.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

**Pinterest**
- **Masonry grid layout** — cards of varying heights create visual rhythm without rigidity. Content feels abundant and browsable. No wasted space.
- **Card expand animation** — tapping a pin smoothly zooms it into a full detail view. The transition feels connected to the source — you know where you came from and can easily return.
- **Visual density** — image-forward, minimal text on cards. You scan with your eyes, not by reading. Information hierarchy is: image > title > metadata.
- **Applied to sendit:** The flashcard screen after tapping a blob uses a Pinterest-style masonry grid of reel extraction cards. Tap a card to expand into full detail with venue/price/booking. Visual density makes the board feel rich and alive.

**Passion Finder (glassmorphism bubbles reference — ui designs/glassmorphism bubbles.webp)**
- **Tag bubble picker** — interests displayed as floating white bubbles on a warm gradient background with glassmorphism blur. Tappable, tactile, playful.
- **Warm gradient backdrop** — orange/amber tones with soft blur create an inviting, personal atmosphere. Not clinical.
- **Progressive reveal** — moves from tag selection to deeper personality analysis to results. Each step feels like discovery.
- **Applied to sendit:** Direct reference for the personality survey onboarding. 10 screens of floating tag bubbles (hobbies, activities, energy level, etc.) on glassmorphism gradient backgrounds, using sendit's palette (blush, sage, berry, teal, navy).

**Spline 3D Blobs (Panter Vision reference — ui designs/3D Blobs in Spline App.jpeg + 3d blob video.mp4)**
- **Organic shape language** — distorted spheres with smooth/grab brush feel alive, not geometric. They breathe.
- **Depth through material** — fresnel effects, glass layering, depth gradients create convincing 3D without true 3D rendering. Shadows add grounding.
- **Multi-colour composition** — magenta, blue, orange, glass blobs at different sizes and depths. Foreground/background layering creates spatial hierarchy.
- **Applied to sendit:** The blob graph view. 5 blobs with radial gradients, gaussian blur, and faked 3D depth (scale + blur layering). Foreground blobs are larger/sharper, background blobs are smaller/blurrier. Subtle floating animation with Reanimated.

**Korean Seasons Gradient Poster (ui designs/circular blobs.jpeg)**
- **Soft radial gradients** — pink-to-orange-to-blue colour transitions with feathered edges. Blobs overlap with opacity blending.
- **50% opacity overlap** — where blobs intersect, colours mix and glow. Creates depth without hard boundaries.
- **Different sizes** — creates natural visual hierarchy. Your eye goes to the largest blob first.
- **Applied to sendit:** Blob gradient and sizing model. Each blob's size maps to engagement/like count within that vibe cluster. Colours drawn from sendit palette with radial gradient transitions. Overlap areas glow.

### Transferable UX Patterns

**Navigation Patterns:**
- **Spatial navigation (blob view)** — drift between blobs by panning, not menu selection. Inspired by Obsidian graph view but with the aesthetic of Spline blobs.
- **Masonry browse (flashcard screen)** — Pinterest-style grid after blob expand. Browse by scanning, not scrolling a list.

**Interaction Patterns:**
- **Tag bubble picker (survey)** — Passion Finder style floating bubbles for onboarding. Tap to select, playful physics.
- **Card expand (flashcard detail)** — Pinterest-style smooth zoom from masonry grid to full extraction card.
- **Blob tap → expand → cards fly out** — custom transition combining blob growth animation with card scatter. No direct reference — this is sendit's signature interaction.

**Visual Patterns:**
- **Glassmorphism + warm gradients** — Passion Finder's blur/glass aesthetic applied to sendit's palette for auth, survey, and overlays.
- **3D depth faking** — Spline blob technique (scale, blur, opacity layering) applied to blob graph view via React Native Skia.
- **Dark theme with glowing accents** — news-tab's dark card style combined with blob glow for the board list and overall app chrome.

### Anti-Patterns to Avoid

- **Flat, geometric bubbles** — the react-native-bubble-select library looked cold and rigid. Blobs must feel organic, soft, alive. No hard circles.
- **WebView-dependent 3D** — 3d-force-graph requires WebGL in a WebView, killing native gesture performance. Fake 3D with Skia instead.
- **AI-generated generic UI** — standard gradient buttons and card layouts that look like every other app. Every component should be sourced from reactbits.dev or specifically designed with the frontend-design skill.
- **Tutorial overlays** — the blob view is novel but should be self-explanatory. No "tap here to explore" tooltips. Affordances (subtle pulse, visible card edges, labels) teach through design, not instruction.
- **Rigid grid layouts** — everything should feel organic. Masonry over grid. Floating over pinned. Drifting over snapping.

### Design Inspiration Strategy

**What to Adopt:**
- Pinterest masonry layout + card expand animation → flashcard screen
- Passion Finder glassmorphism tag bubbles → personality survey
- Spline 3D blob depth/material techniques → blob graph view (via Skia)
- Korean poster gradient/opacity/sizing → blob colour and hierarchy model
- reactbits.dev components → animations, text effects, interactive elements throughout
- News-tab dark card list → board list screen

**What to Adapt:**
- Pinterest's web-scale masonry → simplified to 5-15 cards per blob cluster (mobile screen constraints)
- Spline's WebGL rendering → faked with React Native Skia (radial gradients, blur, blend modes)
- Passion Finder's single-screen picker → expanded to 10-screen progressive survey

**What to Avoid:**
- react-native-bubble-select (archived, cold aesthetic)
- 3d-force-graph in WebView (performance killer)
- Default React Native component styling (generic, AI-looking)
- Tutorial overlays or instructional text on novel interactions

## Design System Foundation

### Design System Choice

**Hybrid Custom** — a bespoke design system assembled from curated component sources, custom rendering (Skia), and existing design tokens. No off-the-shelf UI library as the base.

### Rationale for Selection

- **Visual uniqueness is non-negotiable** — the blob graph view, glassmorphism survey, and Pinterest-style flashcards cannot be achieved with Material Design or any themeable library. The aesthetic IS the product.
- **Component sources are already defined** — reactbits.dev for animated primitives, specific URL references for key screens, frontend-design skill for composition. This isn't building from scratch — it's assembling from curated sources.
- **Existing design tokens are solid** — `constants/Theme.ts` already defines the colour palette (navy backgrounds, burgundy/teal/sage/blush accents), Nunito typography system (light through black + RubikBubbles display), semantic colours, and spacing/radius scales. This is the foundation.
- **Hackathon context favours speed with impact** — a fully custom blob view + polished flashcard screen will win more than 20 perfectly-themed standard screens. Focus custom effort on the hero moments.

### Implementation Approach

**Layer 1 — Design Tokens (existing, extend)**
- Colour palette: extend Theme.ts with blob gradient definitions, glassmorphism blur values, glow opacity levels
- Typography: Nunito (body) + RubikBubbles (display/logo) — already configured
- Spacing: 8px base grid — already configured
- Border radius: sm(8), md(12), lg(16), xl(20), full(999) — already configured
- Shadows: add 3D depth shadow definitions for blob cards

**Layer 2 — Primitive Components (reactbits.dev + frontend-design)**
- Buttons, inputs, modals — source from reactbits.dev, themed to sendit palette
- Cards — custom styled, dark theme with warm accents
- Tag bubbles — glassmorphism style for personality survey
- Navigation — bottom tab bar, dark chrome

**Layer 3 — Custom Rendering (React Native Skia)**
- Blob graph view — radial gradients, gaussian blur, blend modes, animated transforms
- Blob-to-flashcard transition — custom shared element transition
- Glow effects — URL input bar, active states, blob highlights

**Layer 4 — Animation System (Reanimated)**
- Blob floating/drifting — continuous subtle animation
- Card fly-out — blob expand transition
- Flashcard swipe — gesture-driven card navigation
- Tag bubble physics — survey interaction
- Vote confirmation — micro-animation feedback

### Customization Strategy

| Component | Source | Customization |
|-----------|--------|---------------|
| Blob graph view | Custom (Skia + d3-force) | Fully bespoke — sendit's signature screen |
| Personality survey | Passion Finder reference + reactbits.dev | Glassmorphism tag bubbles on warm gradient |
| Board list cards | News-tab reference + frontend-design | Dark cards with custom covers, warm accents |
| Flashcard masonry grid | Pinterest reference + frontend-design | Masonry layout with extraction card design |
| Flashcard detail expand | Pinterest reference + Reanimated | Smooth zoom transition |
| URL input bar | Custom | Glowing, low-opacity, floating at bottom |
| Vote buttons (In/Maybe/Out) | reactbits.dev + custom | Single-tap with micro-animation feedback |
| Commitment tally | Custom | Avatar rings with real-time colour updates |
| Auth screen | reactbits.dev + frontend-design | Clean, warm, Google OAuth + email/password |
| Bottom tab bar | Custom themed | Dark chrome, warm accent on active tab |

## Defining Experience

### The One-Liner

> **"Share reels, see your group's taste form as floating clouds, get AI-powered plans that actually happen"**

### Defining Interaction

The defining experience is a three-act loop:

1. **Input** — paste a reel URL (or share via share sheet). Zero friction, one action.
2. **Magic** — AI extracts venue/price/date/vibe, the reel card floats into the correct vibe blob on the graph. The group's taste cloud shifts and grows.
3. **Output** — a specific plan suggestion emerges from the group's collective taste. Friends vote In/Maybe/Out. The plan happens.

### User Mental Model

Users come from group chats where sharing a reel = "we should do this." But nobody acts. Sendit replaces the group chat with a space that:
- **Remembers** what everyone shares (blobs cluster it)
- **Understands** what everyone likes (taste profile)
- **Suggests** what to actually do (AI recommendations)
- **Commits** the group socially (voting + tally)

The mental model is: "this is my group chat, but it actually does something with all those links we share."

### Novel UX Patterns

- **Blob graph navigation** — completely novel. No mainstream app uses vibe-clustered floating gradient blobs as primary navigation. Taught through affordance (visible card edges, labels, gentle pulse), not tutorials.
- **Blob-to-masonry transition** — novel animation combining blob expand with card scatter into Pinterest-style grid. Sendit's signature moment.
- **Personality survey as onboarding** — adapts Passion Finder tag-picker pattern to build individual taste vectors before any content is shared.

### Experience Mechanics

| Phase | User Action | System Response | Feedback |
|-------|------------|----------------|----------|
| Initiation | Paste URL in glowing input | Platform auto-detected, reel created | Platform icon appears |
| Extraction | Wait (~2-3s) | Edge function extracts metadata, classifies content | Loading shimmer on blob, then card appears inside correct blob |
| Discovery | Pan/drift between blobs | Spatial navigation, blobs float around | Smooth, continuous, cloud-like movement |
| Exploration | Tap a blob | Blob expands, cards fly out into masonry grid | Smooth transition animation |
| Detail | Tap a card in masonry | Card expands to full extraction detail | Pinterest-style zoom, venue/price/date visible |
| Suggestion | Scroll past cards | AI suggestion appears at end of cluster | Contextual — "based on what your group shares about [vibe]" |
| Commitment | Tap In/Maybe/Out | Vote recorded, tally updates live | Avatar ring colour change, count increment |
| Return | Re-open app | Blobs may have new cards, sizes shifted | Subtle animation showing what's new |
