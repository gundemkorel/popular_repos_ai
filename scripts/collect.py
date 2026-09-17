"""Collect GitHub repos per config/watch.json. Stdlib only, Python 3.9 compatible."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

GH_SEARCH_FIELDS = [
    "fullName",
    "url",
    "description",
    "stargazersCount",
    "forksCount",
    "openIssuesCount",
    "language",
    "createdAt",
    "updatedAt",
    "pushedAt",
    "topics",
    "isArchived",
    "isFork",
]


def repo_root():
    # scripts/collect.py -> parent of scripts/
    return Path(__file__).resolve().parent.parent


def load_config(root):
    with open(root / "config" / "watch.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def find_gh():
    found = shutil.which("gh")
    if found:
        return found
    cand = Path.home() / ".local" / "bin" / "gh"
    if cand.is_file():
        return str(cand)
    return None


def is_excluded(full_name, excludes):
    name = (full_name or "").lower()
    for sub in excludes or []:
        if sub and sub.lower() in name:
            return True
    return False


def normalize_repo(raw, bucket, source, query):
    if not isinstance(raw, dict):
        raw = {}
    full_name = raw.get("full_name") or raw.get("fullName") or ""
    html_url = raw.get("html_url") or raw.get("url") or (
        "https://github.com/" + full_name if full_name else ""
    )
    stars = raw.get("stargazers_count")
    if stars is None:
        stars = raw.get("stargazersCount", 0)
    forks = raw.get("forks_count")
    if forks is None:
        forks = raw.get("forksCount", 0)
    open_issues = raw.get("open_issues_count")
    if open_issues is None:
        open_issues = raw.get("openIssuesCount", raw.get("open_issues", 0))
    try:
        stars = int(stars or 0)
    except (TypeError, ValueError):
        stars = 0
    try:
        forks = int(forks or 0)
    except (TypeError, ValueError):
        forks = 0
    try:
        open_issues = int(open_issues or 0)
    except (TypeError, ValueError):
        open_issues = 0
    topics = raw.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    archived = raw.get("archived")
    if archived is None:
        archived = raw.get("isArchived", False)
    fork = raw.get("fork")
    if fork is None:
        fork = raw.get("isFork", False)
    return {
        "full_name": full_name,
        "html_url": html_url,
        "description": raw.get("description") or "",
        "stars": stars,
        "forks": forks,
        "open_issues": open_issues,
        "language": raw.get("language"),
        "created_at": raw.get("created_at") or raw.get("createdAt"),
        "pushed_at": raw.get("pushed_at") or raw.get("pushedAt"),
        "topics": topics,
        "archived": bool(archived),
        "fork": bool(fork),
        "bucket": bucket,
        "buckets": [bucket] if bucket else [],
        "source": source,
        "query": query,
    }


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


def _drop_unknown_field(fields, stderr):
    m = re.search(r"[Uu]nknown JSON field[s]?:?\s*\"?([A-Za-z0-9_]+)\"?", stderr or "")
    if m and m.group(1) in fields:
        fields = [f for f in fields if f != m.group(1)]
        return fields, True
    m2 = re.search(r"\"([A-Za-z0-9_]+)\"", stderr or "")
    if m2 and m2.group(1) in fields:
        fields = [f for f in fields if f != m2.group(1)]
        return fields, True
    return fields, False


def gh_search(gh, query, limit):
    fields = list(GH_SEARCH_FIELDS)
    last_err = ""
    for _ in range(len(GH_SEARCH_FIELDS) + 1):
        cmd = [
            gh, "search", "repos", query,
            "--sort", "stars", "--order", "desc",
            "--limit", str(limit),
            "--json", ",".join(fields),
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except Exception as e:
            raise RuntimeError("gh search failed: %s" % e)
        if p.returncode == 0:
            try:
                data = json.loads(p.stdout or "[]")
            except json.JSONDecodeError as e:
                raise RuntimeError("gh search bad JSON: %s" % e)
            if isinstance(data, dict):
                for k in ("repos", "items", "results"):
                    if isinstance(data.get(k), list):
                        return data[k]
                return []
            return data if isinstance(data, list) else []
        last_err = p.stderr or p.stdout or "gh search failed"
        fields, dropped = _drop_unknown_field(fields, last_err)
        if not dropped:
            raise RuntimeError(last_err.strip()[:500])
    raise RuntimeError(last_err.strip()[:500])


def gh_seed(gh, owner_repo):
    cmd = ["gh", "api", "repos/%s" % owner_repo]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as e:
        raise RuntimeError("gh api failed: %s" % e)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "gh api failed").strip()[:500])
    try:
        return json.loads(p.stdout or "{}")
    except json.JSONDecodeError as e:
        raise RuntimeError("gh api bad JSON: %s" % e)


def http_get_json(url, headers):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", "replace")
            return json.loads(body or "{}"), dict(resp.headers.items()), 200
    except urllib.error.HTTPError as e:
        status = getattr(e, "code", 0)
        if status in (403, 429):
            try:
                retry_after = e.headers.get("Retry-After") if e.headers else None
            except Exception:
                retry_after = None
            wait = 20
            try:
                wait = int(retry_after) if retry_after else 20
            except (TypeError, ValueError):
                wait = 20
            time.sleep(wait)
            req2 = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req2, timeout=60) as resp2:
                    body2 = resp2.read().decode("utf-8", "replace")
                    return json.loads(body2 or "{}"), dict(resp2.headers.items()), 200
            except urllib.error.HTTPError as e2:
                try:
                    eb = e2.read().decode("utf-8", "replace")[:500]
                except Exception:
                    eb = "HTTP %s" % getattr(e2, "code", "?")
                raise RuntimeError("HTTP %s: %s" % (getattr(e2, "code", "?"), eb))
        try:
            eb = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            eb = "HTTP %s" % status
        raise RuntimeError("HTTP %s: %s" % (status, eb))
    except urllib.error.URLError as e:
        raise RuntimeError("network error: %s" % e)


def api_search(query, per_page, headers):
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(params)
    data, resp_headers, _ = http_get_json(url, headers)
    items = data.get("items", []) if isinstance(data, dict) else []
    remaining = None
    for k, v in (resp_headers or {}).items():
        if k.lower() == "x-ratelimit-remaining":
            remaining = v
    return items if isinstance(items, list) else [], remaining


def api_seed(owner_repo, headers):
    url = "https://api.github.com/repos/%s" % owner_repo
    data, _, _ = http_get_json(url, headers)
    return data if isinstance(data, dict) else {}


def main():
    root = repo_root()
    # Also work if cwd is scripts/: root resolution is file-based so fine.
    cfg = load_config(root)
    buckets_cfg = cfg.get("buckets", [])
    seeds_cfg = cfg.get("seed_repos", [])
    excludes = cfg.get("exclude_name_substrings", [])
    min_stars = int(cfg.get("min_stars", 0) or 0)
    per_query = int(cfg.get("search_per_query", 20) or 20)
    user_agent = cfg.get("user_agent", "first-project-agent-watch/0.1")
    created_within = int(cfg.get("created_within_days", 0) or 0)
    exclude_exact = set(
        (x or "").lower() for x in (cfg.get("exclude_full_names") or []) if x
    )
    created_qual = ""
    if created_within > 0:
        cutoff = (date.today() - timedelta(days=created_within)).isoformat()
        created_qual = " created:>%s" % cutoff

    token = get_token()
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = "Bearer %s" % token

    gh = find_gh()
    use_gh = False
    if gh is not None and token:
        use_gh = True
    elif gh is not None:
        try:
            auth = subprocess.run(
                [gh, "auth", "status"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            use_gh = auth.returncode == 0
        except Exception:
            use_gh = False

    errors = []
    collected = []
    search_sleep = 0.3 if token else 6.5
    rate_remaining = None
    first_search = True

    for bucket in buckets_cfg:
        bid = bucket.get("id", "")
        for query in bucket.get("queries", []):
            if created_qual and "created:" not in query:
                query = query + created_qual
            items = None
            if use_gh:
                try:
                    items = gh_search(gh, query, per_query)
                except Exception as e:
                    errors.append("gh search failed bucket=%s query=%.80s: %s" % (bid, query, e))
                    items = None
            if items is None:
                if not first_search:
                    time.sleep(search_sleep)
                first_search = False
                try:
                    items, remaining = api_search(query, per_query, headers)
                    if remaining is not None:
                        rate_remaining = remaining
                except Exception as e:
                    errors.append("search failed bucket=%s query=%.80s: %s" % (bid, query, e))
                    continue
            else:
                if not first_search:
                    # keep light pacing even with gh
                    time.sleep(0.2)
                first_search = False
            for raw in items or []:
                try:
                    n = normalize_repo(raw, bid, "search", query)
                except Exception as e:
                    errors.append("normalize failed bucket=%s: %s" % (bid, e))
                    continue
                if is_excluded(n.get("full_name", ""), excludes):
                    continue
                if (n.get("full_name") or "").lower() in exclude_exact:
                    continue
                if n.get("stars", 0) < min_stars:
                    continue
                collected.append(n)

    for seed in seeds_cfg:
        owner_repo = seed.get("repo", "") if isinstance(seed, dict) else ""
        sb = seed.get("bucket", "") if isinstance(seed, dict) else ""
        if not owner_repo:
            continue
        raw = None
        if use_gh:
            try:
                raw = gh_seed(gh, owner_repo)
            except Exception as e:
                errors.append("gh seed failed %s: %s" % (owner_repo, e))
                raw = None
        if raw is None:
            try:
                raw = api_seed(owner_repo, headers)
            except Exception as e:
                errors.append("seed failed %s: %s" % (owner_repo, e))
                continue
        if isinstance(raw, dict) and raw.get("message") and not raw.get("full_name"):
            errors.append("seed failed %s: %s" % (owner_repo, str(raw.get("message"))[:200]))
            continue
        try:
            n = normalize_repo(raw, sb, "seed", None)
        except Exception as e:
            errors.append("normalize seed failed %s: %s" % (owner_repo, e))
            continue
        if is_excluded(n.get("full_name", ""), excludes):
            continue
        # seeds bypass min_stars
        collected.append(n)

    repos = dedupe_repos(collected)

    collected_at = datetime.now(timezone.utc).isoformat()
    out = {"collected_at": collected_at, "errors": errors, "repos": repos}

    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    with open(raw_dir / ("%s.json" % day), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(raw_dir / "latest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    counts = {}
    for r in repos:
        for b in r.get("buckets", []) or [r.get("bucket")]:
            if b:
                counts[b] = counts.get(b, 0) + 1
    print("collected %d repos" % len(repos))
    for b in sorted(counts):
        print("  %s: %d" % (b, counts[b]))
    if rate_remaining is not None:
        print("rate-limit remaining: %s" % rate_remaining)
    if errors:
        print("errors: %d (see JSON)" % len(errors))


if __name__ == "__main__":
    sys.exit(main())
