# first-project — agent GitHub watch

Every-other-day digest of GitHub repos people are actually using in the AI-agent stack: coding CLIs, skills/plugins/MCP, memory systems, and white-collar/productivity agents.

## Layout

- `config/watch.json` — queries, buckets, seeds, thresholds
- `scripts/collect.py` — GitHub Search + seed fetch (stdlib only)
- `scripts/rank.py` — score, dedupe, 5 per bucket, update snapshots
- `data/raw/` — collector JSON
- `data/ranked/` — ranked JSON (`latest.json` pointer)
- `state/seen.json` — star snapshots + already-reported ids
- `digests/` — human logs
- `logs/runs.log` — run log

## Manual run

```bash
cd ~/Desktop/first-project
python3 scripts/collect.py
python3 scripts/rank.py
```

Optional: set `GITHUB_TOKEN` or `GH_TOKEN` in the environment for a higher API rate limit. Unauthenticated works, slower.

## Schedule

Hermes cron, every 2 days, delivers the digest to Telegram and writes `digests/`.
