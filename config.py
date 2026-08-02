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

# --- dropdown option lists, read from the tool repos -------------------------

def _list_from_config(repo: str, varname: str) -> list:
    """A list-of-strings constant out of another repo's config.py, via ast —
    no import, so the other config's side effects (dotenv loads, env mutation)
    never run in the launcher process, and the module name can't collide with
    this one. [] if the repo/constant is missing — the UI hides that card."""
    import ast
    path = os.path.join(ROOT, repo, "config.py")
    if not os.path.exists(path):
        return []
    try:
        tree = ast.parse(open(path, "r", encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == varname
                            for t in node.targets)):
                value = ast.literal_eval(node.value)
                return [str(v) for v in value] if isinstance(value, list) else []
    except (OSError, SyntaxError, ValueError):
        pass
    return []


NICHES = _list_from_config("Niche", "NICHES")
SCRAPER3_CATEGORIES = _list_from_config("scraper3", "BUSINESS_CATEGORIES")

# --- the 6 buttons ----------------------------------------------------------
# kind: "scraper" -> appends to a master workbook; diff for new rows.
#       "leeds"   -> writes an intent sheet; diff by Permalink, then adapt.
#       "dm"      -> scraper3 DM mode; emails the 10-link sheet it wrote.
#       "niche"   -> Niche tool; emails the one-liner sheet it wrote.
# env_repo: which repo's .env holds the keys, for rate-limit toasts.
# options: dropdown choices shown on the card; the pick arrives as params.choice.

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
        "subtitle": "Pick a category, get 10 Instagram-only businesses with DM links",
        "kind": "dm",
        "python": _venv_python("scraper3"),
        "cwd": os.path.join(ROOT, "scraper3"),
        "env_repo": "scraper3",
        "options": SCRAPER3_CATEGORIES,
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
    "6": {
        "label": "Niche",
        "subtitle": "Pick one niche, get its no-website businesses with a one-line pitch",
        "kind": "niche",
        "python": _venv_python("Niche"),
        "cwd": os.path.join(ROOT, "Niche"),
        "env_repo": "Niche",
        "options": NICHES,
    },
}
