# Chillispark Lead Launcher

One page, 5 buttons. Click one, it runs the right tool, adds a personalized
cold-outreach draft to every lead (via `email-automation`), and emails you the
sheet. No venvs, no terminals, no `python main.py`.

## Run it

Double-click **`start.bat`**. Your browser opens `http://127.0.0.1:8765`.
Close the console window to stop.

## The 5 buttons

| # | Button | Tool | Finds |
|---|--------|------|-------|
| 1 | With Website | `scraper` | NCR businesses with a stale website |
| 2 | Without Website | `scraper2` | NCR businesses with no website |
| 3 | Social Media | `scraper3` | Instagram-only NCR businesses |
| 4 | Intented | `leeds` | People who asked for a website in the last 48 hours |
| 5 | Instant | `leeds-hour` | The freshest such leads from the last hour |

Each click emails **only that run's new leads** (not the whole master) to the
address in `launcher/.env` (`LAUNCHER_RECIPIENT`, default `ashutosh06066@gmail.com`).
Nothing is ever sent to a lead. Every message is a draft you review and send by hand.

## Toasts

- **Green**: sent N leads to your email, M with a ready draft.
- **Orange**: an API key hit its rate limit. It names the exact repo `.env` and key
  to swap, e.g. "Apify rate limit, edit `scraper\.env` (APIFY_TOKEN)".
- **Red**: the run or the email failed (reason shown; full log on the page).

## Keys live in each tool's own `.env`

The launcher just orchestrates; the pipeline keys stay where they always were:
`APIFY_TOKEN` in `scraper*/.env`, `GEMINI_API_KEY` in `email-automation/.env` and
`leeds/.env`, `STACKEXCHANGE_KEY` / `REDDIT_*` / `BLUESKY_*` in `leeds/.env`. The
launcher's own send key is `RESEND_API_KEY` in `launcher/.env`.
