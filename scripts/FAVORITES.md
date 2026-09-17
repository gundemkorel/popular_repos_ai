# Favorites — historical note (deprecated implementation)

This file originally specified the first browser-local Favorites feature. That design is **no longer the current production architecture**.

Current behavior:

- favorites are keyed by username
- localStorage is only the per-user cache / offline fallback
- favorites sync across devices through Supabase
- production is hosted on GitHub Pages

Authoritative docs:

- `AGENTS.md` — overall project handoff
- `scripts/PAGES_SETUP.md` — Pages + Supabase operations
- `scripts/DASHBOARD.md` — current dashboard architecture
- `scripts/supabase_favorites.sql` — current remote favorites schema/policies

Legacy detail retained for migration context:

- the old browser-wide key was `first-project-favs`
- current code may read that key once to migrate existing browser favorites into the selected username's per-user cache

Do not reimplement favorites as browser-only storage unless explicitly requested.
