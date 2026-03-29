---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# Sendit - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Sendit, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: User can create a new board with a custom name
- FR2: System generates a unique join link/code for each board
- FR3: User can join an existing board via link or code without authentication
- FR4: User can set a display name when joining a board
- FR5: User can view all boards they belong to
- FR6: User can switch between multiple boards
- FR7: All board members can see other members' names and avatars
- FR8: User can share a URL to Sendit via the native iOS/Android share sheet from any app
- FR9: User can select which board to send content to when sharing via share sheet
- FR10: User can paste a URL directly into the board as a fallback input method
- FR11: System automatically detects the source platform from a URL (YouTube, Instagram, TikTok, X, other)
- FR12: All board members can see new content appear on the board in real-time
- FR13: System extracts spoken transcript from video content (via captions API or Whisper)
- FR14: System extracts on-screen text overlays from video frames (via vision AI)
- FR15: System extracts metadata from URL (caption, hashtags, audio track, location tags, creator info)
- FR16: System verifies real venues and events against external databases (Google Places, Resident Advisor, Eventbrite)
- FR17: System classifies each piece of content into one of five types: real event, real venue, vibe/inspiration, recipe, humour/identity
- FR18: System generates a structured extraction card for each URL showing all discovered information
- FR19: User can view the extraction card with venue, price, date, booking link, vibe tags, and classification
- FR20: System builds and maintains a group taste profile from all content on the board
- FR21: Taste profile updates in real-time as new content is added
- FR22: User can view the group taste profile (activity types, aesthetic register, food preferences, location patterns, price range)
- FR23: System generates a group identity label based on the taste profile
- FR24: User can view and share the group identity as a card
- FR25: System tracks cross-platform content signals as a taste indicator
- FR26: System generates one specific plan suggestion based on the group's taste profile
- FR27: Each suggestion includes: what, why, where, when, cost per person, and booking link if available
- FR28: System prioritises time-sensitive content (real events with dates) for immediate suggestion
- FR29: System incorporates calendar availability when suggesting a time (if calendars connected)
- FR30: User can request a new suggestion if the current one doesn't fit (regenerate)
- FR31: User can view the reasoning behind each suggestion (which reels influenced it)
- FR32: User can mark themselves as In, Maybe, or Out on a suggestion
- FR33: All board members can see the live commitment tally for a suggestion
- FR34: User can upload a ticket/booking confirmation screenshot to the receipt wall
- FR35: All board members can see the receipt wall showing confirmed (green) vs pending (grey) avatars
- FR36: System sends a decay reminder notification if no one acts on a suggestion within 72 hours
- FR37: System sends a private nudge to uncommitted members when a majority has confirmed
- FR38: System archives suggestions that expire without action
- FR39: System auto-creates an event memory page when a plan reaches sufficient commitment
- FR40: Event page is pre-filled with the originating reel, date, venue, and attendees
- FR41: User can upload photos and videos to the event page within a 48-hour window post-event
- FR42: User can submit a one-line memory response
- FR43: System generates an AI-written narrative chapter summarising the event
- FR44: User can view a scrollable group timeline of all past events
- FR45: System maintains an archive of plans the group never acted on
- FR46: System periodically resurfaces archived plans as suggestions
- FR47: User can use the app with an anonymous device session (no account required)
- FR48: User can upgrade to Google OAuth when they want calendar integration
- FR49: System accesses only free/busy calendar data (no event titles or details)
- FR50: No board member can see another member's calendar events
- FR51: System computes mutual availability windows from connected calendars
- FR52: System generates a group manifesto (AI-written character study of the group)
- FR53: System generates a weekly debate brief from political/philosophical content on the board
- FR54: System generates a group playlist from music signals detected in shared reels

### NonFunctional Requirements

- NFR1: AI extraction pipeline returns structured data within 3 seconds of URL submission
- NFR2: Board updates propagate to all connected clients within 1 second via Realtime subscriptions
- NFR3: App cold start to usable board screen in under 2 seconds
- NFR4: Taste profile recalculation completes within 2 seconds of new content added
- NFR5: Plan suggestion generation completes within 5 seconds (multiple AI reasoning steps)
- NFR6: Calendar integration stores only free/busy time blocks — no event titles, descriptions, or attendee data
- NFR7: No board member can access another member's calendar data
- NFR8: Anonymous device sessions use secure local storage (Expo SecureStore) for session tokens
- NFR9: All API communication over HTTPS
- NFR10: Supabase Row Level Security (RLS) ensures users can only access boards they belong to
- NFR11: YouTube Data API v3 extraction works reliably for public Shorts content
- NFR12: If a platform API fails, system degrades gracefully to metadata-only extraction with clear user feedback
- NFR13: Claude API calls include retry logic (1 retry with exponential backoff) for transient failures
- NFR14: Google Calendar OAuth token refresh handled automatically without user re-authentication
- NFR15: Extraction results are cached — re-submitting the same URL returns cached data instantly
- NFR16: Supabase Realtime maintains persistent WebSocket connections for all active board members
- NFR17: If WebSocket connection drops, client automatically reconnects and fetches missed updates
- NFR18: Commitment state changes are immediately consistent across all connected clients

### Additional Requirements

- Starter template: `create-expo-app --template tabs` with Expo Router, TypeScript, tab navigation
- Dependencies: @supabase/supabase-js, expo-secure-store, expo-sharing, expo-linking, expo-image-picker, expo-notifications, expo-auth-session, expo-crypto, zustand
- Supabase schema: 8 tables deployed (boards, members, reels, taste_profiles, suggestions, commitments, events, calendar_masks)
- Edge Functions: extract, classify, taste-update, suggest
- State management: Zustand stores (board-store, auth-store, taste-store)
- Feature-based folder structure per Architecture doc
- Supabase Realtime enabled on boards, reels, commitments, taste_profiles, suggestions
- Environment config: .env with EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY
- API keys stored as Supabase Edge Function secrets (CLAUDE_API_KEY, YOUTUBE_API_KEY)

### UX Design Requirements

No UX Design document found. UI requirements derived from PRD user journeys and Architecture folder structure.

### FR Coverage Map

| FR | Epic | Description |
|----|------|------------|
| FR1-FR7 | Epic 1 | Board CRUD, join, members, switching |
| FR8-FR12 | Epic 2 | Share sheet, paste URL, platform detection, real-time |
| FR13-FR19 | Epic 2 | AI extraction pipeline, classification, extraction cards |
| FR20-FR25 | Epic 3 | Taste profile, identity label, cross-platform signals |
| FR26-FR31 | Epic 4 | Suggestion engine, reasoning, regenerate, calendar-aware |
| FR32-FR38 | Epic 5 | Commitment voting, receipt wall, nudges, archiving |
| FR39-FR46 | Epic 7 | Event pages, photos, memories, narrative, timeline |
| FR47 | Epic 1 | Anonymous device session |
| FR48-FR51 | Epic 6 | Google OAuth, calendar sync, mutual availability |
| FR52-FR54 | Epic 8 | Manifesto, debate brief, playlist |

## Epic List

### Epic 1: Board Creation & Onboarding
Users can create a named board, share a join link, and invite friends who join anonymously in one tap.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR47
**Priority:** P0 | **Assignee:** Person A

### Epic 2: Content Sharing & AI Extraction
Users can share URLs from any app via share sheet (or paste), and see an AI-powered extraction card with venue, price, date, vibe, and classification.
**FRs covered:** FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19
**Priority:** P0 | **Assignee:** Person B + C

### Epic 3: Group Taste Intelligence
The board builds a live taste profile from all shared content, showing the group's collective identity — activity types, food preferences, aesthetic, humour style.
**FRs covered:** FR20, FR21, FR22, FR23, FR24, FR25
**Priority:** P0 | **Assignee:** Person D (Ayday)

### Epic 4: Plan Suggestions
The system generates one specific, reasoned plan suggestion based on the group's taste profile, with venue, time, cost, and booking link.
**FRs covered:** FR26, FR27, FR28, FR29, FR30, FR31
**Priority:** P0 | **Assignee:** Person D (Ayday)

### Epic 5: Commitment & Social Pressure
Group members can vote In/Maybe/Out on suggestions, see live tallies, upload ticket receipts, and receive nudges.
**FRs covered:** FR32, FR33, FR34, FR35, FR36, FR37, FR38
**Priority:** P0 (voting + tally) / P1 (nudges + receipt wall) | **Assignee:** Person A

### Epic 6: Calendar Integration & Progressive Auth
Users can connect Google Calendar to enable calendar-aware suggestions. Privacy-first — only free/busy data.
**FRs covered:** FR48, FR49, FR50, FR51
**Priority:** P1 | **Assignee:** Whoever finishes P0 first

### Epic 7: Memory & Timeline
Completed plans become memory pages with photos, one-line memories, AI narratives, and a scrollable group timeline.
**FRs covered:** FR39, FR40, FR41, FR42, FR43, FR44, FR45, FR46
**Priority:** P2 | **Assignee:** Stretch

### Epic 8: Shared Objects
AI generates group manifesto, weekly debate brief, and group playlist from board content.
**FRs covered:** FR52, FR53, FR54
**Priority:** P2 | **Assignee:** Stretch

---

## Epic 1: Board Creation & Onboarding

Users can create a named board, share a join link, and invite friends who join anonymously in one tap.

### Story 1.1: App Scaffold & Anonymous Session

As a new user,
I want to open the app and get a device identity automatically,
So that I can start using Sendit without creating an account.

**Acceptance Criteria:**

**Given** a fresh install of Sendit
**When** the user opens the app for the first time
**Then** a unique device UUID is generated and stored in SecureStore
**And** the Supabase client is initialized with the project URL and anon key
**And** the user sees the board list screen (empty state)

### Story 1.2: Create Board with Join Code

As a user,
I want to create a named board and get a shareable join code,
So that I can invite my friend group.

**Acceptance Criteria:**

**Given** the user is on the board list screen
**When** they tap "Create Board" and enter a name (e.g. "Summer Friends")
**Then** a new board row is created in Supabase with a unique 6-character join code
**And** the user is automatically added as a member of the board
**And** the join code/link is displayed and copyable

### Story 1.3: Join Board via Link or Code

As an invited friend,
I want to join a board by tapping a link or entering a code,
So that I'm part of the group with zero friction.

**Acceptance Criteria:**

**Given** a user has a join link (sendit://join/ABC123) or a 6-character code
**When** they tap the deep link or enter the code manually
**Then** they are prompted to enter a display name
**And** a member row is created with their device_id and display_name
**And** they are navigated to the board detail screen

### Story 1.4: Board List & Switching

As a user with multiple boards,
I want to see all my boards and switch between them,
So that I can manage different friend groups.

**Acceptance Criteria:**

**Given** the user belongs to one or more boards
**When** they view the board list screen
**Then** all their boards are displayed with name and member count
**And** tapping a board navigates to its detail screen
**And** boards are fetched via Supabase filtered by the user's device_id in members table

### Story 1.5: Board Detail with Member List

As a board member,
I want to see who's on the board,
So that I know which friends are part of this group.

**Acceptance Criteria:**

**Given** the user is viewing a board detail screen
**When** the screen loads
**Then** all members are displayed with display names and avatars
**And** new members joining appear in real-time via Supabase Realtime subscription

---

## Epic 2: Content Sharing & AI Extraction

Users can share URLs from any app via share sheet (or paste), and see an AI-powered extraction card with venue, price, date, vibe, and classification.

### Story 2.1: Paste URL & Platform Detection

As a board member,
I want to paste a URL into the board and have the platform auto-detected,
So that I can share content without worrying about format.

**Acceptance Criteria:**

**Given** the user is on a board detail screen
**When** they paste a URL into the input field and submit
**Then** the system detects the platform (youtube, instagram, tiktok, x, other) from the URL pattern
**And** a reel row is created in Supabase with url, platform, board_id, added_by
**And** the extraction Edge Function is invoked automatically

### Story 2.2: AI Extraction Edge Function — Metadata

As the system,
I want to extract metadata from a video URL,
So that I can build structured data from shared content.

**Acceptance Criteria:**

**Given** a URL is submitted to the extract Edge Function
**When** the platform is YouTube
**Then** the YouTube Data API v3 is called to fetch title, description, tags, channel info, transcript
**And** when the platform is Instagram or TikTok, available metadata is scraped from the URL
**And** the raw metadata is passed to Claude API for structured extraction
**And** the result is returned as structured JSON (venue_name, location, price, date, vibe, activity, mood, hashtags, booking_url)

### Story 2.3: AI Extraction — Transcript & Vision Analysis

As the system,
I want to process video transcripts and on-screen text,
So that extraction captures what's actually said and shown in the video.

**Acceptance Criteria:**

**Given** a YouTube Shorts URL
**When** the extract Edge Function processes it
**Then** the spoken transcript is fetched via YouTube captions API (or Whisper fallback)
**And** on-screen text overlays are described via vision AI analysis
**And** both are included in the Claude API prompt for richer extraction
**And** the extraction completes within 3 seconds (NFR1)

### Story 2.4: Content Classification

As the system,
I want to classify each piece of content into one of five types,
So that the taste profile and suggestions can differentiate between event content and identity content.

**Acceptance Criteria:**

**Given** extraction data exists for a reel
**When** the classify Edge Function processes it
**Then** the content is classified as exactly one of: real_event, real_venue, vibe_inspiration, recipe_food, humour_identity
**And** the classification is stored on the reel row
**And** classification accuracy is >80% (NFR target)

### Story 2.5: Web Verification for Venues & Events

As the system,
I want to verify real venues and events against external databases,
So that suggestions include confirmed locations with booking links.

**Acceptance Criteria:**

**Given** a reel is classified as real_event or real_venue
**When** extraction identifies a venue name
**Then** Google Places API is queried to confirm the venue exists
**And** address, rating, and opening hours are added to extraction_data
**And** for real_events, Resident Advisor or Eventbrite is checked for upcoming dates and ticket links

### Story 2.6: Extraction Card UI

As a board member,
I want to see a rich extraction card for each shared URL,
So that I can instantly see what the content is about without watching the video.

**Acceptance Criteria:**

**Given** a reel has extraction_data and classification
**When** it is displayed on the board
**Then** an extraction card shows: platform icon, classification badge, venue name (if any), price, date, vibe tags, booking link
**And** cards for real_event type show a prominent "Tickets" button
**And** cards are visually distinct by classification type (color-coded)

### Story 2.7: Real-Time Reel Updates

As a board member,
I want to see new reels appear on the board instantly when someone shares,
So that the board feels alive and collaborative.

**Acceptance Criteria:**

**Given** the user is viewing a board detail screen
**When** another member adds a reel to the same board
**Then** the new reel and its extraction card appear within 1 second (NFR2)
**And** the update is powered by Supabase Realtime subscription on the reels table

### Story 2.8: Share Sheet Integration

As a user browsing Instagram/TikTok/YouTube,
I want to share a URL to Sendit via the native share sheet,
So that adding content is as easy as forwarding a reel.

**Acceptance Criteria:**

**Given** the user is in any app with a share button
**When** they tap Share and select Sendit
**Then** the Sendit share extension receives the URL
**And** the user can select which board to send it to
**And** the reel is added to the board and extraction begins
**Note:** If share sheet extension requires Expo eject, defer to P1 and rely on paste URL (Story 2.1) for hackathon demo.

---

## Epic 3: Group Taste Intelligence

The board builds a live taste profile from all shared content, showing the group's collective identity.

### Story 3.1: Taste Profile Generation

As the system,
I want to analyze all reels on a board and generate a group taste profile,
So that the group's collective preferences are captured as structured data.

**Acceptance Criteria:**

**Given** a board has 3+ reels with extraction data
**When** the taste-update Edge Function is invoked with the board_id
**Then** Claude API analyzes all extraction_data and produces a taste profile: activity_types, aesthetic, food_preferences, location_patterns, price_range, humour_style, platform_mix
**And** the taste_profiles row is created or updated for the board
**And** recalculation completes within 2 seconds (NFR4)

### Story 3.2: Taste Profile Display

As a board member,
I want to see the group's taste profile on the board screen,
So that I can see what our group is collectively into.

**Acceptance Criteria:**

**Given** a board has a taste_profiles row
**When** the user views the board detail screen
**Then** the taste profile is displayed showing activity types, food preferences, aesthetic, location patterns, and price range
**And** the display updates in real-time when the profile changes (Supabase Realtime)

### Story 3.3: Auto-Update Taste on New Reel

As the system,
I want to recalculate the taste profile whenever a new reel is added,
So that the profile stays current and responsive.

**Acceptance Criteria:**

**Given** a new reel is added to a board and extraction completes
**When** the extraction_data is saved
**Then** the taste-update Edge Function is automatically triggered
**And** the taste profile updates in real-time on all connected clients

### Story 3.4: Group Identity Label

As a board member,
I want the app to generate a fun group identity label,
So that my friend group has a shareable personality description.

**Acceptance Criteria:**

**Given** a taste profile exists with sufficient data (3+ reels)
**When** the taste profile is generated or updated
**Then** Claude API generates an identity_label (e.g. "The Chaotic Intellectuals")
**And** the label is stored in the taste_profiles row and displayed on the board

### Story 3.5: Shareable Group Identity Card

As a board member,
I want to share our group's identity as a visual card,
So that I can send it to the group chat and show off our collective personality.

**Acceptance Criteria:**

**Given** a board has an identity label and taste profile
**When** the user taps "Share Identity"
**Then** a shareable card image is generated with group name, identity label, and key taste attributes
**And** the card can be shared via the native share sheet

---

## Epic 4: Plan Suggestions

The system generates one specific, reasoned plan suggestion based on the group's taste profile.

### Story 4.1: Suggestion Generation

As a board member,
I want the app to suggest one specific plan based on our taste profile,
So that our group's shared interests turn into an actionable plan.

**Acceptance Criteria:**

**Given** a board has a taste profile with sufficient data
**When** the suggest Edge Function is invoked
**Then** Claude API generates one specific suggestion with: what, why (which reels drove it), where, when, cost_per_person, booking_url
**And** the suggestion is saved to the suggestions table
**And** generation completes within 5 seconds (NFR5)

### Story 4.2: Suggestion Card UI with Reasoning

As a board member,
I want to see the suggestion with a clear explanation of why it was chosen,
So that I understand the recommendation is based on what we've been sharing.

**Acceptance Criteria:**

**Given** a suggestion exists for the board
**When** the user views the suggestion screen
**Then** the suggestion card displays: what, where, when, cost, booking link
**And** a "Why this?" section shows which reels influenced the suggestion
**And** influenced reels are tappable to view their extraction cards

### Story 4.3: Time-Sensitive Prioritization

As the system,
I want to prioritize real events with upcoming dates,
So that time-sensitive opportunities aren't missed.

**Acceptance Criteria:**

**Given** a board has reels classified as real_event with dates
**When** generating a suggestion
**Then** events with dates in the next 14 days are weighted higher
**And** the suggestion prompt explicitly references upcoming events

### Story 4.4: Regenerate Suggestion

As a board member,
I want to request a new suggestion if I don't like the current one,
So that the group isn't stuck with one recommendation.

**Acceptance Criteria:**

**Given** a suggestion is displayed
**When** the user taps "Regenerate"
**Then** the suggest Edge Function is called again with instruction to produce a different plan
**And** the old suggestion is archived (status = 'archived')
**And** the new suggestion replaces it on screen

---

## Epic 5: Commitment & Social Pressure

Group members can vote In/Maybe/Out on suggestions, see live tallies, and receive nudges.

### Story 5.1: In/Maybe/Out Voting with Live Tally

As a board member,
I want to mark myself as In, Maybe, or Out on a suggestion,
So that the group can see who's committed.

**Acceptance Criteria:**

**Given** a suggestion is active on the board
**When** the user taps In, Maybe, or Out
**Then** a commitment row is upserted with their vote
**And** the live tally updates instantly for all members via Realtime (NFR18)
**And** each member's avatar shows their status (green=in, yellow=maybe, grey=out/pending)

### Story 5.2: Receipt Wall

As a board member,
I want to upload a screenshot of my ticket purchase,
So that the group can see who's actually bought tickets.

**Acceptance Criteria:**

**Given** a member has voted "In" on a suggestion
**When** they tap "Add Receipt" and select/take a photo
**Then** the image is uploaded to Supabase Storage (receipts bucket)
**And** the receipt_url is saved on their commitment row
**And** the receipt wall displays: green avatar with checkmark for receipts uploaded, grey for pending

### Story 5.3: Decay Reminder Notification

As a board member,
I want to get a nudge if nobody acts on a suggestion within 72 hours,
So that good plans don't die silently.

**Acceptance Criteria:**

**Given** a suggestion has been active for 72 hours with no "In" commitments
**When** the decay threshold is reached
**Then** a push notification is sent to all board members: "Still interested in [suggestion]?"
**And** after the reminder, if still no action in 24 hours, the suggestion is archived

### Story 5.4: Private Nudge to Uncommitted Members

As the system,
I want to privately nudge members who haven't committed when a majority has,
So that social pressure drives follow-through without public embarrassment.

**Acceptance Criteria:**

**Given** 3 of 5 members have committed "In"
**When** 2 members are still pending or "Maybe"
**Then** those 2 receive a private push notification: "3 of your friends have confirmed for Saturday. Still interested?"
**And** the notification comes from the app, not attributed to any member

### Story 5.5: Archive Expired Suggestions

As the system,
I want to archive suggestions that expire without action,
So that the board stays clean and focused on active plans.

**Acceptance Criteria:**

**Given** a suggestion has been active for 96+ hours with insufficient commitment
**When** the archive threshold is reached
**Then** the suggestion status is set to 'archived'
**And** it is removed from the active suggestion view
**And** it is stored for the "plans you never took" feature (Epic 7)

---

## Epic 6: Calendar Integration & Progressive Auth

Users can connect Google Calendar to enable calendar-aware suggestions.

### Story 6.1: Google OAuth Flow

As a board member,
I want to connect my Google account,
So that I can enable calendar-aware suggestions.

**Acceptance Criteria:**

**Given** the user taps "Connect Calendar" on the profile screen
**When** they complete Google OAuth via expo-auth-session
**Then** their google_id is saved to their member row
**And** the OAuth token is securely stored for calendar API access
**And** the profile screen shows "Calendar Connected"

### Story 6.2: Calendar Sync — Free/Busy Mask

As the system,
I want to read a member's calendar and store only free/busy blocks,
So that suggestions can be time-aware without exposing private calendar details.

**Acceptance Criteria:**

**Given** a member has connected Google OAuth
**When** calendar sync is triggered
**Then** the Google Calendar freebusy API is called for the next 14 days
**And** only busy time blocks (start/end timestamps) are stored in calendar_masks
**And** no event titles, descriptions, or attendee data are stored (NFR6)

### Story 6.3: Mutual Availability Computation

As the system,
I want to compute when all calendar-connected members are free,
So that suggestions land on times everyone can make.

**Acceptance Criteria:**

**Given** 2+ members have calendar masks
**When** the suggest Edge Function runs
**Then** it computes overlapping free windows from all calendar_masks
**And** the suggestion's "when" field is set to a specific time within a mutual free window

---

## Epic 7: Memory & Timeline

Completed plans become memory pages with photos, one-line memories, AI narratives, and a scrollable group timeline.

### Story 7.1: Auto-Create Event Page

As the system,
I want to auto-create an event memory page when enough members commit,
So that the event has a container before it happens.

**Acceptance Criteria:**

**Given** 3+ members commit "In" on a suggestion
**When** the commitment threshold is reached
**Then** an events row is created pre-filled with suggestion data, date, venue, and attendee list

### Story 7.2: Photo Drop

As a member,
I want to upload photos after the event,
So that our memories are collected in one place.

**Acceptance Criteria:**

**Given** an event page exists and it's within 48 hours post-event
**When** user uploads photos
**Then** images go to Supabase Storage and URLs are appended to the events.photos jsonb array

### Story 7.3: One-Line Memory

As a member,
I want to submit one sentence about the night,
So that the group builds a collective memory.

**Acceptance Criteria:**

**Given** an event page exists
**When** user submits a memory
**Then** {member_id, text} is appended to events.memories jsonb array
**And** all members' memories are visible on the event page

### Story 7.4: AI Narrative Chapter

As a member,
I want an AI-written summary of the night,
So that the event has a lasting narrative.

**Acceptance Criteria:**

**Given** an event has photos and memories
**When** narrative generation is triggered
**Then** Claude writes a short paragraph narrating the night and stores it in events.narrative

### Story 7.5: Group Timeline

As a member,
I want a scrollable timeline of all past events,
So that I can relive our group's history.

**Acceptance Criteria:**

**Given** a board has 1+ completed events
**When** user views the timeline screen
**Then** events are displayed chronologically with date, venue, photos thumbnail, and narrative preview

### Story 7.6: Plans You Never Took

As a member,
I want to see archived suggestions we never acted on,
So that good ideas can be rediscovered.

**Acceptance Criteria:**

**Given** archived suggestions exist
**When** user views the archive
**Then** past suggestions are displayed
**And** a "Revive" button creates a new active suggestion from the archived one

---

## Epic 8: Shared Objects

AI generates group manifesto, weekly debate brief, and group playlist from board content.

### Story 8.1: Group Manifesto

As a member,
I want an AI character study of our group,
So that we have a shareable portrait of who we are.

**Acceptance Criteria:**

**Given** a mature taste profile exists (10+ reels)
**When** manifesto generation is triggered
**Then** Claude writes a 3-5 sentence character study stored in taste_profiles and displayed as a shareable card

### Story 8.2: Weekly Debate Brief

As a member,
I want a weekly discussion topic from our political/philosophical reels,
So that our content sparks real conversations.

**Acceptance Criteria:**

**Given** a board has 3+ reels classified as humour_identity with political/philosophical content
**When** the weekly brief is generated
**Then** Claude produces a structured debate brief: motion, arguments for/against, provocations

### Story 8.3: Group Playlist

As a member,
I want a playlist generated from music signals in our reels,
So that the group has a soundtrack.

**Acceptance Criteria:**

**Given** reels have audio track names in extraction_data
**When** playlist generation is triggered
**Then** the system extracts song/artist names and generates a Spotify-compatible playlist suggestion
