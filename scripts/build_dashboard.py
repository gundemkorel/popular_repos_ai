"""Embed ranked JSON into dashboard/index.html as window.__WATCH_DATA__."""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "ranked" / "latest.json"
HTML_PATH = REPO_ROOT / "dashboard" / "index.html"

PATTERN = re.compile(r"<script>window\.__WATCH_DATA__.*?</script>", re.DOTALL)
LEGACY_FAVS_PATTERN = re.compile(r"\s*<script>window\.__WATCH_FAVS__.*?</script>", re.DOTALL)


def main():
    if DATA_PATH.exists():
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    else:
        payload = {"ranked_at": None, "buckets": {}}

    html = HTML_PATH.read_text(encoding="utf-8")
    tag = "<script>window.__WATCH_DATA__ = " + json.dumps(payload, separators=(",", ":")) + ";</script>"
    if PATTERN.search(html):
        html = PATTERN.sub(lambda m: tag, html)
    elif "</body>" in html:
        html = html.replace("</body>", tag + "</body>")
    else:
        html = html + tag

    # Favorites are now per-username and synced remotely. Remove the old global snapshot.
    html = LEGACY_FAVS_PATTERN.sub("", html)

    HTML_PATH.write_text(html, encoding="utf-8")
    print(str(HTML_PATH))


if __name__ == "__main__":
    main()
