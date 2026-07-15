"""Email a finished leads sheet to YOU via Resend, using only the stdlib.

Mirrors the payload shape of leeds-hour/mailer.py (base64 attachment) but posts
with urllib so the launcher needs no third-party package. This only ever mails
the recipient in config (your gmail) — it never contacts a lead.
"""

import base64
import json
import os
import urllib.error
import urllib.request

import config

RESEND_URL = "https://api.resend.com/emails"


def send(sheet_path: str, subject: str, html_body: str):
    """Send sheet_path as an attachment. Returns (ok, status, detail).

    ok=False with status=None means a local problem (no key / no file); a numeric
    status is Resend's HTTP response. detail is a short human string.
    """
    key = config.RESEND_API_KEY
    if not key:
        return False, None, "RESEND_API_KEY is not set (edit launcher\\.env)"
    if not os.path.exists(sheet_path):
        return False, None, f"sheet not found: {sheet_path}"

    with open(sheet_path, "rb") as fh:
        content = base64.b64encode(fh.read()).decode("ascii")

    payload = {
        "from": config.RESEND_FROM,
        "to": [config.RECIPIENT],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {"filename": os.path.basename(sheet_path), "content": content}
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RESEND_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # Resend is fronted by Cloudflare, which blocks the default
            # "Python-urllib/x.y" agent (403 error code 1010). Look like a client.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) chillispark-launcher/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
            msg_id = ""
            try:
                msg_id = json.loads(body).get("id", "")
            except ValueError:
                pass
            return True, resp.status, f"sent to {config.RECIPIENT} (id {msg_id or '?'})"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        # 429 = rate limit; 403/422 = usually the free-tier recipient/domain rule.
        return False, exc.code, f"Resend refused the send: HTTP {exc.code}: {body}"
    except urllib.error.URLError as exc:
        return False, None, f"could not reach Resend: {exc.reason}"
