Update the dashboard Favorites feature so favorites are durable across tunnel restarts and shared between Mac + phone, by backing them with a project file and a small local API.

Files to touch:
- scripts/fav_server.py (new)
- scripts/build_dashboard.py (embed favorites snapshot)
- dashboard/app.js (read/write via API + localStorage cache + embedded fallback)
- dashboard/index.html (add fallback script tag if needed)
- dashboard/styles.css (only if needed; likely no change)

## Context
- Dashboard is served by a Python HTTP server on port 8765 from the repo root (/Users/korelgundem/Desktop/first-project). Currently: `python3 -m http.server 8765 --bind 0.0.0.0` (PID 15563). A Cloudflare quick tunnel exposes it publicly; the tunnel URL changes on every restart.
- Current Favorites implementation uses browser localStorage only (key `first-project-favs`). That breaks when the tunnel restarts because the browser origin (the random trycloudflare.com hostname) changes, and it is not shared between Mac and phone browsers.
- Repo root: /Users/korelgundem/Desktop/first-project
- Dashboard files: dashboard/index.html, dashboard/app.js, dashboard/styles.css
- Builder: scripts/build_dashboard.py embeds data/ranked/latest.json as window.__WATCH_DATA__
- State dir: /Users/korelgundem/Desktop/first-project/state/ (already has seen.json)

## Goal
Make favorites durable and shared:
1. Durable store = /Users/korelgundem/Desktop/first-project/state/favorites.json (array of full_name strings). Create it if missing (empty array).
2. Local API on the Python server:
   - GET /api/favs → 200 JSON {favs: [...]} reading state/favorites.json
   - POST /api/favs → body JSON {favs: [...]} (array of strings); validate; write state/favorites.json atomically (write to temp, rename); return 200 {ok: true, favs: [...]}
   - Any other path → serve static files normally (dashboard/, data/, etc.)
   - stdlib only; no new dependencies.
3. build_dashboard.py: also read state/favorites.json and embed as window.__WATCH_FAVS__ in dashboard/index.html (same pattern as __WATCH_DATA__). This is a fallback snapshot for when the server is not reachable (e.g. file URL, tunnel down). Keep __WATCH_DATA__ for ranked repos.
4. app.js:
   - Prefer live data: on init, fetch('/api/favs', {cache:'no-store'}) → set favs from response.favs; also persist to localStorage as cache.
   - Fallback order if fetch fails or server unreachable: window.__WATCH_FAVS__ (if present) → localStorage → [].
   - Star toggle: update in-memory favs, save to localStorage immediately, then fire-and-forget POST /api/favs with {favs: favs} to persist to file. Ignore POST errors (server may be down); UI still updates.
   - refreshFavoritesLane / chip count / copy button continue to work off in-memory favs.
   - Copy favorites button builds the same text block as before.
   - Keep existing card expand behavior; keep mobile touch behavior.
5. index.html: if build_dashboard.py adds the __WATCH_FAVS__ script tag, ensure app.js can read it (it can — window.__WATCH_FAVS__). No other HTML changes needed unless the script tag placement requires it.
6. styles.css: no change unless a small tweak improves the favorites lane; prefer leaving it as is.

## Operational notes
- After implementing, stop the old http.server (PID 15563) and start fav_server.py on port 8765 in the background from repo root.
- The Cloudflare tunnel is already running and points to port 8765; it should continue working with the new server.
- Verify:
  - curl -s http://127.0.0.1:8765/api/favs returns {"favs":[]} initially
  - curl -s -X POST -H 'Content-Type: application/json' -d '{"favs":["acme/demo"]}' http://127.0.0.1:8765/api/favs returns {"ok":true,"favs":["acme/demo"]}
  - state/favorites.json now contains ["acme/demo"]
  - curl -s http://127.0.0.1:8765/api/favs returns {"favs":["acme/demo"]}
  - dashboard still loads at http://127.0.0.1:8765/dashboard/ and shows the Favorites chip and star buttons
- Do not delete existing favorites if any exist; start from empty only if file missing.
- Do not change the ranked-data pipeline or cron job.
- Keep the implementation minimal and robust; avoid over-engineering.
