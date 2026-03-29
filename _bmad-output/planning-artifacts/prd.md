---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain-skipped", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish", "step-12-complete"]
inputDocuments:
  - "Ideas/sendit_cross_platform (1).html"
  - "Ideas/sendit_teammate_explainer (1).html"
  - "Ideas/sendit_team_doc (2).docx"
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
workflowType: 'prd'
classification:
  projectType: mobile_app
  domain: social_consumer
  complexity: medium
  projectContext: greenfield
  scope: full_product_prioritized
  timeline: 24_hours_4_devs_hackathon
---

# Product Requirements Document - Sendit

**Author:** Ayday
**Date:** 2026-03-28

## Executive Summary

Sendit is a cross-platform mobile app (React Native + Expo) that transforms the short-form video content friend groups already share with each other into plans that actually happen. Gen Z friend groups send reels, TikToks, and Shorts to each other daily — rooftop bars, restaurants, club nights, recipes, trip ideas — into group chats where they get buried and die. The intent is real. The follow-through is zero. Sendit captures that signal at the point of sharing via the native iOS/Android share sheet (same 3 taps as forwarding a reel), processes content through a four-layer AI extraction pipeline (transcript, on-screen text, metadata, web verification), builds a living cross-platform taste profile for the group, and surfaces one specific, calendar-aware plan suggestion when the group is ready. It then tracks commitment, nudges holdouts privately, and preserves the memory of every night that actually happens — photos, one-line memories, AI-written chapters, and a scrollable group timeline.

Target users are Gen Z friend groups (18-28) who communicate primarily through shared short-form video content across Instagram, TikTok, and YouTube. The app serves both high-activity "let's go out" groups and lower-key groups that bond over brainrot, political satire, and dark humour — because all content is taste data that builds the group's identity.

### What Makes This Special

**Zero new behaviour required.** Sendit lives inside the native share sheet of every app. The input mechanism is identical to forwarding a reel to a group chat — but instead of dying in the chat, it lands on a board that reads it. The product works because it doesn't ask users to change anything about how they already behave.

**Cross-platform taste graph.** Instagram Blend only reads Instagram. Spotify Blend only reads Spotify. Sendit is the only product that reads taste signals across all short-form video platforms and synthesises them into a single group identity. A group that sends TikToks for humour, Reels for food, and Shorts for music has a richer profile in Sendit than anywhere else.

**Group intelligence, not individual.** Every recommendation engine builds profiles for individuals. Sendit builds one for a friend group — the intersection of taste, not the union. The suggestion isn't "you might like this" — it's "three of you have been sending Japanese dinner reels for two weeks, you're all free Saturday at 7, here's a spot."

**AI that watches the video, not just the hashtags.** Four-layer extraction: spoken transcript (YouTube captions API / TikTok transcript API / Whisper fallback), on-screen text overlays (vision AI frame analysis), metadata and captions, and web verification against Google Places / Resident Advisor / Eventbrite to confirm real venues and events with accurate dates, prices, and booking links.

## Project Classification

- **Type:** Cross-platform mobile app (React Native + Expo)
- **Domain:** Social / Consumer
- **Complexity:** Medium — AI extraction pipeline and multi-platform URL parsing add technical depth; no regulatory constraints
- **Context:** Greenfield
- **Timeline:** 24-hour hackathon, team of 4 developers
- **Scope:** Full product implementation, features prioritised P0/P1/P2

## Success Criteria

### User Success

- **The "holy shit" moment:** User shares a reel URL → AI extraction card appears with venue name, price, date, booking link, vibe classification — visibly pulled from the actual video content, not just hashtags. This is the moment that wins "Best Use of AI."
- **The "that's literally us" moment:** After 3-5 reels, the group taste profile updates live and feels accurate — "Japanese food, rooftop vibes, underground music, dark humour, east London, ~£15/head." Users recognise their friend group in the data.
- **The "it actually happened" moment:** A concrete plan suggestion appears based on the group's taste signals + calendar availability. The commitment board shows who's in and who's stalling. The plan feels like it would actually get executed.
- **Zero friction input:** Sharing content to Sendit feels identical in effort to forwarding a reel in a group chat. Share sheet integration works natively. No new behaviour learned.

### Business Success (Hackathon Context)

- **Win "Best Use of AI" track:** Judges see a four-layer AI extraction pipeline that watches videos, not just metadata — transcript, on-screen text, captions, web verification. Demonstrably deeper than any competitor's AI usage.
- **Win "Hacker's Choice":** Other hackathon participants see the demo and think "I'd use this with my friends." The product resonates emotionally because everyone has a group chat full of dead plans.
- **Organic pull:** At least one other hackathon team asks "can I try this?" during or after the demo.

### Technical Success

- AI extraction returns structured data for YouTube Shorts and Instagram Reels URLs within 3 seconds
- Content correctly classified into one of five types (real event, real venue, vibe/inspiration, recipe, humour/identity) with >80% accuracy
- Taste profile updates in real-time as new content is added to the board
- Share sheet integration works on both iOS and Android simulators
- App runs smoothly on Expo across all 4 team members' devices simultaneously

### Measurable Outcomes

| Metric | Target |
|--------|--------|
| URL → extraction card | < 3 seconds |
| Classification accuracy | > 80% correct type |
| Taste profile update | Real-time after each reel |
| Suggestion relevance | Visibly derived from actual board content |
| Commitment board | Live tally updates across all connected devices |
| Demo length | < 3 minutes, covers full loop |

## Product Scope & Phased Development

### MVP Strategy

**Approach:** Experience MVP — make people *feel* the product's value, not just see it work. The demo needs to produce the "I want this for my friend group" reaction. Ship the core loop end-to-end (reel → extraction → taste → suggestion → commitment) rather than going deep on any single feature.

**Resources:** 4 developers, 24 hours, React Native + Expo + Supabase + Claude API.

**Guiding principle:** If it doesn't contribute to the demo flow or the judges' reaction, it waits.

### P0 — Must Ship (The Demo Floor)

**Core Journeys Supported:** J1 (board creation), J2 (sharing + suggestion), J3 (commitment)

| # | Feature | Why It's P0 |
|---|---------|-------------|
| 1 | Create board + join via link/code | No board = no product |
| 2 | Share sheet integration (iOS + Android) | The "zero new behaviour" differentiator |
| 3 | Paste URL fallback | Backup input if share sheet fails on simulator |
| 4 | AI extraction — 4-layer pipeline | The "Best Use of AI" moment |
| 5 | Content classification (5 types) | Proves the AI understands content, not just metadata |
| 6 | Group taste profile — live updating | The "that's literally us" moment |
| 7 | Plan suggestion — one specific recommendation | The conversion from intent to action |
| 8 | Commitment board — In/Maybe/Out + live tally | The social pressure mechanic that makes plans happen |

### P1 — Should Ship (Completes the Story)

**Journeys added:** J5 (calendar connect), J3 extended (nudges + receipt wall)

| # | Feature | Dependency |
|---|---------|-----------|
| 9 | Google Calendar integration (free/busy) | Requires Google OAuth |
| 10 | Calendar-aware suggestions | Requires #9 |
| 11 | Group identity label + shareable card | Requires taste profile (#6) |
| 12 | Decay reminder (72-hour nudge) | Requires push notifications |
| 13 | Private nudge to uncommitted members | Requires push notifications |
| 14 | Receipt wall for ticketed events | Requires image upload |

### P2 — Stretch (Wins Extra Points)

**Journey added:** J4 (memory + timeline)

| # | Feature | Dependency |
|---|---------|-----------|
| 15 | Event memory page (auto-created on plan confirm) | Requires suggestions + commitments |
| 16 | Shared photo drop (48-hour window) | Requires image storage |
| 17 | One-line memory prompts | Requires event page |
| 18 | Group timeline (scrollable history) | Requires multiple completed events |
| 19 | Group manifesto (AI character study) | Requires taste profile maturity |
| 20 | Plans you never took archive | Requires declined suggestions |
| 21 | Group playlist (Spotify integration) | Requires Spotify API OAuth |
| 22 | Weekly debate brief | Requires political/philosophical content classification |
| 23 | Multiple boards per user | Navigation + board switching UI |

### Vision (Post-Hackathon)

- Browser extension
- Auto-capture from group chats (WhatsApp/Telegram monitoring)
- Venue-side sponsored suggestions
- Affiliate commission monetisation
- Noosh integration (dinner party execution module)
- Annual chapter / Wrapped-style year review

### Risk Mitigation

**Technical Risks:**

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Share sheet extension requires Expo eject | Blocks P0 primary input | Paste URL fallback ready from day 1. Demo with paste, pitch with share sheet. |
| AI extraction latency > 3 seconds | Demo feels sluggish | Pre-warm extraction for demo URLs. YouTube Shorts first (fastest API). |
| Supabase Realtime connection drops | Board updates don't sync | Polling fallback every 5 seconds. Not ideal but functional. |
| Claude API rate limits during demo | Extraction fails live | Cache extraction results. Pre-process demo reel set. |

**Market Risks:**

| Risk | Validation |
|------|-----------|
| "People won't leave their group chat for this" | Share sheet means they don't leave — same action, different destination. Demo proves this. |
| "Groups won't actually commit" | The grey circle / receipt wall mechanic creates social pressure. Hackathon audience reaction validates. |

**Resource Risks:**

| Risk | Contingency |
|------|------------|
| One teammate gets stuck | P0 features are parallelizable — 3 people can still ship the core loop |
| Time runs out at hour 18 | P0 is self-contained. Drop P1/P2, polish the demo flow. |
| Backend issues | Supabase handles infra. If Edge Functions fail, fall back to local Express server. |

## User Journeys

### Journey 1 — Priya Creates "Summer Friends" (Board Creation + Onboarding)

Priya's scrolling Instagram at 11pm, sees a rooftop bar reel, sends it to her group chat for the hundredth time. This time she thinks "we never actually go." She downloads Sendit, taps "Create Board", types "Summer Friends", gets a join link. Drops it in the WhatsApp group with "everyone join this." Four friends tap the link, enter their names, they're on the board — no account required, 5 seconds. Priya shares the rooftop reel via share sheet — two taps. The AI extraction card appears: venue name, location, vibe tag, price range. Her friends see it land on the board in real-time and go "wait, what is this?"

**Reveals:** Board creation flow, join-via-link onboarding, anonymous session model, share sheet integration, real-time board sync, AI extraction pipeline.

### Journey 2 — Tom the Casual Sharer (Content Input + Suggestion)

Tom's on TikTok during his commute. Sees a video about a warehouse rave, creator mentions "Peckham Audio, tickets £12." Tom hits share → Sendit → picks "Summer Friends" → done. Three taps, same effort as sending it to the group chat. He doesn't open the app again for two days. When he does, the board has 8 reels from different people, a taste profile that says "underground music, east London, intimate evenings, dark humour" and a suggestion: "3 of you have been sending club night reels. You're all free Saturday. Peckham Audio has a night — £12. Who's in?" Tom taps "I'm in."

**Reveals:** Share sheet as primary input, cross-platform URL handling, taste profile building across multiple reels, AI-generated plan suggestion, commitment action.

### Journey 3 — Sofia the Holdout (Commitment Pressure + Nudges)

Sofia sees the suggestion on the board but doesn't commit. She's a Maybe. Two days later she gets a private push notification: "3 of your friends have confirmed for Saturday at Peckham Audio. Still interested?" She taps through, sees Priya ✓, Tom ✓, Mehrdad ✓, Sofia ⬜. The empty grey circle is her. She taps "I'm in" and drops a screenshot of her ticket purchase into the receipt wall.

**Reveals:** In/Maybe/Out commitment states, private nudge notifications, receipt wall with ticket confirmation, social pressure through visual design (grey circles), push notification infrastructure.

### Journey 4 — The Group After the Night (Memory + Timeline)

Saturday happens. Sunday morning, the event page is already there — pre-filled with the reel that started it, the date, who went. Everyone gets a prompt: "One thing you'll remember about last night?" Priya writes "the queue was worth it." A 48-hour window opens for photo drops. By Monday the board has a memory page with photos, one-liners, and an AI-written chapter. It joins the group timeline. Six months later, it's a scroll through every night they had together.

**Reveals:** Auto-created event pages, one-line memory prompts, shared photo upload, AI-written narrative chapter, group timeline, long-term retention value.

### Journey 5 — Calendar Connect (Progressive Authentication)

The board has 5 reels but suggestions aren't landing on available times because the app doesn't know when people are free. The app prompts: "Want smarter suggestions? Connect your Google Calendar — your friends never see your plans." Priya taps through, Google OAuth, done. The app now holds only a free/busy mask — no event titles, no details. As more members authenticate, suggestions get sharper. When 3+ members have calendars connected, the first calendar-aware suggestion drops: a specific day, a specific time, for a plan the group actually wants.

**Reveals:** Progressive auth model (anonymous → Google OAuth), Google Calendar API (free/busy only), privacy-first calendar design, auth-gated feature unlock, suggestion quality scaling with data.

### Journey Requirements Summary

| Capability Area | Revealed By Journeys |
|----------------|---------------------|
| Board CRUD + join-via-link | J1 |
| Anonymous session + progressive auth | J1, J5 |
| Native share sheet (iOS + Android) | J1, J2 |
| URL paste fallback | J1, J2 |
| AI extraction pipeline (4 layers) | J1, J2 |
| Content classification (5 types) | J2 |
| Real-time board sync | J1, J2 |
| Taste profile engine | J2 |
| Plan suggestion engine | J2, J5 |
| Commitment board (In/Maybe/Out) | J2, J3 |
| Push notifications | J3 |
| Private nudge system | J3 |
| Receipt wall | J3 |
| Google OAuth + Calendar API | J5 |
| Event memory pages | J4 |
| Photo upload + storage | J4 |
| One-line memory prompts | J4 |
| AI narrative generation | J4 |
| Group timeline | J4 |

## Innovation & Competitive Landscape

### Innovation Areas

**Cross-platform group taste graph.** No existing product aggregates taste signals across multiple short-form video platforms for a friend group. Instagram Blend reads only Instagram. Spotify Blend reads only Spotify. Sendit reads across all platforms and builds a composite group identity — the intersection of taste, not any individual's profile. This is a fundamentally new data asset.

**Deep AI content understanding.** Standard URL processing reads metadata (title, description, hashtags). Sendit's four-layer extraction pipeline processes the actual video content — spoken transcript via captions API or Whisper, on-screen text overlays via vision AI, metadata and captions, then web verification against real venue and event databases. The output is a fully structured event card with confirmed venue, date, price, and booking link — not a guess.

**Behaviour interception, not behaviour change.** The share sheet integration means users don't learn a new action. They do exactly what they already do (share a reel from any app), but Sendit intercepts it and routes it to a board instead of a chat. Zero new behaviour required for adoption.

### Competitive Landscape

- **Instagram Blend / Spotify Blend:** Single-platform, individual-focused. No group intelligence, no cross-platform signals.
- **Shared Pinterest boards / Google Docs:** Manual curation, no AI extraction, no action output (no suggestions, no commitment tracking).
- **Partiful / IRL / Luma:** Event-first tools — you create an event then invite people. Sendit is desire-first — the group's shared content generates the event suggestion. Fundamentally different direction of flow.

### Validation Approach

Hackathon demo validates the core hypothesis: does AI extraction of a shared reel → group taste profile → specific plan suggestion produce a reaction of "I want this for my friend group"? Audience vote (Hacker's Choice) is the validation metric.

## Mobile App Requirements

### Platform Requirements

- **Framework:** React Native + Expo (managed workflow)
- **Target platforms:** iOS 15+ and Android 12+ via Expo simulators
- **Connectivity:** Always-connected. No offline mode required.
- **Store compliance:** Not applicable — not publishing to App Store/Play Store during hackathon

### Device Permissions & Features

| Permission | Purpose | Required For |
|-----------|---------|-------------|
| Share sheet receiver | Receive URLs from Instagram, TikTok, YouTube, any app | P0 — primary input mechanism |
| Deep linking | Join board via link from WhatsApp/messages | P0 — onboarding flow |
| Camera + photo library | Receipt wall screenshots, event photo drops | P1 (receipt wall), P2 (photo drops) |
| Push notifications | Decay reminders, private nudges, new suggestions | P1 — commitment pressure |
| Google OAuth | Authentication for calendar access | P1 — calendar integration |
| Calendar (read-only, free/busy) | Find mutual availability windows | P1 — calendar-aware suggestions |

### Push Notification Strategy

- **Provider:** Expo Push Notifications (handles both APNs and FCM)
- **Notification types:**
  - New suggestion available on board
  - Commitment deadline approaching (72-hour decay)
  - Private nudge ("3 of your friends confirmed for Saturday")
  - New reel added to board (optional, low priority)
- **Privacy:** Nudges come from the app, never exposing who asked for the nudge

### Technical Architecture Considerations

- **Real-time sync:** Supabase Realtime subscriptions for board updates, new reels, commitment changes — all members see updates instantly
- **Share sheet extension:** Requires Expo config plugin for iOS Share Extension and Android intent filter. Highest-risk technical component — fallback is paste URL.
- **Deep linking:** Expo Linking for `sendit://join/{board_code}` + universal links for web fallback
- **Image storage:** Supabase Storage for receipt screenshots and event photos
- **API layer:** Supabase Edge Functions (Deno) for AI extraction pipeline, or standalone Express server if more control needed

### Implementation Considerations

- **Expo managed workflow** preferred for speed, but share sheet extension may require a config plugin or bare workflow eject
- **Supabase** chosen over Firebase for: built-in Realtime, PostgreSQL (better for relational board/member/reel data), Edge Functions, and free tier
- **Claude API** for content classification and taste profile generation — single provider, consistent output format
- **YouTube Data API v3** as primary extraction source (richest metadata, free tier generous). Instagram and TikTok via third-party scraping APIs as secondary.

## Functional Requirements

### Board Management

- **FR1:** User can create a new board with a custom name
- **FR2:** System generates a unique join link/code for each board
- **FR3:** User can join an existing board via link or code without authentication
- **FR4:** User can set a display name when joining a board
- **FR5:** User can view all boards they belong to
- **FR6:** User can switch between multiple boards
- **FR7:** All board members can see other members' names and avatars

### Content Input

- **FR8:** User can share a URL to Sendit via the native iOS/Android share sheet from any app
- **FR9:** User can select which board to send content to when sharing via share sheet
- **FR10:** User can paste a URL directly into the board as a fallback input method
- **FR11:** System automatically detects the source platform from a URL (YouTube, Instagram, TikTok, X, other)
- **FR12:** All board members can see new content appear on the board in real-time

### AI Content Processing

- **FR13:** System extracts spoken transcript from video content (via captions API or Whisper)
- **FR14:** System extracts on-screen text overlays from video frames (via vision AI)
- **FR15:** System extracts metadata from URL (caption, hashtags, audio track, location tags, creator info)
- **FR16:** System verifies real venues and events against external databases (Google Places, Resident Advisor, Eventbrite)
- **FR17:** System classifies each piece of content into one of five types: real event, real venue, vibe/inspiration, recipe, humour/identity
- **FR18:** System generates a structured extraction card for each URL showing all discovered information
- **FR19:** User can view the extraction card with venue, price, date, booking link, vibe tags, and classification

### Group Taste Intelligence

- **FR20:** System builds and maintains a group taste profile from all content on the board
- **FR21:** Taste profile updates in real-time as new content is added
- **FR22:** User can view the group taste profile (activity types, aesthetic register, food preferences, location patterns, price range)
- **FR23:** System generates a group identity label based on the taste profile (e.g., "The Chaotic Intellectuals")
- **FR24:** User can view and share the group identity as a card
- **FR25:** System tracks cross-platform content signals as a taste indicator (TikTok-heavy = trends-aware, mixed = richer profile)

### Plan Suggestions

- **FR26:** System generates one specific plan suggestion based on the group's taste profile
- **FR27:** Each suggestion includes: what, why (which signals drove it), where, when, cost per person, and booking link if available
- **FR28:** System prioritises time-sensitive content (real events with dates) for immediate suggestion
- **FR29:** System incorporates calendar availability when suggesting a time (if calendars connected)
- **FR30:** User can request a new suggestion if the current one doesn't fit (regenerate)
- **FR31:** User can view the reasoning behind each suggestion (which reels influenced it)

### Commitment & Social Pressure

- **FR32:** User can mark themselves as In, Maybe, or Out on a suggestion
- **FR33:** All board members can see the live commitment tally for a suggestion
- **FR34:** User can upload a ticket/booking confirmation screenshot to the receipt wall
- **FR35:** All board members can see the receipt wall showing confirmed (green) vs pending (grey) avatars
- **FR36:** System sends a decay reminder notification if no one acts on a suggestion within 72 hours
- **FR37:** System sends a private nudge to uncommitted members when a majority has confirmed
- **FR38:** System archives suggestions that expire without action

### Memory & Timeline

- **FR39:** System auto-creates an event memory page when a plan reaches sufficient commitment
- **FR40:** Event page is pre-filled with the originating reel, date, venue, and attendees
- **FR41:** User can upload photos and videos to the event page within a 48-hour window post-event
- **FR42:** User can submit a one-line memory response to the prompt "One thing you'll remember about tonight?"
- **FR43:** System generates an AI-written narrative chapter summarising the event
- **FR44:** User can view a scrollable group timeline of all past events
- **FR45:** System maintains an archive of plans the group never acted on
- **FR46:** System periodically resurfaces archived plans as suggestions

### Authentication & Identity

- **FR47:** User can use the app with an anonymous device session (no account required)
- **FR48:** User can upgrade to Google OAuth when they want calendar integration
- **FR49:** System accesses only free/busy calendar data (no event titles or details)
- **FR50:** No board member can see another member's calendar events
- **FR51:** System computes mutual availability windows from connected calendars

### Shared Objects (Stretch)

- **FR52:** System generates a group manifesto (AI-written character study of the group)
- **FR53:** System generates a weekly debate brief from political/philosophical content on the board
- **FR54:** System generates a group playlist from music signals detected in shared reels

## Non-Functional Requirements

### Performance

- **NFR1:** AI extraction pipeline returns structured data within 3 seconds of URL submission
- **NFR2:** Board updates propagate to all connected clients within 1 second via Realtime subscriptions
- **NFR3:** App cold start to usable board screen in under 2 seconds
- **NFR4:** Taste profile recalculation completes within 2 seconds of new content added
- **NFR5:** Plan suggestion generation completes within 5 seconds (multiple AI reasoning steps)

### Security & Privacy

- **NFR6:** Calendar integration stores only free/busy time blocks — no event titles, descriptions, or attendee data
- **NFR7:** No board member can access another member's calendar data
- **NFR8:** Anonymous device sessions use secure local storage (Expo SecureStore) for session tokens
- **NFR9:** All API communication over HTTPS
- **NFR10:** Supabase Row Level Security (RLS) ensures users can only access boards they belong to

### Integration Reliability

- **NFR11:** YouTube Data API v3 extraction works reliably for public Shorts content
- **NFR12:** If a platform API fails, system degrades gracefully to metadata-only extraction with clear user feedback
- **NFR13:** Claude API calls include retry logic (1 retry with exponential backoff) for transient failures
- **NFR14:** Google Calendar OAuth token refresh handled automatically without user re-authentication
- **NFR15:** Extraction results are cached — re-submitting the same URL returns cached data instantly

### Real-Time Sync

- **NFR16:** Supabase Realtime maintains persistent WebSocket connections for all active board members
- **NFR17:** If WebSocket connection drops, client automatically reconnects and fetches missed updates
- **NFR18:** Commitment state changes are immediately consistent across all connected clients
