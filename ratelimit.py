"""Turn a line of subprocess output into a rate-limit toast.

The whole point: when an API key is throttled, tell the user WHICH key and WHICH
repo's .env to edit — not a vague "something failed". `repo_hint` is the repo of
the step currently running (e.g. "scraper2", "email-automation", "leeds"), which
is what lets one generic "gave up after N attempts" message resolve to the right
.env (email-automation vs leeds both call Gemini the same way).
"""

import os
import re

import config


def _env_path(repo: str) -> str:
    """Display path like 'scraper2\\.env' (what the user opens to swap the key)."""
    return os.path.join(os.path.basename(repo.rstrip("\\/")) or repo, ".env")


# (compiled regex, provider label, env key name). Matched against each output
# line; repo_hint fills in the .env location at match time.
_RULES = [
    (re.compile(r"Apify (returned|request failed)", re.I), "Apify", "APIFY_TOKEN"),
    (re.compile(r"Places API (4\d\d|429)", re.I), "Google Places", "GOOGLE_PLACES_API_KEY"),
    (re.compile(r"gemini retry", re.I), "Gemini", "GEMINI_API_KEY"),
    (re.compile(r"gave up after \d+ attempts", re.I), "Gemini", "GEMINI_API_KEY"),
    (re.compile(r"\bHTTP 429\b"), "Gemini", "GEMINI_API_KEY"),
    (re.compile(r"Resend refused", re.I), "Resend", "RESEND_API_KEY"),
]

# leeds prints "<platform>: daily quota exhausted (n/m)" — capture the platform
# and point at the matching credential.
_QUOTA_RE = re.compile(r"([A-Za-z_][\w]*)\s*:\s*daily quota exhausted", re.I)
_PLATFORM_KEY = {
    "stackexchange": "STACKEXCHANGE_KEY",
    "stack_exchange": "STACKEXCHANGE_KEY",
    "reddit": "REDDIT_CLIENT_ID",
    "bluesky": "BLUESKY_APP_PASSWORD",
    "gemini": "GEMINI_API_KEY",
}


def detect(line: str, repo_hint: str) -> list[dict]:
    """Return rate-limit hits found in one output line (usually 0)."""
    hits: list[dict] = []

    for rx, provider, key in _RULES:
        if rx.search(line):
            # Resend keys live with the launcher, not the pipeline repo.
            repo = "launcher" if provider == "Resend" else repo_hint
            hits.append({
                "provider": provider,
                "env_key": key,
                "env_path": _env_path(repo),
                "detail": line.strip()[:200],
            })

    m = _QUOTA_RE.search(line)
    if m:
        platform = m.group(1).lower()
        hits.append({
            "provider": platform,
            "env_key": _PLATFORM_KEY.get(platform, platform.upper() + "_KEY"),
            "env_path": _env_path(repo_hint),
            "detail": line.strip()[:200],
        })

    return hits
