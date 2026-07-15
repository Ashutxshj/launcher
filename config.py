"""Launcher configuration: paths, recipient, keys, and the 5 button definitions.

This is the one place that knows where every repo, venv and data file lives, and
how each of the 5 buttons is wired. Nothing here contacts a lead; the launcher
only runs the existing tools and emails the finished sheet to YOU.

Secrets (Resend key) come from launcher/.env so they are never committed.
"""

import os

# --- paths ------------------------------------------------------------------

LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(LAUNCHER_DIR)          # ...\Projects
OUT_DIR = os.path.join(LAUNCHER_DIR, "out")

MASTER_FILE = os.path.join(ROOT, "leads_master.xlsx")
INTENT_FILE = os.path.join(ROOT, "intent_leads.xlsx")
HOUR_FILE = os.path.join(ROOT, "leeds-hour", "hour_leads.xlsx")

EMAIL_AUTOMATION_DIR = os.path.join(ROOT, "email-automation")


def _venv_python(repo: str) -> str:
    return os.path.join(ROOT, repo, ".venv", "Scripts", "python.exe")


# --- .env (tiny loader, no dependency) --------------------------------------

def _load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(os.path.join(LAUNCHER_DIR, ".env"))

# --- settings ---------------------------------------------------------------

# Where every finished sheet is emailed. NEVER the office inbox.
RECIPIENT = os.getenv("LAUNCHER_RECIPIENT", "ashutosh06066@gmail.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv("RESEND_FROM", "Chillispark Leads <onboarding@resend.dev>")

PORT = int(os.getenv("LAUNCHER_PORT", "8765"))

# --- email-automation drafting step -----------------------------------------

EMAIL_AUTOMATION = {
    "python": _venv_python("email-automation"),
    "cwd": EMAIL_AUTOMATION_DIR,
    "args": ["main.py", "--prep"],
}

# --- the 5 buttons ----------------------------------------------------------
# kind: "scraper" -> appends to a master workbook; diff for new rows.
#       "leeds"   -> writes an intent sheet; diff by Permalink, then adapt.
# env_repo: which repo's .env holds the keys, for rate-limit toasts.

BUTTONS = {
    "1": {
        "label": "With Website",
        "subtitle": "NCR businesses with a stale website",
        "kind": "scraper",
        "python": _venv_python("scraper"),
        "cwd": os.path.join(ROOT, "scraper"),
        "args": ["main.py", "--category", "0", "--no-email"],
        "env_repo": "scraper",
    },
    "2": {
        "label": "Without Website",
        "subtitle": "NCR businesses with no website",
        "kind": "scraper",
        "python": _venv_python("scraper2"),
        "cwd": os.path.join(ROOT, "scraper2"),
        "args": ["main.py", "--category", "0", "--no-email"],
        "env_repo": "scraper2",
    },
    "3": {
        "label": "Social Media",
        "subtitle": "Instagram-only NCR businesses",
        "kind": "scraper",
        "python": _venv_python("scraper3"),
        "cwd": os.path.join(ROOT, "scraper3"),
        "args": ["main.py", "--category", "0", "--no-email"],
        "env_repo": "scraper3",
    },
    "4": {
        "label": "Intented",
        "subtitle": "People who asked for a website in the last 48 hours",
        "kind": "leeds",
        # leeds itself has no venv; leeds-hour's venv carries leeds' deps.
        "python": _venv_python("leeds-hour"),
        "cwd": os.path.join(ROOT, "leeds"),
        "args": ["main.py", "all", "--since-hours", "48"],
        "source_file": INTENT_FILE,
        "env_repo": "leeds",
    },
    "5": {
        "label": "Instant",
        "subtitle": "The freshest leads from the last hour",
        "kind": "leeds",
        "python": _venv_python("leeds-hour"),
        "cwd": os.path.join(ROOT, "leeds-hour"),
        "args": ["run.py", "--no-email"],
        "source_file": HOUR_FILE,
        "env_repo": "leeds",
    },
}
