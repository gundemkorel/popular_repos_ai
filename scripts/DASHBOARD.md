# Dashboard architecture and maintenance notes

This document describes the **current** dashboard. It is no longer a one-time build spec.

Production URL:

`https://gundemkorel.github.io/popular_repos_ai/`

## Files

- `dashboard/index.html` — static HTML shell + embedded ranked data block
- `dashboard/styles.css` — mobile-first styling
- `dashboard/app.js` — rendering, filters, search, username flow, favorites sync
- `dashboard/sync-config.js` — Supabase browser client config
- `scripts/build_dashboard.py` — injects ranked JSON into `index.html`
- `.github/workflows/pages.yml` — builds and deploys the Pages artifact

## Data shape

Primary dashboard data comes from `data/ranked/latest.json`:

```json
{
  "ranked_at": "ISO timestamp",
  "buckets": {
    "coding_agents": {"title": "Coding agents / CLIs", "items": []},
    "skills_plugins": {"title": "Skills / MCP", "items": []},
    "memory_context": {"title": "Memory / context", "items": []},
    "white_collar": {"title": "White-collar / productivity", "items": []},
    "evals": {"title": "Evals / benchmarks", "items": []}
  }
}
```

Repo items may include `full_name`, `html_url`, `description`, `stars`, `forks`, `language`, `created_at`, `pushed_at`, `score`, `star_delta`, `is_new`, `age_days`, and `topics`.

Never invent repo data in the frontend.

## Ranked-data loading

`scripts/build_dashboard.py` embeds ranked JSON into `dashboard/index.html` as:

`window.__WATCH_DATA__`

`dashboard/app.js` prefers that embedded payload. If it is absent, the app tries fetch paths that support both:

- GitHub Pages site-root deployment
- local `/dashboard/` serving

The builder also removes the old global `window.__WATCH_FAVS__` snapshot because favorites are now per username and synced remotely.

## Favorites and username sync

Favorites are not stored in the repository.

The dashboard:

- asks for a username on first use
- remembers it in localStorage
- keeps a per-username local favorites cache
- syncs favorites through Supabase REST
- falls back to local cache when Supabase is unavailable

See:

- `AGENTS.md`
- `scripts/PAGES_SETUP.md`
- `scripts/supabase_favorites.sql`

Username-only access is not authentication. Do not use favorites storage for sensitive information.

## Visual design

Preserve the existing visual language unless a redesign is requested:

- dark near-black background
- warm paper-white text
- amber accent
- system/SF Pro font stack
- mobile-first, max width around 720px
- sticky horizontal bucket chips
- compact repo cards with expandable descriptions
- 44px-class touch targets for mobile controls
- no framework/CDN dependency required for core UI

## Behavior to preserve

- Search filters repo name + description.
- Lane chips filter the ranked buckets.
- Favorites chip/lane renders current user favorites.
- Cards expand/collapse without interfering with star buttons or external links.
- New repos can show a `new` pill.
- `star_delta` can show the `+N / 2d` movement label.
- Copy-favorites exports a plain-text list.
- Missing/empty ranked data shows a quiet failure state; never fabricate content.
- Username control allows switching users.
- Sync status reflects synced/local/degraded state.

## Build and local verification

```bash
python3 scripts/build_dashboard.py
python3 -m py_compile scripts/build_dashboard.py
python3 -m http.server 8765
```

Open:

`http://127.0.0.1:8765/dashboard/`

For JavaScript syntax checking, if Node is available:

```bash
node -e "d=require('fs').readFileSync('dashboard/app.js','utf8');new Function(d);console.log('app.js ok')"
```

## GitHub Pages deployment

`.github/workflows/pages.yml` copies the contents of `dashboard/` to the Pages artifact root and separately copies `data/ranked/latest.json` under `data/ranked/`.

The scheduled digest workflow updates ranked data and the embedded dashboard, commits them to `main`, and that push should trigger Pages.

Do not suppress CI on generated digest commits with `[skip ci]`.
