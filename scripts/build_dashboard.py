"""Embed ranked JSON into dashboard/index.html as window.__WATCH_DATA__."""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "ranked" / "latest.json"
FAVS_PATH = REPO_ROOT / "state" / "favorites.json"
HTML_PATH = REPO_ROOT / "dashboard" / "index.html"

PATTERN = re.compile(r"<script>window\.__WATCH_DATA__.*?</script>", re.DOTALL)
FAVS_PATTERN = re.compile(r"<script>window\.__WATCH_FAVS__.*?</script>", re.DOTALL)


def load_favs():
    try:
        if FAVS_PATH.exists():
            data = json.loads(FAVS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("favs"), list):
                data = data["favs"]
            if isinstance(data, list):
                return [x for x in data if isinstance(x, str) and x]
    except Exception:
        pass
    return []


def main():
    if DATA_PATH.exists():
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    else:
        payload = {"ranked_at": None, "buckets": {}}
    favs = load_favs()
    html = HTML_PATH.read_text(encoding="utf-8")
    tag = "<script>window.__WATCH_DATA__ = " + json.dumps(payload, separators=(",", ":")) + ";</script>"
    if PATTERN.search(html):
        html = PATTERN.sub(lambda m: tag, html)
    elif "</body>" in html:
        html = html.replace("</body>", tag + "</body>")
    else:
        html = html + tag
    favs_tag = "<script>window.__WATCH_FAVS__ = " + json.dumps(favs, separators=(",", ":")) + ";</script>"
    if FAVS_PATTERN.search(html):
        html = FAVS_PATTERN.sub(lambda m: favs_tag, html)
    elif "</body>" in html:
        html = html.replace("</body>", favs_tag + "</body>")
    else:
        html = html + favs_tag
    HTML_PATH.write_text(html, encoding="utf-8")
    print(str(HTML_PATH))


if __name__ == "__main__":
    main()
