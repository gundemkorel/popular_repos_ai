# Agent watch (first-project)

This folder is the workdir for the every-2-days GitHub digest.

## What this project does

Track popular GitHub repos in four buckets:

1. Coding agents / CLIs
2. Skills / plugins / MCP
3. Memory / context
4. White-collar / productivity agents

GitHub only. Cap **5 repos per bucket**.

## Cron tick (do this, in order)

1. If `data/ranked/latest.json` is missing or older than 1 day, run:
   `python3 scripts/collect.py && python3 scripts/rank.py`
2. Read `data/ranked/latest.json` (and `config/watch.json` if needed).
3. Write `digests/YYYY-MM-DD.md` using today's date (local).
4. Append a one-line entry to `logs/runs.log`.
5. Your **final assistant message** is the digest body (Telegram delivery). Do not add process narration.

Do **not** re-scrape GitHub yourself. Do **not** invent repos. Only use ranked JSON.

If ranked JSON is empty or the collector failed, say so in one short paragraph and stop.

## Digest format

```
# Agent GitHub watch — YYYY-MM-DD

One-line theme of this cycle.

## Coding agents / CLIs
- **owner/name** (+N stars / 2d, total S) — one clause what it is
  https://github.com/owner/name

(same for the other four buckets, 5 items max each)

## Themes
- 3 bullets max
```

Skip a bucket if it has no items. Prefer movers (star delta) and newly created repos over stale high-star names unless they moved.

## Constraints

- Hermes cron ticks are short (~3 minutes). Collection belongs in the scripts.
- State is `state/seen.json`. Do not put this in Hermes memory.
