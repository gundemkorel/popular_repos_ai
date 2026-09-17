Implement stdlib-only Python 3.9 scripts for this repo. Do not add dependencies. Do not use PyYAML. Config is config/watch.json.

Create:

1) scripts/collect.py
2) scripts/rank.py

## collect.py

- Run as: `python3 scripts/collect.py` from repo root (also work if cwd is scripts/).
- Resolve repo root as parent of scripts/.
- Load config/watch.json.
- Prefer GitHub CLI if present: look for `gh` on PATH, then `~/.local/bin/gh`.
  - Search: `gh search repos <query> --sort stars --order desc --limit N --json fullName,url,description,stargazersCount,forksCount,openIssuesCount,language,createdAt,updatedAt,pushedAt,topics,isArchived,isFork`
    (use whichever json fields gh actually supports; if a field fails, drop it)
  - Seed: `gh api repos/{owner}/{repo}`
  - Fallback if gh missing or fails: urllib to GitHub REST (no requests package):
    - Search: GET https://api.github.com/search/repositories?q=...&sort=stars&order=desc&per_page=N
    - Seed: GET https://api.github.com/repos/{owner}/{repo}
- Auth: if env GITHUB_TOKEN or GH_TOKEN is set, send Authorization: Bearer <token>. Always send User-Agent from config and Accept: application/vnd.github+json.
- Rate limits: if unauthenticated, sleep 6.5s between search calls. If authenticated, sleep 0.3s. On HTTP 403/429, sleep Retry-After or 20s and retry once.
- For each bucket query, search and tag results with bucket id + query.
- Fetch each seed_repos entry; tag with its bucket.
- Skip items whose name (lowercase) contains any exclude_name_substrings.
- Skip if stargazers_count < min_stars unless it is a seed.
- Normalize each repo to:
  full_name, html_url, description, stars, forks, open_issues, language, created_at, pushed_at, topics (list), archived, fork, bucket, source ("search"|"seed"), query (or null)
- Deduplicate by full_name keeping the first, but merge bucket if you want — actually keep a `buckets` list of unique bucket ids seen.
- Write data/raw/YYYY-MM-DD.json and also data/raw/latest.json (same content).
- Print a short summary to stdout: counts per bucket, rate-limit remaining if present in headers.
- Never print tokens.
- Create directories if missing.
- Be robust: one failed query should not abort the whole run; record errors in the JSON under "errors": [].

JSON output shape:
{
  "collected_at": ISO-8601 UTC,
  "errors": [],
  "repos": [ ... ]
}

## rank.py

- Load data/raw/latest.json and config/watch.json.
- Load state/seen.json if present, else {"snapshots": {}, "reported": {}}.
  snapshots: { "owner/name": {"stars": int, "updated_at": iso} }
- For each repo compute:
  - age_days from created_at (min 0.5)
  - days_since_push from pushed_at
  - star_delta = current stars - snapshots[full_name].stars if snapshot else None
  - is_new = created within lookback_days
  - score = 0
      + (star_delta or 0) * 4
      + stars / age_days
      + (20 if is_new else 0)
      + (15 if days_since_push <= 3 else 0)
      + (8 if source seed else 0)
- Drop archived repos. Drop forks unless stars >= 200.
- Assign primary bucket: first of repo["buckets"] if list, else repo["bucket"].
- Sort each bucket by score desc, keep per_bucket (5).
- Prefer diversity: at most 2 repos from the same owner per bucket.
- Write data/ranked/YYYY-MM-DD.json and data/ranked/latest.json:
  {
    "ranked_at": iso,
    "buckets": {
      "coding_agents": { "title": "...", "items": [ {fields + score, star_delta, is_new} ] },
      ...
    }
  }
- Update state/seen.json snapshots with current stars for every collected repo (not only ranked).
- Print how many items per bucket.

## Tests

Add scripts/test_rank.py that:
- writes a tiny fake raw JSON to a temp dir OR monkeypatches paths — simplest: unit-test scoring with a function imported from rank.py
- So: put shared helpers in scripts/lib.py OR make rank.py functions importable without running main (if __name__ == "__main__")
- Test: dedupe, exclude substring, cap 5, owner diversity.

After writing, run:
  python3 scripts/test_rank.py
and fix until it passes.

Do not run live GitHub collect (no network test). Do not git commit. Do not edit watch.json unless a field is missing.
