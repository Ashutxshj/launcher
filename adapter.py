"""Adapt leeds intent-sheet rows into the master schema email-automation drafts.

leeds writes a different workbook (Username, Stated Problem, Suggested Opener, …).
email-automation only understands leads_master.xlsx columns and drafts from the
BULLETS column. So for buttons 4/5 we translate each intent row into a master row
whose bullets describe what the person publicly asked for — that's what the LLM
turns into a personalized opener.

Many intent leads reach out only via a forum permalink (no email/phone/IG). For
those, email-automation has no channel and skips them, so we keep leeds' own
`Suggested Opener` on the side as a fallback the orchestrator fills back in.
"""

import os
import re
import sys

import config

sys.path.insert(0, config.EMAIL_AUTOMATION_DIR)
import master_registry as mr   # email-automation's copy — the schema we target

_IG_RE = re.compile(r"(?:instagram\.com/|@)([A-Za-z0-9._]{2,30})", re.I)

# leeds' platform name for the OpenStreetMap sweep.
_OSM_PLATFORM = "directories"


def contactable(rows: list[dict]) -> tuple[list[dict], int]:
    """Intent rows minus the OSM businesses we could never actually contact.
    Returns (kept, dropped).

    An OSM lead is a shop with a phone number and no website: the only way to
    work it is to ring it or WhatsApp it, so a shop outside India is not a lead
    no matter how good the row looks. leeds only sweeps Indian cities now, but
    this filter is what the emailed sheet is actually guaranteed by — the intent
    sheet on disk still holds foreign rows from earlier runs, and `--areas` can
    always be pointed abroad again.

    A blank Country on an OSM row means the city wasn't in leeds' AREA_COUNTRY
    map, i.e. we don't know where it is; unknown is dropped, not assumed.

    Only OSM rows are filtered. A Reddit or Freelancer poster is reachable from
    anywhere, so their country is irrelevant and never checked.
    """
    kept, dropped = [], 0
    for row in rows:
        platform = str(row.get("Platform") or "").strip().lower()
        country = str(row.get("Country") or "").strip().upper()
        if platform == _OSM_PLATFORM and country != "IN":
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def _instagram(row: dict) -> str:
    if str(row.get("Platform") or "").strip().lower() == "instagram":
        return str(row.get("Username") or "").strip().lstrip("@")
    for field in ("Other Profiles", "Website", "Contact Channel"):
        m = _IG_RE.search(str(row.get(field) or ""))
        if m:
            return m.group(1)
    return ""


def _bullets(row: dict) -> str:
    """Fact-only bullets from the public post. First bullet is the opener hook,
    so it must read as a noun phrase ('a website for their dental clinic').

    The permalink is deliberately NOT a bullet. It used to be one, back when the
    bullets column was the only place it could live; it now has its own clickable
    Source Link column, and a raw URL here just cost three wrapped lines of row
    height and gave the drafting model a string it might paste into a message.
    """
    wanted = str(row.get("Service Wanted") or "").strip()
    biz = str(row.get("Business Type") or "").strip()
    problem = str(row.get("Stated Problem") or "").strip()
    budget = str(row.get("Budget Signal") or "").strip()
    excerpt = str(row.get("Post Excerpt") or "").strip()

    out = []
    hook = wanted or "help with their website"
    if biz:
        out.append(f"{hook} for their {biz}")
    else:
        out.append(hook)
    if problem:
        out.append(f"Publicly posted: {problem[:180]}")
    elif excerpt:
        out.append(f"Publicly posted: {excerpt[:180]}")
    if budget:
        out.append(f"Budget signal: {budget[:120]}")
    return "\n".join(f"• {b}" for b in out)


def convert(rows: list[dict]) -> list[dict]:
    """Intent rows -> master-schema rows. Each carries private _opener/_keys that
    the orchestrator strips before writing the sheet."""
    out = []
    for row in rows:
        business = (str(row.get("Username") or "").strip()
                    or str(row.get("Post Title") or "").strip()[:60]
                    or "Unknown")
        master = {col: "" for col in mr.COLUMNS}
        master["Business Name"] = business
        master["Category"] = (str(row.get("Business Type") or "").strip()
                              or str(row.get("Service Wanted") or "").strip())
        master["Lead Type"] = "Intent"
        master["Has_Website"] = str(row.get("Has Website") or "").strip()
        master["Phone Number"] = str(row.get("Phone Number") or "").strip()
        if "WhatsApp Link" in master:
            master["WhatsApp Link"] = str(row.get("WhatsApp") or "").strip()
        master["Email Address"] = str(row.get("Email Address") or "").strip()
        master["Instagram"] = _instagram(row)
        master[mr.BULLETS_COLUMN] = _bullets(row)
        master["Message"] = ""
        master["Reached"] = False
        master["Do Not Contact"] = False

        master["_opener"] = str(row.get("Suggested Opener") or "").strip()
        master["_source_link"] = str(row.get("Permalink") or "").strip()
        master["_keys"] = mr.identity_keys(master)
        out.append(master)
    return out
