"""Rank collected repos. Stdlib only, Python 3.9 compatible."""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


def repo_root():
    return Path(__file__).resolve().parent.parent


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError):
        return default


def parse_dt(s):
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip()
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def primary_bucket(repo):
    buckets = repo.get("buckets")
    if isinstance(buckets, list) and buckets:
        return buckets[0]
    return repo.get("bucket", "")


def build_seed_map(config):
    m = {}
    for s in config.get("seed_repos", []) or []:
        if isinstance(s, dict):
            repo = s.get("repo", "")
            bucket = s.get("bucket", "")
            if repo and bucket:
                m[str(repo).lower()] = bucket
    return m


def classify_bucket(repo, buckets_order, seed_map, min_hits):
    full_name = repo.get("full_name") or ""
    lower_name = str(full_name).lower()
    if lower_name in seed_map:
        return seed_map[lower_name]
    has_any_keywords = False
    for b in buckets_order or []:
        kws = b.get("keywords", []) or []
        if kws:
            has_any_keywords = True
            break
    if not has_any_keywords:
        return primary_bucket(repo) or None
    desc = repo.get("description") or ""
    if not isinstance(desc, str):
        desc = str(desc)
    topics = repo.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    topics_str = " ".join([str(t) for t in topics if t])
    blob = ((full_name or "") + " " + desc + " " + topics_str).lower()
    topics_l = [str(t).lower() for t in topics]
    if "book" in topics_l:
        return None
    repo_short = lower_name.split("/")[-1] if "/" in lower_name else lower_name
    if "memory" in repo_short or "mem0" in repo_short:
        return "memory_context"
    if "eval" in repo_short or "bench" in repo_short:
        return "evals"
    if "skill" in repo_short:
        return "skills_plugins"
    scored = []
    for b in buckets_order or []:
        bid = b.get("id")
        if not bid:
            continue
        kws = b.get("keywords", []) or []
        negs = b.get("negative_keywords", []) or []
        neg_hit = False
        for nk in negs:
            if not nk:
                continue
            nk_low = nk.lower() if isinstance(nk, str) else str(nk).lower()
            if nk_low and nk_low in blob:
                neg_hit = True
                break
        if neg_hit:
            scored.append((bid, 0))
            continue
        hits = 0
        for kw in kws:
            if not kw:
                continue
            kw_low = kw.lower() if isinstance(kw, str) else str(kw).lower()
            if kw_low and kw_low in blob:
                hits += 1
        scored.append((bid, hits))
    if not scored:
        return primary_bucket(repo) or None
    max_hits = max(h for _, h in scored)
    if max_hits < min_hits:
        return None
    tied = [bid for bid, h in scored if h == max_hits]
    if len(tied) == 1:
        return tied[0]
    pb = primary_bucket(repo)
    if pb in tied:
        return pb
    return tied[0]


def is_seed_item(item, bid, seed_map):
    if item.get("source") == "seed":
        return True
    full = (item.get("full_name") or "")
    try:
        low = str(full).lower()
    except Exception:
        return False
    return seed_map.get(low) == bid


def is_excluded(full_name, excludes):
    name = (full_name or "").lower()
    for sub in excludes or []:
        if sub and sub.lower() in name:
            return True
    return False


def dedupe_repos(repos):
    seen = {}
    order = []
    for r in repos:
        name = r.get("full_name") or ""
        if not name:
            continue
        if name not in seen:
            if "buckets" not in r or not isinstance(r.get("buckets"), list):
                b = r.get("bucket")
                r["buckets"] = [b] if b else []
            seen[name] = r
            order.append(name)
        else:
            existing = seen[name]
            eb = existing.get("buckets")
            if not isinstance(eb, list):
                eb = [existing.get("bucket")] if existing.get("bucket") else []
                existing["buckets"] = eb
            for b in r.get("buckets", []) or ([r.get("bucket")] if r.get("bucket") else []):
                if b and b not in eb:
                    eb.append(b)
    return [seen[n] for n in order]


def score_repo(repo, snapshot_stars, now, lookback_days):
    stars = int(repo.get("stars", 0) or 0)
    created = parse_dt(repo.get("created_at"))
    pushed = parse_dt(repo.get("pushed_at"))
    if created is not None:
        age_days = (now - created).total_seconds() / 86400.0
    else:
        age_days = 365.0
    age_days = max(age_days, 0.5)
    if pushed is not None:
        days_since_push = (now - pushed).total_seconds() / 86400.0
    else:
        days_since_push = 9999.0
    if snapshot_stars is not None:
        try:
            star_delta = stars - int(snapshot_stars)
        except (TypeError, ValueError):
            star_delta = None
    else:
        star_delta = None
    is_new = bool(created is not None and age_days <= lookback_days)
    score = 0.0
    score += (star_delta or 0) * 4
    score += stars / age_days
    if is_new:
        score += 20
    if days_since_push <= 3:
        score += 15
    if repo.get("source") == "seed":
        score += 25
    return {
        "score": score,
        "star_delta": star_delta,
        "is_new": is_new,
        "age_days": age_days,
        "days_since_push": days_since_push,
    }


def rank_repos(repos, config, seen, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    lookback = config.get("lookback_days", 14)
    try:
        lookback = int(lookback)
    except (TypeError, ValueError):
        lookback = 14
    if not lookback:
        lookback = 14
    per_bucket = config.get("per_bucket", 5)
    try:
        per_bucket = int(per_bucket)
    except (TypeError, ValueError):
        per_bucket = 5
    if not per_bucket:
        per_bucket = 5
    seed_slots = config.get("seed_slots_per_bucket", 2)
    try:
        seed_slots = int(seed_slots)
    except (TypeError, ValueError):
        seed_slots = 2
    if seed_slots is None:
        seed_slots = 2
    min_hits = config.get("min_keyword_hits", 1)
    try:
        min_hits = int(min_hits)
    except (TypeError, ValueError):
        min_hits = 1
    if min_hits is None:
        min_hits = 1
    snapshots = (seen or {}).get("snapshots", {}) or {}
    excludes = config.get("exclude_name_substrings", [])
    exclude_exact = set(
        (x or "").lower() for x in (config.get("exclude_full_names") or []) if x
    )
    max_age = config.get("max_age_days", 0)
    try:
        max_age = int(max_age or 0)
    except (TypeError, ValueError):
        max_age = 0

    buckets_order = [b for b in config.get("buckets", []) if isinstance(b, dict) and b.get("id")]
    buckets_cfg = {b.get("id"): b for b in buckets_order}
    seed_map = build_seed_map(config or {})
    grouped = {}

    for repo in repos or []:
        if not isinstance(repo, dict):
            continue
        full_name = repo.get("full_name") or ""
        if not full_name:
            continue
        if is_excluded(full_name, excludes):
            continue
        if full_name.lower() in exclude_exact:
            continue
        if repo.get("archived"):
            continue
        if repo.get("fork") and int(repo.get("stars", 0) or 0) < 200:
            continue
        if max_age > 0:
            created = parse_dt(repo.get("created_at"))
            if created is not None:
                age = (now - created).total_seconds() / 86400.0
                if age > max_age:
                    continue
        bid = classify_bucket(repo, buckets_order, seed_map, min_hits)
        if not bid:
            continue
        snap = snapshots.get(full_name) or {}
        snap_stars = snap.get("stars")
        comp = score_repo(repo, snap_stars, now, lookback)
        item = dict(repo)
        item.update(comp)
        grouped.setdefault(bid, []).append(item)

    result = {}
    all_ids = set(list(buckets_cfg.keys()) + list(grouped.keys()))
    for bid in all_ids:
        title = buckets_cfg.get(bid, {}).get("title", bid)
        items = grouped.get(bid, [])
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        seeds = [it for it in items if is_seed_item(it, bid, seed_map)]
        non_seeds = [it for it in items if not is_seed_item(it, bid, seed_map)]
        picked = []
        owner_counts = {}
        reserve = min(seed_slots, per_bucket) if seed_slots >= 0 else 0
        for it in seeds:
            if len(picked) >= reserve:
                break
            owner = (it.get("full_name") or "").split("/")[0].lower()
            if owner_counts.get(owner, 0) >= 2:
                continue
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
            picked.append(it)
        for it in non_seeds:
            if len(picked) >= per_bucket:
                break
            owner = (it.get("full_name") or "").split("/")[0].lower()
            if owner_counts.get(owner, 0) >= 2:
                continue
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
            picked.append(it)
        if len(picked) < per_bucket:
            for it in seeds:
                if it in picked:
                    continue
                if len(picked) >= per_bucket:
                    break
                owner = (it.get("full_name") or "").split("/")[0].lower()
                if owner_counts.get(owner, 0) >= 2:
                    continue
                owner_counts[owner] = owner_counts.get(owner, 0) + 1
                picked.append(it)
        result[bid] = {"title": title, "items": picked}
    # Only include buckets defined in config? Spec shows all bucket ids.
    # Keep config buckets even if empty, plus any extra seen.
    return result


def main():
    root = repo_root()
    with open(root / "config" / "watch.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    raw = load_json(root / "data" / "raw" / "latest.json", {"repos": []}) or {"repos": []}
    repos = raw.get("repos", []) if isinstance(raw, dict) else []
    seen_path = root / "state" / "seen.json"
    seen = load_json(seen_path, {"snapshots": {}, "reported": {}}) or {}
    if "snapshots" not in seen or not isinstance(seen.get("snapshots"), dict):
        seen["snapshots"] = {}
    if "reported" not in seen or not isinstance(seen.get("reported"), dict):
        seen["reported"] = {}

    now = datetime.now(timezone.utc)
    ranked_buckets = rank_repos(repos, cfg, seen, now)

    out = {"ranked_at": now.isoformat(), "buckets": ranked_buckets}
    ranked_dir = root / "data" / "ranked"
    ranked_dir.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    with open(ranked_dir / ("%s.json" % day), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(ranked_dir / "latest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    for repo in repos:
        if not isinstance(repo, dict):
            continue
        name = repo.get("full_name")
        if not name:
            continue
        try:
            stars = int(repo.get("stars", 0) or 0)
        except (TypeError, ValueError):
            stars = 0
        seen["snapshots"][name] = {"stars": stars, "updated_at": now.isoformat()}
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    with open(seen_path, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)

    for bid in sorted(ranked_buckets):
        print("%s: %d" % (bid, len(ranked_buckets[bid].get("items", []))))


if __name__ == "__main__":
    sys.exit(main())
