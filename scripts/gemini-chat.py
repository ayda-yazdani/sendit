#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


def load_local_env() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    load_local_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(f"Set GEMINI_API_KEY in {ENV_PATH} or your shell env first.", file=sys.stderr)
        return 1

    prompt = " ".join(sys.argv[1:]).strip()
    if not prompt:
        print("Usage: scripts/gemini-chat.py \"Your prompt here\"", file=sys.stderr)
        return 1

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }

    request = urllib.request.Request(
        f"{API_URL}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(error_body, file=sys.stderr)
        return exc.code or 1

    candidates = body.get("candidates") or []
    if not candidates:
        print(json.dumps(body, indent=2))
        return 0

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if text:
        print(text)
    else:
        print(json.dumps(body, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
