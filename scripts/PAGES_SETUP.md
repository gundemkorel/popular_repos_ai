# GitHub Pages + synced favorites operations

The production dashboard is deployed at:

`https://gundemkorel.github.io/popular_repos_ai/`

Repo rankings are generated in GitHub; favorites sync through Supabase and are keyed by the username entered in the UI.

## Current production model

```text
GitHub repo / scheduled workflow
        |
        v
ranked JSON + dashboard build
        |
        v
GitHub Pages
        |
        +--> repo data from deployed static artifact
        |
        +--> favorites through Supabase REST API
```

## Supabase

The favorites schema lives in `scripts/supabase_favorites.sql`.

The dashboard client configuration lives in `dashboard/sync-config.js` and contains only:

- Supabase project URL
- browser-safe publishable/anon key

Never put a Supabase secret/service-role key, database password, or other private credential in the repo.

The table is `public.favorites` with primary key `(username, repo)`.

The UI intentionally uses username-only access. Supabase therefore permits anonymous reads/inserts/deletes. This means **username is not authentication**: anyone who knows a username can read or modify that username's favorites. Do not store sensitive data in this table.

## GitHub Pages

Repository Pages source should remain:

**Settings → Pages → Source → GitHub Actions**

`.github/workflows/pages.yml` publishes:

- `dashboard/` as the Pages site root
- `data/ranked/latest.json` as `data/ranked/latest.json`

The workflow triggers on pushes to `main` that change dashboard assets, ranked JSON, or the workflow itself.

### Important CI gotcha

The digest workflow commits generated outputs back to `main`. Those commits must trigger Pages. Do not add `[skip ci]` to the digest commit message, or the public dashboard can stop updating even though ranked data in the repository continues to change.

## Username + favorites behavior

- First visit: user enters a username.
- Username is normalized to lowercase and must match `[a-z0-9._-]{1,32}`.
- Username is remembered in localStorage under `agent-watch-username`.
- Per-user favorites are cached under `agent-watch-favs:<username>`.
- The old browser-wide key `first-project-favs` is used only as a migration fallback.
- The app loads remote favorites from Supabase for the username.
- If the remote list is empty but the local cache has favorites, the app seeds Supabase once.
- Favorite/unfavorite updates local state immediately and then writes to Supabase.
- If remote sync fails, the dashboard continues with local cache and shows a degraded sync status.
- Clicking the username control in the header allows switching usernames.

## Local testing

From repo root:

```bash
python3 scripts/build_dashboard.py
python3 -m py_compile scripts/build_dashboard.py
python3 -m http.server 8765
```

Open:

`http://127.0.0.1:8765/dashboard/`

The dashboard is written to work in both layouts:

- local: `/dashboard/`
- GitHub Pages: site root `/popular_repos_ai/`

## Production verification

After changing dashboard or favorites behavior:

1. Confirm the Pages workflow succeeds after merge to `main`.
2. Open the production site and verify ranked repo data loads.
3. Enter a username and favorite a repo.
4. Refresh and confirm the favorite remains.
5. Open the site in another browser/device, use the same username, and confirm the favorite appears.
6. Remove the favorite on one device and confirm the change is reflected remotely after refresh on the other device.
7. Verify the site still works if Supabase is temporarily unreachable; local cached favorites should remain usable.

## If Supabase must be recreated

1. Create a Supabase project.
2. Run `scripts/supabase_favorites.sql` in the SQL Editor.
3. Copy the Project URL and **publishable/anon** browser key.
4. Update `dashboard/sync-config.js`.
5. Merge to `main` and let Pages redeploy.

No backend server is required for production; GitHub Pages is static hosting and the browser talks directly to Supabase.
