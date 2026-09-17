Update scripts/rank.py only (and tests). Config is already in config/watch.json.

New ranking rules:

1. Seed map: config.seed_repos list of {repo, bucket}. Those full_names ALWAYS classify to that bucket.

2. For non-seeds, classify with keywords:
   - blob = lowercase full_name + description + " ".join(topics)
   - For each bucket, hits = count of keywords that appear in blob
   - If any negative_keywords for that bucket appear, that bucket scores 0
   - Winner = bucket with max hits; require hits >= config.min_keyword_hits (default 1)
   - On tie, prefer the repo's existing primary_bucket if it is among the tied, else first max
   - If no bucket reaches min hits, DROP the repo (noise)

3. Ranking per bucket:
   - Sort by score (existing score_repo)
   - Reserve config.seed_slots_per_bucket (default 2) slots for seeds of that bucket (highest score among seeds)
   - Fill remaining slots from non-seeds
   - Still max 2 repos per owner
   - Cap per_bucket total (5)

4. Keep existing score_repo math. Bump seed source bonus from 8 to 25.

5. Tests in scripts/test_rank.py:
   - seed forced into its bucket even if description looks like a skill
   - ponytail/yagni-style repo without memory keywords is NOT in memory_context
   - mem0-like repo lands in memory_context
   - cap still 5
   - seed slots: if 3 seeds and 10 others, at least 1-2 seeds appear when seed_slots=2

Run python3 scripts/test_rank.py until pass. Do not call GitHub. Do not edit collect.py unless a tiny import is needed.
