# Agent watch — project handoff

This repository powers an automated GitHub watcher plus a public, mobile-first dashboard for popular AI-agent repositories.

## Project purpose

Track and rank GitHub repos in five lanes:

1. Coding agents / CLIs
2. Skills / plugins / MCP
3. Memory / context
4. White-collar / productivity agents
5. Evals / benchmarks

The ranked output is capped at **5 repos per lane** and is used both for digests and the dashboard.

## Production dashboard

Live site:

`https://gundemkorel.github.io/popular_repos_ai/`

The site is deployed with GitHub Pages from `.github/workflows/pages.yml`.

Important deployment behavior:

- `dashboard/` is copied to the Pages site root.
- `data/ranked/latest.json` is copied to `data/ranked/latest.json` in the Pages artifact.
- The dashboard works with embedded `window.__WATCH_DATA__` when present and falls back to fetching ranked JSON.
- Pages redeploys when `dashboard/**`, `data/ranked/latest.json`, or the Pages workflow changes on `main`.
- Keep digest-generated commits CI-visible. Do **not** re-add `[skip ci]` to the digest commit message, or Pages will stop updating after scheduled refreshes.

## Favorites architecture

Favorites are cross-device and keyed by a username entered in the dashboard.

Flow:

`browser -> dashboard/app.js -> Supabase REST API -> public.favorites`

Relevant files:

- `dashboard/app.js` — username flow, favorites UI, local cache, Supabase reads/writes
- `dashboard/sync-config.js` — public Supabase project URL + publishable key
- `scripts/supabase_favorites.sql` — table + RLS/policies for username-only favorites
- `scripts/PAGES_SETUP.md` — operational notes

Browser storage:

- username key: `agent-watch-username`
- per-user favorites key prefix: `agent-watch-favs:`
- legacy migration key: `first-project-favs`

Behavior:

- Username is normalized to lowercase.
- Valid usernames match `[a-z0-9._-]{1,32}`.
- LocalStorage is the fast/offline cache.
- On load, the app fetches remote favorites for the username.
- If the remote list is empty but a local cache exists, it seeds Supabase once.
- Favorite/unfavorite updates local state immediately, then writes to Supabase.
- If Supabase is unavailable, the UI continues using the local cache and shows a degraded sync status.

### Security model

The username is **not authentication**. The Supabase table intentionally permits anonymous select/insert/delete so anyone who knows a username can read or modify that username's favorites. This is acceptable only because favorites are non-sensitive data.

Never put a Supabase `service_role`, secret key, database password, GitHub token, or any other private credential in browser code or committed docs. `dashboard/sync-config.js` must contain only a browser-safe publishable/anon key.

## Data / ranking pipeline

Core files:

- `config/watch.json` — searches, buckets, seeds, thresholds
- `scripts/collect.py` — collect GitHub candidates
- `scripts/rank.py` — score, dedupe, cap to 5 per lane, update state
- `scripts/build_dashboard.py` — embed `data/ranked/latest.json` into `dashboard/index.html`
- `data/raw/` — collected JSON
- `data/ranked/latest.json` — current ranked payload used by the dashboard
- `state/seen.json` — snapshots / already-seen state
- `digests/` — digest outputs
- `logs/runs.log` — run log

Do not invent repos or fabricate ranked data. If ranked JSON is empty, treat that as a pipeline failure/empty result rather than filling the UI manually.

## Automation

`.github/workflows/digest.yml` refreshes the data on a true 48-hour cadence:

- GitHub Actions triggers the workflow once per day at `00:00 UTC`.
- A cadence gate computes the UTC Unix-day index and only runs the digest on alternating days.
- This avoids the month-boundary bug of cron expressions such as `*/2` in the day-of-month field, which can produce a 24-hour gap between the last day of one month and the first day of the next.
- `workflow_dispatch` bypasses the cadence gate and always runs immediately.

When the cadence gate allows a run, the workflow:

1. checks out the repo
2. runs `scripts/collect.py`
3. runs `scripts/rank.py`
4. runs `scripts/build_dashboard.py`
5. commits generated outputs back to `main`

`.github/workflows/pages.yml` then deploys the dashboard to GitHub Pages.

GitHub scheduled workflows can start a little later than the nominal cron time under load, but the intended run slots are every 48 hours.

## Manual development

From the repo root:

```bash
python3 scripts/collect.py
python3 scripts/rank.py
python3 scripts/build_dashboard.py
python3 -m py_compile scripts/build_dashboard.py
```

For a simple local dashboard server:

```bash
python3 -m http.server 8765
```

Then open:

`http://127.0.0.1:8765/dashboard/`

The dashboard fetch logic supports both the local `/dashboard/` layout and the GitHub Pages root layout.

## Verification checklist after dashboard/favorites changes

- `dashboard/app.js` still parses as JavaScript.
- `scripts/build_dashboard.py` still runs and embeds ranked data.
- `dashboard/index.html` loads locally.
- Search and lane chips work.
- Cards expand and GitHub links open correctly.
- Username is remembered after refresh.
- Favorites persist after refresh.
- Same username on a second device/browser receives the same remote favorites.
- Removing a favorite syncs remotely as well as locally.
- Pages workflow completes after merge to `main`.
- Production site still loads at the URL above.

## Digest-generation instructions

If explicitly operating as the digest agent rather than a coding/maintenance agent:

1. If `data/ranked/latest.json` is missing or stale, run the collection/ranking scripts instead of scraping ad hoc.
2. Read ranked JSON and `config/watch.json` as needed.
3. Write `digests/YYYY-MM-DD.md`.
4. Append a one-line entry to `logs/runs.log` if that execution path expects it.
5. Keep digest output concise and grounded only in ranked data.

Preferred digest structure:

```md
# Agent GitHub watch — YYYY-MM-DD

One-line theme of this cycle.

## Coding agents / CLIs
- **owner/name** (+N stars / 2d, total S) — one clause what it is
  https://github.com/owner/name

## Themes
- up to 3 bullets
```

Skip empty lanes. Prefer movers and newly created repos over stale high-star repos unless the latter actually moved.

## Change-management guidance

- Preserve the existing dashboard visual language unless the user asks for a redesign.
- Keep the frontend framework-free unless there is a clear reason to change that architecture.
- Prefer small, reviewable changes on a branch + PR for non-trivial edits.
- Update this file and the relevant operational docs whenever deployment, storage, auth/sync, or automation architecture changes.
