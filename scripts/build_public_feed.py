#!/usr/bin/env python3
"""Build deterministic, static RSS 2.0 and HTML transmission archives.

Only stdlib; no API keys, analytics, remote requests, or GitHub credentials.
Publishing is handled separately by GitHub Pages Actions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site" / "posts.json"
CSS = ROOT / "site" / "style.css"
DEFAULT_OUT = ROOT / "dist" / "feed-site"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM)
ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def validated(data: dict) -> tuple[dict, list[dict]]:
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    base = data.get("base_url")
    url = urlparse(base) if isinstance(base, str) else None
    if not url or url.scheme != "https" or url.netloc != "cryogenized-spec.github.io" or url.path != "/elf-shell-ayarime/" or url.query or url.fragment:
        raise ValueError("The canonical HTTPS Pages URL must not change silently")
    for field in ("title", "description", "language"):
        if not isinstance(data.get(field), str) or not 1 <= len(data[field]) <= 250:
            raise ValueError("Missing or invalid feed metadata: " + field)
    posts = data.get("items")
    if not isinstance(posts, list) or not 1 <= len(posts) <= 100:
        raise ValueError("Feed needs between 1 and 100 posts")
    output, seen = [], set()
    for item in posts:
        if not isinstance(item, dict):
            raise ValueError("Every post must be an object")
        ident = item.get("id")
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in seen:
            raise ValueError("Invalid or duplicate post ID")
        seen.add(ident)
        for field, maximum in (("title", 160), ("summary", 2000), ("category", 80)):
            value = item.get(field)
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
                raise ValueError(f"Post {ident}: invalid {field}")
        try:
            published = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError) as exc:
            raise ValueError(f"Post {ident}: invalid published timestamp") from exc
        if published.tzinfo is None or published.utcoffset() is None:
            raise ValueError("Published timestamps must include a timezone")
        output.append({**item, "published_dt": published.astimezone(timezone.utc)})
    output.sort(key=lambda item: (item["published_dt"], item["id"]), reverse=True)
    return data, output


def build(source: Path = SOURCE, out: Path = DEFAULT_OUT) -> dict:
    config, posts = validated(json.loads(source.read_text(encoding="utf-8")))
    base = config["base_url"]
    feed = ET.Element("rss", version="2.0")
    channel = ET.SubElement(feed, "channel")
    for tag, value in (
        ("title", config["title"]), ("link", base),
        ("description", config["description"]), ("language", config["language"]),
        ("lastBuildDate", format_datetime(posts[0]["published_dt"], usegmt=True)),
        ("generator", "ELF//SHELL static RSS generator"),
    ):
        ET.SubElement(channel, tag).text = value
    ET.SubElement(channel, f"{{{ATOM}}}link", {
        "href": base + "feed.xml", "rel": "self", "type": "application/rss+xml"
    })
    for post in posts:
        item = ET.SubElement(channel, "item")
        url = base + "#"+post["id"]
        for tag, value in (
            ("title", post["title"]), ("link", url),
            ("description", post["summary"]),
            ("pubDate", format_datetime(post["published_dt"], usegmt=True)),
            ("category", post["category"]),
        ):
            ET.SubElement(item, tag).text = value
        ET.SubElement(item, "guid", isPermaLink="false").text = "urn:elfshell:transmission:" + post["id"]
    ET.indent(feed, space="  ")
    rss_bytes = ET.tostring(feed, encoding="utf-8", xml_declaration=True) + b"\n"

    cards = []
    for post in posts:
        title, summary, cat, ident = (escape(post[k], quote=True) for k in ("title", "summary", "category", "id"))
        date = escape(post["published_dt"].strftime("%d %b %Y"), quote=True)
        iso = escape(post["published_dt"].isoformat(), quote=True)
        cards.append(f'<article class="transmission" id="{ident}"><div class="meta"><time datetime="{iso}">{date}</time><span>{cat}</span></div><h2>{title}</h2><p>{summary}</p></article>')
    safe_title = escape(config["title"], quote=True)
    safe_description = escape(config["description"], quote=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'">
  <meta name="description" content="{safe_description}">
  <link rel="alternate" type="application/rss+xml" title="{safe_title}" href="feed.xml">
  <link rel="stylesheet" href="style.css">
  <title>{safe_title}</title>
</head>
<body>
<main class="wrap">
  <div class="brow"><span>// ELF//SHELL · NETWORK TRANSMISSION</span><a href="https://github.com/cryogenized-spec/elf-shell-ayarime" rel="noopener noreferrer">SOURCE ARCHIVE</a></div>
  <h1>AYARIME <b>//</b> TRANSMISSIONS</h1>
  <p class="dek">{safe_description}</p>
  <nav class="links" aria-label="Publication links"><a href="feed.xml" type="application/rss+xml">◉ SUBSCRIBE / RSS</a><a href="https://github.com/cryogenized-spec/elf-shell-ayarime" rel="noopener noreferrer">◈ OPEN PROJECT</a></nav>
  <div class="section-title">// LATEST TRANSMISSIONS · {len(posts):02d}</div>
  {''.join(cards)}
  <footer>Independent open-source project · This feed does not track readers or access Firefox browser information.<br>ELF//SHELL is not affiliated with Mozilla or OpenAI.</footer>
</main>
</body>
</html>
"""
    out.mkdir(parents=True, exist_ok=True)
    (out / "feed.xml").write_bytes(rss_bytes)
    (out / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(CSS, out / "style.css")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {"count": len(posts), "url": base + "feed.xml", "bytes": len(rss_bytes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.source, args.output))


if __name__ == "__main__":
    main()
