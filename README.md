# popular_repos_ai — agent GitHub watch

Automated GitHub watcher + public dashboard for repos people are actively using across the AI-agent stack: coding agents/CLIs, skills/plugins/MCP, memory/context systems, white-collar/productivity agents, and evals/benchmarks.

## Live dashboard

`https://gundemkorel.github.io/popular_repos_ai/`

The dashboard is mobile-first, supports search and lane filters, and has username-based favorites that sync across devices through Supabase.

> Username-only access is intentionally lightweight and is **not real authentication**. Favorites are non-sensitive data; anyone who knows a username could read or modify that username's favorites.

## Architecture

```text
GitHub Actions digest workflow
        |
        v
collect.py -> rank.py -> data/ranked/latest.json
        |                       |
        |                       v
        +-> build_dashboard.py -> dashboard/index.html
                                |
                                v
                         GitHub Pages
                                |
                +---------------+---------------+
                |                               |
                v                               v
          ranked repo data              Supabase favorites
                                        (keyed by username)
```

## Repository layout

- `config/watch.json` — queries, buckets, seeds, thresholds
- `scripts/collect.py` — GitHub collection
- `scripts/rank.py` — scoring, dedupe, 5 per lane, state updates
- `scripts/build_dashboard.py` — embeds ranked JSON into the dashboard
- `scripts/supabase_favorites.sql` — favorites table and anonymous RLS policies
- `scripts/PAGES_SETUP.md` — Pages + Supabase operational notes
- `dashboard/index.html` — dashboard shell
- `dashboard/app.js` — rendering, filtering, username flow, favorites sync
- `dashboard/styles.css` — mobile-first visual styling
- `dashboard/sync-config.js` — browser-safe Supabase project URL + publishable key
- `data/raw/` — collected JSON
- `data/ranked/` — ranked JSON (`latest.json` is the current payload)
- `state/seen.json` — star snapshots / seen state
- `digests/` — generated digest history
- `logs/runs.log` — run log
- `.github/workflows/digest.yml` — scheduled data refresh + generated-file commit
- `.github/workflows/pages.yml` — GitHub Pages deployment

## Favorites sync

The dashboard remembers a username in localStorage and stores favorites in two places:

1. per-username local cache for immediate/offline behavior
2. Supabase `public.favorites` for cross-device sync

Use the same username on another browser/device to see the same favorites.

Relevant browser storage keys:

- `agent-watch-username`
- `agent-watch-favs:<username>`
- legacy migration key: `first-project-favs`

Only a Supabase publishable/anon key belongs in `dashboard/sync-config.js`. Never commit service-role keys, database passwords, or other secrets.

## Manual run

From the repo root:

```bash
python3 scripts/collect.py
python3 scripts/rank.py
python3 scripts/build_dashboard.py
```

Optional: set `GITHUB_TOKEN` or `GH_TOKEN` for a higher GitHub API rate limit.

To serve the dashboard locally:

```bash
python3 -m http.server 8765
```

Then open:

`http://127.0.0.1:8765/dashboard/`

## Deployment

GitHub Pages is configured to deploy through GitHub Actions. The Pages workflow publishes the dashboard at the site root and copies `data/ranked/latest.json` into the deployed artifact.

The digest refresh runs every **48 hours**. The workflow is triggered daily at `00:00 UTC`, then an alternating-day cadence gate runs the expensive collection/ranking/build steps only on every second UTC day. Manual workflow dispatches always run immediately.

The digest workflow commits refreshed `data/` and `dashboard/` outputs to `main`; that push triggers the Pages workflow so production stays current.

Do not add `[skip ci]` to those generated digest commits, because doing so would suppress the Pages redeploy.

## Agent handoff

Coding agents should read `AGENTS.md` before making changes. It contains the current architecture, sync model, deployment gotchas, testing checklist, and digest-specific instructions.
