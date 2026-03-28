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
    platform: null,
    coverImageUrl: null,
    videoUrl: null,
    embedUrl: null,
    canonicalUrl: null,
    description: "Nothing fetched yet.",
    postDate: "Nothing fetched yet.",
    userText: "Nothing fetched yet.",
  };
}

function emptyConfigSummary() {
  return {
    apiBaseUrl: "Detecting...",
    supabaseUrl: "Loading from backend .env...",
    authUrl: "Loading from backend .env...",
    keyName: "Loading from backend .env...",
    keyPresent: "Loading from backend .env...",
    signupMode: "Not checked yet.",
    providers: "Not checked yet.",
  };
}

function formatProviders(external) {
  if (!external || typeof external !== "object") {
    return "No provider data returned.";
  }

  const enabled = Object.entries(external)
    .filter(([, isEnabled]) => Boolean(isEnabled))
    .map(([provider]) => provider);

  return enabled.length > 0 ? enabled.join(", ") : "No enabled providers returned.";
}

async function parseResponse(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch (_error) {
    return { raw: text };
  }
}

function apiUrl(path) {
  if (typeof window === "undefined") {
    return path;
  }

  const { protocol, hostname, port } = window.location;
  const isFrontendDevPort = port && port !== "8000";
  const isLocalhost = hostname === "127.0.0.1" || hostname === "localhost";

  if (isLocalhost && isFrontendDevPort) {
    return `${protocol}//${hostname}:8000${path}`;
  }

  return path;
}

async function loadRuntimeInfo() {
  const response = await fetch(apiUrl("/api/v1/auth/runtime"));
  return parseResponse(response);
}

export default function App() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");
  const [configStatus, setConfigStatus] = useState({
    message: "Checking Supabase configuration...",
    tone: "",
  });
  const [authStatus, setAuthStatus] = useState({ message: "", tone: "" });
  const [fetchStatus, setFetchStatus] = useState({ message: "", tone: "" });
  const [responseText, setResponseText] = useState("{}");
  const [summary, setSummary] = useState(emptySummary());
  const [configSummary, setConfigSummary] = useState(emptyConfigSummary());
  const [isCheckingConfig, setIsCheckingConfig] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [videoPlaybackError, setVideoPlaybackError] = useState("");

  useEffect(() => {
    setToken(localStorage.getItem(storageKey) || "");
    void fetchRuntimeInfo();
    void checkSupabaseConfig({ updateResponse: false });
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
    setVideoPlaybackError("");
  }

  function applyPayload(payload) {
    setVideoPlaybackError("");
    setSummary({
      platform: payload.platform || null,
      coverImageUrl: payload.cover_image_url || null,
      videoUrl: payload.video_url || null,
      embedUrl: payload.embed_url || null,
      canonicalUrl: payload.canonical_url || payload.resolved_url || payload.requested_url || null,
      description: payload.description || "No description returned.",
      postDate: payload.post_date || "No post date returned.",
      userText: prettyUser(payload.user),
    });
  }

  function applyConfigSummary(payload) {
    setConfigSummary((current) => ({
      apiBaseUrl: payload.api_base_url || current.apiBaseUrl,
      supabaseUrl: payload.supabase_url || current.supabaseUrl || "Not returned.",
      authUrl: payload.auth_url || current.authUrl || "Not returned.",
      keyName: payload.key_name || current.keyName,
      keyPresent:
        typeof payload.key_present === "boolean"
          ? payload.key_present
            ? "Yes"
            : "No"
          : current.keyPresent,
      signupMode:
        payload.disable_signup === true
          ? "Disabled"
          : payload.disable_signup === false
            ? "Enabled"
            : current.signupMode,
      providers:
        payload.external !== undefined
          ? formatProviders(payload.external)
          : current.providers,
    }));
  }

  async function fetchRuntimeInfo() {
    try {
      const payload = await loadRuntimeInfo();
      applyConfigSummary(payload);
    } catch (error) {
      setConfigSummary((current) => ({
        ...current,
        apiBaseUrl: apiUrl(""),
        supabaseUrl: `Runtime load failed: ${error.message || String(error)}`,
        authUrl: `Runtime load failed: ${error.message || String(error)}`,
        keyName: "Runtime load failed",
        keyPresent: "Unknown",
      }));
    }
  }

  async function checkSupabaseConfig(options = {}) {
    const { updateResponse = true } = options;

    setIsCheckingConfig(true);
    setConfigStatus({ message: "Checking Supabase configuration...", tone: "" });

    try {
      const response = await fetch(apiUrl("/api/v1/auth/config-check"));
      const payload = await parseResponse(response);

      if (updateResponse) {
        setResponseText(JSON.stringify(payload, null, 2));
      }

      if (!response.ok) {
        setConfigStatus({
          message: payload.detail || "Supabase config check failed.",
          tone: "error",
        });
        return;
      }

      applyConfigSummary(payload);
      setConfigStatus({
        message:
          payload.message || "Supabase Auth is reachable with the configured key.",
        tone: "success",
      });
    } catch (error) {
      setConfigStatus({
        message: `Supabase config check failed: ${error.message || String(error)}`,
        tone: "error",
      });
      if (updateResponse) {
        setResponseText(
          JSON.stringify(
            { detail: `Supabase config check failed: ${error.message || String(error)}` },
            null,
            2,
          ),
        );
      }
    } finally {
      setIsCheckingConfig(false);
    }
  }

  async function register() {
    if (!email.trim() || !password) {
      setAuthStatus({ message: "Enter both email and password.", tone: "error" });
      return;
    }

    setIsRegistering(true);
    setAuthStatus({ message: "Creating account...", tone: "" });

    try {
      const requestBody = {
        email: email.trim(),
        password,
      };

      if (displayName.trim()) {
        requestBody.metadata = { name: displayName.trim() };
      }

      const response = await fetch(apiUrl("/api/v1/auth/signup"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const payload = await parseResponse(response);
      setResponseText(JSON.stringify(payload, null, 2));

      if (!response.ok) {
        setAuthStatus({
          message: payload.detail || payload.message || "Registration failed.",
          tone: "error",
        });
        return;
      }

      if (payload.session?.access_token) {
        saveToken(payload.session.access_token);
        setAuthStatus({ message: "Registered and signed in.", tone: "success" });
        return;
      }

      setAuthStatus({
        message:
          payload.message ||
          "Registered successfully. Check your email if confirmation is enabled.",
        tone: "success",
      });
    } catch (error) {
      setAuthStatus({
        message: `Registration request failed: ${error.message || String(error)}`,
        tone: "error",
      });
    } finally {
      setIsRegistering(false);
    }
  }

  async function login() {
    if (!email.trim() || !password) {
      setAuthStatus({ message: "Enter both email and password.", tone: "error" });
      return;
    }

    setIsLoggingIn(true);
    setAuthStatus({ message: "Signing in...", tone: "" });

    try {
      const response = await fetch(apiUrl("/api/v1/auth/login"), {
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
      const response = await fetch(apiUrl("/api/v1/auth/me"), {
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
      const response = await fetch(apiUrl("/api/v1/media/scrape"), {
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
          Check that the configured Supabase project key works, register or sign in,
          then paste a supported social video URL and inspect the returned cover image,
          description, post date, and user details. This React page is meant for local
          development only.
        </p>
      </section>

      <section className="grid">
        <section className="panel stack">
          <div className="panel-header">
            <h2>Session</h2>
            <p>Verify Supabase first, then register or sign in.</p>
          </div>

          <div className="meta-grid">
            <article className="meta-card">
              <h3>API Base</h3>
              <p>{configSummary.apiBaseUrl}</p>
            </article>
            <article className="meta-card">
              <h3>Project URL</h3>
              <p>{configSummary.supabaseUrl}</p>
            </article>
            <article className="meta-card">
              <h3>Auth URL</h3>
              <p>{configSummary.authUrl}</p>
            </article>
            <article className="meta-card">
              <h3>Env Key</h3>
              <p>
                {configSummary.keyName} ({configSummary.keyPresent})
              </p>
            </article>
            <article className="meta-card">
              <h3>Signups</h3>
              <p>{configSummary.signupMode}</p>
            </article>
            <article className="meta-card">
              <h3>Providers</h3>
              <p>{configSummary.providers}</p>
            </article>
          </div>

          <div className="actions">
            <button
              type="button"
              className="secondary"
              disabled={isCheckingConfig}
              onClick={() => checkSupabaseConfig()}
            >
              {isCheckingConfig ? "Checking..." : "Check Supabase"}
            </button>
          </div>

          <div className="status" data-tone={configStatus.tone}>
            {configStatus.message}
          </div>

          <div className="row">
            <div>
              <label htmlFor="display-name">Display Name</label>
              <input
                id="display-name"
                type="text"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Optional name"
              />
            </div>
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
          </div>

          <div>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
            />
          </div>

          <div className="actions">
            <button type="button" disabled={isRegistering} onClick={register}>
              {isRegistering ? "Registering..." : "Register"}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={isLoggingIn}
              onClick={login}
            >
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
                <h3>Video</h3>
                {summary.videoUrl || summary.embedUrl || summary.canonicalUrl ? (
                  <div className="media-stack">
                    {summary.videoUrl ? (
                      <video
                        key={summary.videoUrl}
                        className="video-preview"
                        controls
                        preload="metadata"
                        src={summary.videoUrl}
                        onError={() => {
                          setVideoPlaybackError(
                            "Direct video playback is blocked by this provider. Use the embed or open the original post.",
                          );
                        }}
                      />
                    ) : null}
                    {videoPlaybackError ? (
                      <p className="media-note">{videoPlaybackError}</p>
                    ) : null}
                    {summary.embedUrl ? (
                      <iframe
                        className="embed-preview"
                        src={summary.embedUrl}
                        title="Embedded media preview"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    ) : null}
                    {summary.videoUrl ? (
                      <a
                        className="media-link"
                        href={summary.videoUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open direct video URL
                      </a>
                    ) : null}
                    {summary.embedUrl ? (
                      <a
                        className="media-link"
                        href={summary.embedUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open embed URL
                      </a>
                    ) : null}
                    {summary.canonicalUrl ? (
                      <a
                        className="media-link"
                        href={summary.canonicalUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original post
                      </a>
                    ) : null}
                  </div>
                ) : (
                  <p>No video URL returned.</p>
                )}
              </article>
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
