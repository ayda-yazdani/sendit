import { useEffect, useState } from "react";

const storageKey = "sendit-tester-token";

function prettyUser(user) {
  if (!user) {
    return "Nothing fetched yet.";
  }

  const parts = [];
  if (user.name) {
    parts.push(user.name);
  }
  if (user.username) {
    parts.push(`@${user.username}`);
  }
  if (user.profile_url) {
    parts.push(user.profile_url);
  }

  return parts.join(" | ") || JSON.stringify(user);
}

function emptySummary() {
  return {
    coverImageUrl: null,
    description: "Nothing fetched yet.",
    postDate: "Nothing fetched yet.",
    userText: "Nothing fetched yet.",
  };
}

async function parseResponse(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch (_error) {
    return { raw: text };
  }
}

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");
  const [authStatus, setAuthStatus] = useState({ message: "", tone: "" });
  const [fetchStatus, setFetchStatus] = useState({ message: "", tone: "" });
  const [responseText, setResponseText] = useState("{}");
  const [summary, setSummary] = useState(emptySummary());
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  useEffect(() => {
    setToken(localStorage.getItem(storageKey) || "");
  }, []);

  function saveToken(nextToken) {
    setToken(nextToken);
    if (nextToken) {
      localStorage.setItem(storageKey, nextToken);
    } else {
      localStorage.removeItem(storageKey);
    }
  }

  function resetSummary() {
    setSummary(emptySummary());
  }

  function applyPayload(payload) {
    setSummary({
      coverImageUrl: payload.cover_image_url || null,
      description: payload.description || "No description returned.",
      postDate: payload.post_date || "No post date returned.",
      userText: prettyUser(payload.user),
    });
  }

  async function login() {
    if (!email.trim() || !password) {
      setAuthStatus({ message: "Enter both email and password.", tone: "error" });
      return;
    }

    setIsLoggingIn(true);
    setAuthStatus({ message: "Signing in...", tone: "" });

    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const payload = await parseResponse(response);
      setResponseText(JSON.stringify(payload, null, 2));

      if (!response.ok) {
        setAuthStatus({
          message: payload.detail || payload.message || "Login failed.",
          tone: "error",
        });
        return;
      }

      saveToken(payload.session?.access_token || "");
      setAuthStatus({ message: "Signed in and token stored.", tone: "success" });
    } catch (error) {
      setAuthStatus({
        message: `Login request failed: ${error.message || String(error)}`,
        tone: "error",
      });
    } finally {
      setIsLoggingIn(false);
    }
  }

  async function checkSession() {
    if (!token.trim()) {
      setAuthStatus({ message: "Paste or generate an access token first.", tone: "error" });
      return;
    }

    setIsCheckingSession(true);
    setAuthStatus({ message: "Checking session...", tone: "" });

    try {
      const response = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token.trim()}` },
      });

      const payload = await parseResponse(response);
      setResponseText(JSON.stringify(payload, null, 2));

      if (!response.ok) {
        setAuthStatus({
          message: payload.detail || "Session check failed.",
          tone: "error",
        });
        return;
      }

      setAuthStatus({ message: "Token is valid.", tone: "success" });
    } catch (error) {
      setAuthStatus({
        message: `Session request failed: ${error.message || String(error)}`,
        tone: "error",
      });
    } finally {
      setIsCheckingSession(false);
    }
  }

  async function fetchMedia() {
    if (!token.trim()) {
      setFetchStatus({ message: "A bearer token is required.", tone: "error" });
      return;
    }

    if (!url.trim()) {
      setFetchStatus({ message: "Paste a media URL first.", tone: "error" });
      return;
    }

    setIsFetching(true);
    setFetchStatus({ message: "Fetching API...", tone: "" });

    try {
      const response = await fetch("/api/v1/media/scrape", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token.trim()}`,
        },
        body: JSON.stringify({ url: url.trim() }),
      });

      const payload = await parseResponse(response);
      setResponseText(JSON.stringify(payload, null, 2));

      if (!response.ok) {
        resetSummary();
        setSummary((current) => ({
          ...current,
          description: payload.detail || "Fetch failed.",
        }));
        setFetchStatus({
          message: payload.detail || "Fetch failed.",
          tone: "error",
        });
        return;
      }

      applyPayload(payload);
      setFetchStatus({ message: "Media fetched successfully.", tone: "success" });
    } catch (error) {
      resetSummary();
      setFetchStatus({
        message: `Request failed: ${error.message || String(error)}`,
        tone: "error",
      });
      setResponseText(
        JSON.stringify(
          { detail: `Request failed: ${error.message || String(error)}` },
          null,
          2,
        ),
      );
    } finally {
      setIsFetching(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="dev-badge">DEV</div>
        <h1>Sendit scrape tester</h1>
        <p className="subtitle">
          Paste a social video URL, hit your FastAPI backend, and inspect the returned
          cover image, description, post date, and user details. This React page is
          meant for local development only.
        </p>
      </section>

      <section className="grid">
        <section className="panel stack">
          <div className="panel-header">
            <h2>Session</h2>
            <p>Authenticate once, then reuse your token.</p>
          </div>

          <div className="row">
            <div>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Your password"
              />
            </div>
          </div>

          <div className="actions">
            <button type="button" disabled={isLoggingIn} onClick={login}>
              {isLoggingIn ? "Signing In..." : "Sign In"}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={isCheckingSession}
              onClick={checkSession}
            >
              {isCheckingSession ? "Checking..." : "Check Session"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                saveToken("");
                setAuthStatus({
                  message: "Token cleared from this browser.",
                  tone: "success",
                });
              }}
            >
              Clear Token
            </button>
          </div>

          <div>
            <label htmlFor="token">Bearer Token</label>
            <textarea
              id="token"
              value={token}
              onChange={(event) => saveToken(event.target.value)}
              placeholder="Paste a token here or sign in above."
            />
            <p className="hint">Saved in local storage for quick repeat tests.</p>
          </div>

          <div className="status" data-tone={authStatus.tone}>
            {authStatus.message}
          </div>
        </section>

        <section className="panel stack">
          <div className="panel-header">
            <h2>Fetch</h2>
            <p>Paste any supported URL. The backend decides the platform.</p>
          </div>

          <div>
            <label htmlFor="url">Video URL</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://..."
            />
          </div>

          <div className="actions">
            <button type="button" disabled={isFetching} onClick={fetchMedia}>
              {isFetching ? "Fetching..." : "Fetch Data"}
            </button>
          </div>

          <div className="status" data-tone={fetchStatus.tone}>
            {fetchStatus.message}
          </div>
          <p className="hint">Supported: Instagram Reels, TikTok videos, YouTube Shorts.</p>
        </section>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Returned Data</h2>
          <p>Normalized fields plus the raw JSON payload.</p>
        </div>

        <div className="summary">
          <div className="cover">
            {summary.coverImageUrl ? (
              <img alt="Returned cover image" src={summary.coverImageUrl} />
            ) : (
              <span>No cover image returned yet.</span>
            )}
          </div>

          <div className="meta-grid">
            <article className="meta-card">
              <h3>Description</h3>
              <p>{summary.description}</p>
            </article>
            <article className="meta-card">
              <h3>Post Date</h3>
              <p>{summary.postDate}</p>
            </article>
          </div>

          <article className="meta-card">
            <h3>User</h3>
            <p>{summary.userText}</p>
          </article>
        </div>

        <pre>{responseText}</pre>
      </section>
    </main>
  );
}
