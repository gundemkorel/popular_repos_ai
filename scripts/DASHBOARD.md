Build a mobile-first dashboard for this GitHub agent-watch project.

## Goal
A beautiful, dynamic dashboard showing ranked repos from data/ranked/latest.json. The user will view it on a phone.

## Create these files only

1) dashboard/index.html
2) dashboard/styles.css
3) dashboard/app.js
4) scripts/build_dashboard.py  (stdlib, Python 3.9)

Do not modify collect.py or rank.py. Do not git commit.

## Data shape (data/ranked/latest.json)

{
  "ranked_at": iso,
  "buckets": {
    "coding_agents": { "title": "Coding agents / CLIs", "items": [ {
        "full_name", "html_url", "description", "stars", "forks",
        "language", "created_at", "pushed_at", "score", "star_delta",
        "is_new", "age_days", "topics": []
    } ] },
    ...
  }
}

Bucket ids: coding_agents, skills_plugins, memory_context, white_collar, evals.

## Visual design (must not look like generic AI SaaS)

- Dark, near-black background (#0b0c0f), warm paper-white text, one accent: molten amber #e8a54b
- Font: system-ui / "SF Pro" stack; titles slightly tight tracking
- Mobile-first: max width 720px centered; comfortable tap targets
- Header: "Agent watch" + ranked_at as a human local-ish datetime + count of repos
- Horizontal chip scroller for buckets (sticky under header). First chip = All
- Cards: repo full_name as the title (link out), one-line description, meta row: stars, created date (YYYY-MM-DD), language, optional "+N / 2d" if star_delta not null
- New repos (is_new true) get a small amber "new" pill
- Empty bucket: quiet empty state, no fake data
- Subtle motion: chip active state, card press opacity — no gaudy gradients, no hero illustration, no Inter/purple/glassmorphism cliché
- Footer: "GitHub only · last 6 months · 5 per lane"

## Behavior

- app.js loads window.__WATCH_DATA__ if present, else fetch("../data/ranked/latest.json")
- Filter by chip; search input filters full_name + description
- Cards are <a> to html_url, target=_blank rel=noopener
- If data missing, show "No ranked data yet" and stop. Never invent repos.

## scripts/build_dashboard.py

- Repo root = parent of scripts/
- Read data/ranked/latest.json (if missing, embed {"ranked_at":null,"buckets":{}})
- Read dashboard/index.html
- Inject/replace a tag: <script>window.__WATCH_DATA__ = ...;</script> immediately before </body> (or replace existing __WATCH_DATA__ block)
- Write dashboard/index.html back
- Print path written
- if __name__ == "__main__"

After writing, run:
  python3 scripts/build_dashboard.py
  python3 -m py_compile scripts/build_dashboard.py

Keep CSS/JS small and readable. No frameworks, no CDN except none — zero external requests (phone may be slow).
