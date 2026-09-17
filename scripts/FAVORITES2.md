# Favorites v2 — historical note (deprecated local-server design)

This document described an intermediate architecture that used:

- a local Python favorites server
- `state/favorites.json`
- `/api/favs`
- an embedded `window.__WATCH_FAVS__` snapshot
- a Cloudflare tunnel

That design has been superseded and is **not production**.

Current production architecture:

- GitHub Pages hosts the static dashboard.
- Favorites are keyed by username.
- Favorites sync directly from the browser to Supabase using the browser-safe publishable/anon key.
- LocalStorage is only a per-username cache / offline fallback.
- `scripts/build_dashboard.py` embeds ranked repo data only and removes any old global favorites snapshot.

The old `scripts/fav_server.py` may remain in the repository for historical/local experimentation, but new work should not depend on it unless the user explicitly chooses to return to a self-hosted backend.

Authoritative docs:

- `AGENTS.md`
- `scripts/PAGES_SETUP.md`
- `scripts/DASHBOARD.md`
- `scripts/supabase_favorites.sql`

Do not restore `/api/favs`, Cloudflare-tunnel assumptions, or global repo-level favorites state as part of normal maintenance.
