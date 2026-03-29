Here’s your **fully rewritten, cohesive UX plan** — structured cleanly from onboarding → interaction → intelligence → action. This version aligns everything you’ve described into one **tight, buildable product flow**.

---

# **🧠 SENDIT — FULL UX PLAN**

## **🔁 Core Product Loop**

- Join Group → Share Reels → Explore via Swiping → Learn Taste → Get Recommendations → Commit → Repeat


This is the entire product. Every screen should serve this loop.

---

# **1\. 🔐 ONBOARDING (Login)**

## **Goal**

Get user into the app in **\< 5 seconds** with zero friction.

## **UX**

### **Screen: Login**

* Input: Display Name  
* Button: “Continue”

  ### **Behind the scenes:**

* Generate `device_id`  
* Store locally (SecureStore)

  ### **Output:**

User enters the system as an **anonymous participant**

---

# **2\. 📋 BOARDS (Group Entry Point)**

## **Goal**

Let users create or join friend groups

---

## **Screen: Boards List**

### **UI Elements**

* Header: “Your Boards”  
* List of boards (cards)  
* CTA Buttons:  
  * ➕ Create Board  
  * 🔑 Join with Code

  ---

  ## **Create Board Flow**

  ### **UX**

* Input: Board Name  
* Tap “Create”

  ### **Result**

* Board created  
* Unique **join code generated**  
* Share modal appears:  
  “Send this code to your friends”  
  ---

  ## **Join Board Flow**

  ### **UX**

* Input: Join Code  
* Input: Display Name  
* Tap “Join”  
  ---

  ## **Output**

User lands inside a **shared group space (board)**

---

# **3\. 🧩 BOARD (Core Experience Hub)**

## **Goal**

Visualise group identity \+ allow content input

---

## **Screen: Board View**

### **Layout**

#### **Top Section**

* Board Name  
* Member avatars  
* ➕ Add Reel (paste URL)  
  ---

  ## **🔵 Activity Bubbles (Primary UI Element)**

  ### **What They Represent**

Clusters of content grouped by **activity type**

Examples:

* 🍣 Food  
* 🎶 Music  
* 🍸 Nightlife  
* 🌿 Chill  
* 😂 Humor  
  ---

  ### **Visual Behavior**

* Bubble size \= number of reels  
* Dynamic \+ animated  
  ---

  ### **Interaction**

* Tap bubble → opens **Flashcard Experience**  
  ---

  ## **➕ Add Reel (Input Mechanism)**

  ### **UX**

* Paste URL  
* Tap “Add”

  ### **Result**

* Reel added to board  
* AI processes content  
* Bubbles update in real-time  
  ---

  # **4\. 🃏 FLASHCARD EXPERIENCE (Discovery Engine)**

  ## **Goal**

Turn passive content into **active preference signals**

---

## **Screen: Flashcards**

### **Layout**

- Top: Swipeable Flashcards  
- Bottom: Scrollable Recommendation Feed  
    
  ---

  # **4A. 🃏 Flashcards (Top Section)**

  ## **Purpose**

Capture **user taste via swiping**

---

## **Card Content (User-Facing)**

Each card shows:

* 🎥 Thumbnail  
* 🏷 Title / Hook  
* 📍 Venue (if available)  
* 💷 Price (if available)  
* 🧠 Vibe tags (e.g. “rooftop”, “underground”)  
* 📝 Short AI summary  
* Platform badge (TikTok / IG / YouTube)  
  ---

  ## **Swipe Actions**

| Action | Meaning |
| ----- | ----- |
| 👉 Right | Like |
| 👈 Left | Dislike |
| ⏭ Button | Skip |

  ---

  ## **Result of Swipe**

Each swipe updates:

* User preference profile  
* Recommendation feed (live)  
  ---

  # **4B. 📜 Recommendation Feed (Bottom Section)**

  ## **Purpose**

Show **personalised activities** based on swipe behaviour

---

## **UI Behavior**

* Scrollable list under flashcards  
* Updates in real-time as user swipes  
  ---

  ## **Content**

Each item shows:

* Thumbnail  
* Title  
* Venue  
* Tags  
* Optional: “Why you’re seeing this”  
  ---

  ## **Logic**

Recommendations are based on:

* Liked reels  
* Shared vibe tags  
* Activity types  
* Price alignment  
  ---

  ## **Key UX Insight**

The more you swipe, the better the feed becomes

---

# **5\. 🧠 TASTE INTELLIGENCE (Invisible but Critical)**

## **What’s Happening**

System builds a **preference model** from:

* Swipe behavior  
* Reel metadata  
* AI classification  
  ---

  ## **Example Profile**

- {  
-   nightlife: high,  
-   food: medium,  
-   vibes: \["underground", "intimate"\],  
-   price\_range: "£10–£20"  
- }  
    
  ---

  ## **Group Layer (Core Differentiator)**

Profiles are merged into a **group taste identity**

Not what YOU like — what YOU ALL like

---

# **6\. 🎯 PLAN RECOMMENDATION (Conversion Moment)**

## **Goal**

Turn taste into **real-world action**

---

## **Where It Appears**

Back on the **Board Screen**

---

## **UI: Suggestion Card**

### **Content**

* 🎯 “You should do this”  
* 📍 Venue  
* 🧠 Reason:  
  “3 of you liked underground music reels”  
* 📅 Suggested time  
* 💷 Price per person  
* 🔗 Booking link  
  ---

  ## **Key UX Principle**

Recommendation must feel *earned* from user behaviour

---

# **7\. ✅ COMMITMENT SYSTEM (Social Pressure)**

## **Goal**

Turn suggestion into an actual plan

---

## **UI Actions**

Buttons:

* ✅ In  
* 🤔 Maybe  
* ❌ Out  
  ---

  ## **Visual Feedback**

* Avatar row:  
  * Green \= committed  
  * Grey \= not committed

  ---

  ## **Tally Example**

- 3 In / 1 Maybe / 1 Out  
    
  ---

  ## **Psychological Mechanic**

The “grey circle” effect:  
Users feel pressure when everyone else commits

---

## **Optional: Receipt Upload**

* Upload ticket screenshot  
* Marks user as **confirmed**  
  ---

  # **8\. 🔄 CONTINUOUS LOOP**

After commitment:

* Users keep adding reels  
* Swiping refines taste  
* New recommendations appear  
  ---

  # **9\. 🧭 NAVIGATION STRUCTURE**

- Login  
-   ↓  
- Boards List  
-   ↓  
- Board View  
-   ↓  
- Flashcards (modal or screen)  
    
  ---

  # **10\. 🧱 COMPONENT SYSTEM**

  ## **Core Components**

  ### **1\. BoardCard**

* Displays group

  ### **2\. ActivityBubble**

* Visualises category

  ### **3\. Flashcard**

* Swipeable content

  ### **4\. RecommendationCard**

* Feed item

  ### **5\. SuggestionCard**

* Plan output

  ### **6\. AvatarGroup**

* Members \+ commitments  
  ---

  # **11\. ⚡ REAL-TIME BEHAVIOR**

  ## **Updates instantly for:**

* New reels  
* New members  
* Commitment changes  
* Taste evolution  
  ---

  # **12\. 🎯 MVP PRIORITY**

  ## **Must Have**

* Login (device-based)  
* Create/join board  
* Add reel (URL)  
* Activity bubbles  
* Flashcard swiping  
* Recommendation feed  
* Suggestion card  
* Commitment buttons  
  ---

  ## **Nice to Have**

* Animations  
* Real-time sync  
* Receipt wall  
  ---

  # **💡 FINAL PRODUCT INSIGHT**

This UX works because:

* **Input \= effortless (paste/share)**  
* **Discovery \= fun (swiping)**  
* **Output \= actionable (plans)**  
* **Pressure \= social (commitment)**  
  ---

  # **🚀 If you want next**

I can:

* Turn this into **actual React Native (Expo) screen code**  
* Design **state management (Zustand) for the full flow**  
* Or map this UX directly to your **existing backend endpoints**  
- 