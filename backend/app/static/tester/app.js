(function () {
  const storageKey = "sendit-tester-token";
  const tokenField = document.getElementById("token");
  const authStatus = document.getElementById("authStatus");
  const fetchStatus = document.getElementById("fetchStatus");
  const responseOutput = document.getElementById("responseOutput");
  const coverBox = document.getElementById("coverBox");
  const descriptionValue = document.getElementById("descriptionValue");
  const postDateValue = document.getElementById("postDateValue");
  const userValue = document.getElementById("userValue");

  tokenField.value = localStorage.getItem(storageKey) || "";

  function setStatus(element, message, tone) {
    element.textContent = message;
    element.dataset.tone = tone || "";
  }

  function saveToken(token) {
    tokenField.value = token || "";
    if (token) {
      localStorage.setItem(storageKey, token);
    } else {
      localStorage.removeItem(storageKey);
    }
  }

  function renderCover(url) {
    if (!url) {
      coverBox.innerHTML = "<span>No cover image returned.</span>";
      return;
    }

    coverBox.innerHTML = '<img alt="Returned cover image" src="' + url + '" />';
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

  function resetSummary() {
    renderCover(null);
    descriptionValue.textContent = "Nothing fetched yet.";
    postDateValue.textContent = "Nothing fetched yet.";
    userValue.textContent = "Nothing fetched yet.";
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
      body: JSON.stringify({ email, password }),
    });

    const payload = await parseResponse(response);
    responseOutput.textContent = JSON.stringify(payload, null, 2);

    if (!response.ok) {
      setStatus(
        authStatus,
        payload.detail || payload.message || "Login failed.",
        "error",
      );
      return;
    }

    const accessToken = payload.session && payload.session.access_token;
    saveToken(accessToken || "");
    setStatus(authStatus, "Signed in and token stored.", "success");
  }

  async function checkSession() {
    const token = tokenField.value.trim();
    if (!token) {
      setStatus(authStatus, "Paste or generate an access token first.", "error");
      return;
    }

    setStatus(authStatus, "Checking session...");

    const response = await fetch("/api/v1/auth/me", {
      headers: { Authorization: "Bearer " + token },
    });

    const payload = await parseResponse(response);
    responseOutput.textContent = JSON.stringify(payload, null, 2);

    if (!response.ok) {
      setStatus(authStatus, payload.detail || "Session check failed.", "error");
      return;
    }

    setStatus(authStatus, "Token is valid.", "success");
  }

  async function fetchMedia() {
    const token = tokenField.value.trim();
    const url = document.getElementById("url").value.trim();

    if (!token) {
      setStatus(fetchStatus, "A bearer token is required.", "error");
      return;
    }

    if (!url) {
      setStatus(fetchStatus, "Paste a media URL first.", "error");
      return;
    }

    setStatus(fetchStatus, "Fetching API...");

    const response = await fetch("/api/v1/media/scrape", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({ url }),
    });

    const payload = await parseResponse(response);
    responseOutput.textContent = JSON.stringify(payload, null, 2);

    if (!response.ok) {
      resetSummary();
      descriptionValue.textContent = payload.detail || "Fetch failed.";
      setStatus(fetchStatus, payload.detail || "Fetch failed.", "error");
      return;
    }

    renderCover(payload.cover_image_url || payload.thumbnail_url || null);
    descriptionValue.textContent = payload.description || "No description returned.";
    postDateValue.textContent =
      payload.post_date || payload.published_at || "No post date returned.";
    renderUser(payload.user || payload.author || payload.channel || null);
    setStatus(fetchStatus, "Media fetched successfully.", "success");
  }

  document.getElementById("loginButton").addEventListener("click", login);
  document.getElementById("meButton").addEventListener("click", checkSession);
  document.getElementById("clearTokenButton").addEventListener("click", function () {
    saveToken("");
    setStatus(authStatus, "Token cleared from this browser.", "success");
  });
  document.getElementById("fetchButton").addEventListener("click", fetchMedia);
})();
