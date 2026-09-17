"""Unit tests for rank/collect helpers. Stdlib only. Run: python3 scripts/test_rank.py"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rank as rankmod
import collect as collectmod


def make_repo(name, stars=100, bucket="coding_agents", owner=None, **kw):
    full = name if "/" in name else ("%s/%s" % (owner or "owner", name))
    r = {
        "full_name": full,
        "html_url": "https://github.com/" + full,
        "description": "test",
        "stars": stars,
        "forks": 5,
        "open_issues": 1,
        "language": "Python",
        "created_at": "2023-01-01T00:00:00Z",
        "pushed_at": "2023-06-01T00:00:00Z",
        "topics": [],
        "archived": False,
        "fork": False,
        "bucket": bucket,
        "buckets": [bucket],
        "source": "search",
        "query": "q",
    }
    r.update(kw)
    return r


def test_exclude_substring():
    assert collectmod.is_excluded("x/awesome-foo", ["awesome-"]) is True
    assert collectmod.is_excluded("x/my-clone-tool", ["clone"]) is True
    assert collectmod.is_excluded("x/legit-tool", ["awesome-", "clone"]) is False
    assert rankmod.is_excluded("x/star-history-x", ["star-history"]) is True
    print("ok exclude substring")


def test_dedupe():
    a = make_repo("acme/tool", stars=50, bucket="coding_agents")
    b = make_repo("acme/tool", stars=50, bucket="memory_context")
    out = collectmod.dedupe_repos([a, b])
    assert len(out) == 1, out
    assert set(out[0]["buckets"]) == {"coding_agents", "memory_context"}, out[0]
    out2 = rankmod.dedupe_repos([dict(a), dict(b)])
    assert len(out2) == 1
    print("ok dedupe")


def test_cap_5():
    cfg = {
        "per_bucket": 5,
        "lookback_days": 14,
        "exclude_name_substrings": [],
        "buckets": [{"id": "coding_agents", "title": "Coding agents / CLIs"}],
    }
    repos = [make_repo("o%d/t%d" % (i, i), stars=10 + i, bucket="coding_agents") for i in range(7)]
    res = rankmod.rank_repos(repos, cfg, {"snapshots": {}, "reported": {}},
                             now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    items = res["coding_agents"]["items"]
    assert len(items) == 5, len(items)
    print("ok cap 5")


def test_owner_diversity():
    cfg = {
        "per_bucket": 5,
        "lookback_days": 14,
        "exclude_name_substrings": [],
        "buckets": [{"id": "coding_agents", "title": "Coding agents / CLIs"}],
    }
    repos = [make_repo("big/r%d" % i, stars=1000 - i * 10, bucket="coding_agents") for i in range(4)]
    repos.append(make_repo("small/other", stars=10, bucket="coding_agents"))
    res = rankmod.rank_repos(repos, cfg, {"snapshots": {}, "reported": {}},
                             now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    items = res["coding_agents"]["items"]
    big = [x for x in items if x["full_name"].startswith("big/")]
    assert len(big) <= 2, [x["full_name"] for x in items]
    assert any(x["full_name"] == "small/other" for x in items), [x["full_name"] for x in items]
    print("ok owner diversity")


def main():
    test_exclude_substring()
    test_dedupe()
    test_cap_5()
    test_owner_diversity()
    print("all tests passed")


if __name__ == "__main__":
    main()
