from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["tester"])

TESTER_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Sendit Media Tester</title>
    <style>
      :root {
        --bg: #f7f2e8;
        --panel: #fffaf2;
        --ink: #1f1a14;
        --muted: #716556;
        --line: #dccfbf;
        --accent: #c75b39;
        --accent-dark: #8f351b;
        --success: #2f7d4a;
        --error: #a72f2f;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background:
          radial-gradient(circle at top left, rgba(199, 91, 57, 0.14), transparent 30%),
          radial-gradient(circle at top right, rgba(47, 125, 74, 0.14), transparent 24%),
          linear-gradient(180deg, #f9f4eb 0%, #f5efe5 100%);
        color: var(--ink);
      }

      main {
        width: min(1100px, calc(100% - 32px));
        margin: 32px auto 48px;
        display: grid;
        gap: 20px;
      }

      .hero,
      .panel {
        background: rgba(255, 250, 242, 0.95);
        border: 1px solid var(--line);
        border-radius: 20px;
        box-shadow: 0 18px 48px rgba(57, 42, 24, 0.08);
      }

      .hero {
        padding: 28px;
      }

      h1,
      h2,
      h3 {
        margin: 0;
        font-weight: 600;
      }

      h1 {
        font-size: clamp(2rem, 5vw, 3.5rem);
        line-height: 0.95;
        letter-spacing: -0.04em;
      }

      .subtitle {
        margin-top: 12px;
        max-width: 720px;
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.5;
      }

      .grid {
        display: grid;
        gap: 20px;
        grid-template-columns: 1fr 1.1fr;
      }

      .panel {
        padding: 22px;
      }

      .panel h2 {
        font-size: 1.25rem;
        margin-bottom: 14px;
      }

      label {
        display: block;
        margin-bottom: 8px;
        font-size: 0.92rem;
        color: var(--muted);
      }

      input,
      select,
      textarea,
      button {
        width: 100%;
        border-radius: 14px;
        border: 1px solid var(--line);
        font: inherit;
      }

      input,
      select,
      textarea {
        padding: 12px 14px;
        background: #fffdf9;
        color: var(--ink);
      }

      textarea {
        min-height: 110px;
        resize: vertical;
      }

      button {
        cursor: pointer;
        padding: 12px 16px;
        border: 0;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
        color: white;
        font-weight: 600;
      }

      button.secondary {
        background: #efe3d2;
        color: var(--ink);
        border: 1px solid var(--line);
      }

      .stack {
        display: grid;
        gap: 14px;
      }

      .row {
        display: grid;
        gap: 12px;
        grid-template-columns: 1fr 1fr;
      }

      .actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }

      .actions button {
        width: auto;
        min-width: 140px;
      }

      .status {
        min-height: 24px;
        font-size: 0.95rem;
      }

      .status[data-tone="success"] {
        color: var(--success);
      }

      .status[data-tone="error"] {
        color: var(--error);
      }

      .summary {
        display: grid;
        gap: 12px;
        margin-bottom: 18px;
      }

      .summary-card {
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 16px;
        background: #fffdf9;
      }

      .summary-card h3 {
        font-size: 0.88rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 8px;
      }

      .summary-card p {
        margin: 0;
        line-height: 1.5;
        word-break: break-word;
      }

      .cover {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid var(--line);
        background: #f2eadf;
        min-height: 180px;
        display: grid;
        place-items: center;
      }

      .cover img {
        width: 100%;
        display: block;
      }

      .cover span {
        color: var(--muted);
        padding: 24px;
        text-align: center;
      }

      pre {
        margin: 0;
        padding: 16px;
        border-radius: 16px;
        background: #1f1d1a;
        color: #f8f2ea;
        overflow: auto;
        font-size: 0.9rem;
        line-height: 1.45;
      }

      .token-hint {
        color: var(--muted);
        font-size: 0.9rem;
      }

      @media (max-width: 900px) {
        .grid {
          grid-template-columns: 1fr;
        }

        .row {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>Sendit Media Tester</h1>
        <p class="subtitle">
          Sign in with your backend, paste a TikTok, Instagram Reel, or YouTube Shorts link,
          and inspect the response. This page talks directly to your FastAPI endpoints.
        </p>
      </section>

      <section class="grid">
        <div class="panel stack">
          <h2>Auth</h2>

          <div class="row">
            <div>
              <label for="email">Email</label>
              <input id="email" type="email" placeholder="you@example.com" />
            </div>
            <div>
              <label for="password">Password</label>
              <input id="password" type="password" placeholder="Your password" />
            </div>
          </div>

          <div class="actions">
            <button id="loginButton" type="button">Sign In</button>
            <button id="meButton" class="secondary" type="button">Check Session</button>
            <button id="logoutButton" class="secondary" type="button">Clear Token</button>
          </div>

          <div>
            <label for="token">Access Token</label>
            <textarea id="token" placeholder="Paste a bearer token here, or sign in above."></textarea>
            <p class="token-hint">Stored in local browser storage for quick testing.</p>
          </div>

          <div id="authStatus" class="status"></div>
        </div>

        <div class="panel stack">
          <h2>Scrape</h2>

          <div class="row">
            <div>
              <label for="platform">Platform</label>
              <select id="platform">
                <option value="auto">Auto Detect</option>
                <option value="instagram">Instagram Reels</option>
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube Shorts</option>
              </select>
            </div>
            <div>
              <label for="url">Media URL</label>
              <input id="url" type="url" placeholder="https://..." />
            </div>
          </div>

          <div class="actions">
            <button id="scrapeButton" type="button">Fetch Media</button>
          </div>

          <div id="scrapeStatus" class="status"></div>
        </div>
      </section>

      <section class="panel">
        <h2>Result</h2>
        <div class="summary">
          <div class="cover" id="coverBox">
            <span>No cover image yet.</span>
          </div>
          <div class="row">
            <div class="summary-card">
              <h3>Description</h3>
              <p id="descriptionValue">Nothing fetched yet.</p>
            </div>
            <div class="summary-card">
              <h3>Post Date</h3>
              <p id="postDateValue">Nothing fetched yet.</p>
            </div>
          </div>
          <div class="summary-card">
            <h3>User</h3>
            <p id="userValue">Nothing fetched yet.</p>
          </div>
        </div>
        <pre id="responseOutput">{}</pre>
      </section>
    </main>

    <script>
      const storageKey = "sendit-tester-token";
      const tokenField = document.getElementById("token");
      const authStatus = document.getElementById("authStatus");
      const scrapeStatus = document.getElementById("scrapeStatus");
      const responseOutput = document.getElementById("responseOutput");
      const coverBox = document.getElementById("coverBox");
      const descriptionValue = document.getElementById("descriptionValue");
      const postDateValue = document.getElementById("postDateValue");
      const userValue = document.getElementById("userValue");

      tokenField.value = localStorage.getItem(storageKey) || "";

      function setStatus(element, message, tone = "") {
        element.textContent = message;
        element.dataset.tone = tone;
      }

      function saveToken(token) {
        tokenField.value = token || "";
        if (token) {
          localStorage.setItem(storageKey, token);
        } else {
          localStorage.removeItem(storageKey);
        }
      }

      function detectPlatform(url) {
        try {
          const parsed = new URL(url);
          const host = parsed.hostname.toLowerCase();
          const path = parsed.pathname;

          if (host.includes("instagram.com") && path.startsWith("/reel/")) {
            return "instagram";
          }
          if (host.includes("tiktok.com")) {
            return "tiktok";
          }
          if (host.includes("youtube.com") && path.startsWith("/shorts/")) {
            return "youtube";
          }
        } catch (error) {
          return null;
        }

        return null;
      }

      function endpointForPlatform(platform) {
        if (platform === "instagram") {
          return "/api/v1/instagram/reels/scrape";
        }
        if (platform === "tiktok") {
          return "/api/v1/tiktok/videos/scrape";
        }
        if (platform === "youtube") {
          return "/api/v1/youtube/shorts/scrape";
        }
        return null;
      }

      function renderCover(url) {
        if (!url) {
          coverBox.innerHTML = "<span>No cover image returned.</span>";
          return;
        }
        coverBox.innerHTML = '<img alt="Cover image" src="' + url + '" />';
      }

      function renderUser(user) {
        if (!user) {
          userValue.textContent = "No user returned.";
          return;
        }

        const parts = [];
        if (user.name) {
          parts.push(user.name);
        }
        if (user.username) {
          parts.push("@" + user.username);
        }
        if (user.handle) {
          parts.push("@" + user.handle);
        }
        if (user.profile_url) {
          parts.push(user.profile_url);
        }
        if (user.channel_url) {
          parts.push(user.channel_url);
        }

        userValue.textContent = parts.join(" | ") || JSON.stringify(user);
      }

      async function parseResponse(response) {
        const text = await response.text();
        try {
          return text ? JSON.parse(text) : {};
        } catch (error) {
          return { raw: text };
        }
      }

      async function login() {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        if (!email || !password) {
          setStatus(authStatus, "Enter both email and password.", "error");
          return;
        }

        setStatus(authStatus, "Signing in...");

        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });

        const payload = await parseResponse(response);
        if (!response.ok) {
          setStatus(authStatus, payload.detail || payload.message || "Login failed.", "error");
          responseOutput.textContent = JSON.stringify(payload, null, 2);
          return;
        }

        const accessToken = payload.session && payload.session.access_token;
        saveToken(accessToken || "");
        setStatus(authStatus, "Signed in and token stored.", "success");
        responseOutput.textContent = JSON.stringify(payload, null, 2);
      }

      async function checkSession() {
        const token = tokenField.value.trim();
        if (!token) {
          setStatus(authStatus, "Paste or generate an access token first.", "error");
          return;
        }

        setStatus(authStatus, "Checking session...");

        const response = await fetch("/api/v1/auth/me", {
          headers: { Authorization: "Bearer " + token }
        });

        const payload = await parseResponse(response);
        if (!response.ok) {
          setStatus(authStatus, payload.detail || "Session check failed.", "error");
          responseOutput.textContent = JSON.stringify(payload, null, 2);
          return;
        }

        setStatus(authStatus, "Token is valid.", "success");
        responseOutput.textContent = JSON.stringify(payload, null, 2);
      }

      async function scrape() {
        const token = tokenField.value.trim();
        const url = document.getElementById("url").value.trim();
        const selectedPlatform = document.getElementById("platform").value;

        if (!token) {
          setStatus(scrapeStatus, "A bearer token is required to call the scrape endpoints.", "error");
          return;
        }

        if (!url) {
          setStatus(scrapeStatus, "Paste a media URL first.", "error");
          return;
        }

        const platform = selectedPlatform === "auto" ? detectPlatform(url) : selectedPlatform;
        const endpoint = endpointForPlatform(platform);

        if (!endpoint) {
          setStatus(scrapeStatus, "Could not detect the platform from that URL.", "error");
          return;
        }

        setStatus(scrapeStatus, "Fetching media...");

        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token
          },
          body: JSON.stringify({ url })
        });

        const payload = await parseResponse(response);
        responseOutput.textContent = JSON.stringify(payload, null, 2);

        if (!response.ok) {
          renderCover(null);
          descriptionValue.textContent = "No description available.";
          postDateValue.textContent = "No post date available.";
          userValue.textContent = "No user available.";
          setStatus(scrapeStatus, payload.detail || "Fetch failed.", "error");
          return;
        }

        renderCover(payload.cover_image_url || payload.thumbnail_url || null);
        descriptionValue.textContent = payload.description || "No description returned.";
        postDateValue.textContent = payload.post_date || payload.published_at || "No post date returned.";
        renderUser(payload.user || payload.author || payload.channel || null);
        setStatus(scrapeStatus, "Media fetched successfully.", "success");
      }

      document.getElementById("loginButton").addEventListener("click", login);
      document.getElementById("meButton").addEventListener("click", checkSession);
      document.getElementById("logoutButton").addEventListener("click", () => {
        saveToken("");
        setStatus(authStatus, "Token cleared from this browser.", "success");
      });
      document.getElementById("scrapeButton").addEventListener("click", scrape);
    </script>
  </body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def tester_page() -> HTMLResponse:
    return HTMLResponse(TESTER_HTML)
