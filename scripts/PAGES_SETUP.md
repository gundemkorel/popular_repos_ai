# GitHub Pages + synced favorites setup

The dashboard is deployable as a static GitHub Pages site. Repo rankings stay in GitHub; favorites sync through a tiny Supabase table keyed by the username entered in the UI.

## 1. Create the favorites store

1. Create a Supabase project.
2. Open **SQL Editor** and run `scripts/supabase_favorites.sql`.
3. Open the project **Connect** dialog and copy:
   - Project URL
   - Publishable key (`sb_publishable_...`)
4. Put those values in `dashboard/sync-config.js`.

`sync-config.js` is browser-visible by design. Use only the **publishable** key. Never put a Supabase secret/service-role key in the repo.

Because this dashboard intentionally uses username-only access, anyone who knows a username can read or modify that username's favorites. Do not store sensitive data in this table.

## 2. Enable GitHub Pages

After this branch is merged, open the repository's **Settings → Pages** and set **Source** to **GitHub Actions**.

The `Deploy dashboard to GitHub Pages` workflow publishes:
- `dashboard/` at the Pages site root
- `data/ranked/latest.json` at `data/ranked/latest.json`

The dashboard therefore works at:

`https://gundemkorel.github.io/popular_repos_ai/`

## 3. How sync works

- First visit: enter a username.
- The username is remembered in that browser.
- Favorites are cached locally for fast/offline display.
- With Supabase configured, favorites are loaded from and written to `public.favorites`.
- Use the same username on another device to see the same favorites.
- Clicking the username in the header lets you switch usernames.

The old browser-local key (`first-project-favs`) and embedded legacy favorites snapshot are used only as migration fallbacks. If the new remote list is empty on first sync, cached favorites are seeded into Supabase.
