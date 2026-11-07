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

    # Editorial publication page. The RSS document above is deliberately unchanged;
    # both output formats are produced from the same reviewed source records.
    index_items = []
    dispatches = []
    for position, post in enumerate(posts):
        ordinal = f"{len(posts) - position:03d}"
        title, summary, category, ident = (
            escape(post[field], quote=True)
            for field in ("title", "summary", "category", "id")
        )
        date_label = escape(post["published_dt"].strftime("%d %b %Y").upper(), quote=True)
        date_iso = escape(post["published_dt"].isoformat(), quote=True)
        time_label = escape(post["published_dt"].strftime("%H:%M UTC"), quote=True)
        index_items.append(
            f'<li><a href="#{ident}" aria-label="Transmission {ordinal}: {title}">'
            f'<span class="index-number">{ordinal}</span>'
            f'<span class="index-title">{title}</span></a></li>'
        )
        dispatches.append(f"""
        <article class="dispatch{' dispatch-featured' if position == 0 else ''}" id="{ident}">
          <div class="dispatch-head">
            <span class="dispatch-number" aria-hidden="true">{ordinal}<span class="dispatch-number-mark">/</span></span>
            <div class="dispatch-identity">
              <p class="dispatch-eyebrow">{category} <span aria-hidden="true">·</span>
                <time datetime="{date_iso}">{date_label}</time></p>
              <h2>{title}</h2>
            </div>
          </div>
          <p class="dispatch-copy">{summary}</p>
          <div class="dispatch-foot">
            <a class="permalink" href="#{ident}" aria-label="Permanent link to {title}">LINK TO DISPATCH <span aria-hidden="true">↗</span></a>
            <span class="dispatch-clock">{time_label}</span>
          </div>
        </article>""")

    safe_title = escape(config["title"], quote=True)
    safe_description = escape(config["description"], quote=True)
    first_date = escape(posts[0]["published_dt"].strftime("%d %B %Y"), quote=True)
    count = f"{len(posts):02d}"
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
<div class="page-frame" id="top">
  <a class="skip-link" href="#dispatches">Skip to transmissions</a>
  <header class="site-head" aria-label="Publication masthead">
    <a class="brand" href="./" aria-label="ELF//SHELL — Ayarime Transmissions">
      <span>ELF</span><span class="brand-slashes">//</span><span>SHELL</span>
    </a>
    <span class="mast-note">AYARIME <span aria-hidden="true">✳</span> PUBLIC TRANSMISSIONS</span>
    <nav class="head-links" aria-label="Primary navigation">
      <a href="#dispatches">ARCHIVE</a>
      <a href="feed.xml" type="application/rss+xml">RSS <span aria-hidden="true">↗</span></a>
      <a href="https://github.com/cryogenized-spec/elf-shell-ayarime" rel="noopener noreferrer">SOURCE <span aria-hidden="true">↗</span></a>
    </nav>
  </header>

  <main>
    <section class="lead-section" aria-labelledby="page-title">
      <div class="lead-body">
        <p class="overline"><span class="signal-dot" aria-hidden="true"></span> THE AYARIME CORRESPONDENCE <span class="overline-number">VOL. 01 / WEB EDITION</span></p>
        <h1 id="page-title">Dispatches<br>from <em>the shell.</em></h1>
        <p class="lead-desc">An ongoing field journal from ELF//SHELL — a place for releases, new illustrations, and the smaller things worth writing down.</p>
        <div class="hero-actions">
          <a class="primary-link" href="#dispatches">READ THE LOG <span aria-hidden="true">↘</span></a>
          <a class="quiet-link" href="feed.xml" type="application/rss+xml">SUBSCRIBE VIA RSS <span aria-hidden="true">↗</span></a>
        </div>
      </div>
      <div class="illustration" aria-hidden="true">
        <div class="illustration-head"><span>AYR / 01</span><span>FIELD NOTES</span></div>
        <div class="orbit orbit-outer"></div>
        <div class="orbit orbit-middle"></div>
        <div class="orbit orbit-inner"></div>
        <div class="orbital-cross orbital-cross-top"></div>
        <div class="orbital-cross orbital-cross-bottom"></div>
        <span class="orbit-core">あ</span>
        <span class="illustration-side">✳ NOISE / SIGNAL / MEMORY</span>
        <div class="illustration-foot"><span>FROM THE DESK OF AYARIME</span><span>EST. 2026</span></div>
      </div>
    </section>

    <div class="section-band" id="dispatches">
      <h2><span aria-hidden="true">///</span> TRANSMISSION REGISTER</h2>
      <span>{count} ENTRIES <span aria-hidden="true">·</span> LATEST {first_date}</span>
    </div>

    <div class="reading-layout">
      <aside class="archive-rail" aria-label="Transmission index">
        <h3>INDEX <span>{count}</span></h3>
        <ol>{''.join(index_items)}</ol>
        <p class="rail-label">ABOUT THIS CHANNEL</p>
        <p class="rail-copy">A deliberately small public record. Each dispatch appears here and in the RSS feed. No account required.</p>
        <a class="rail-rss" href="feed.xml" type="application/rss+xml">GET THE FEED <span aria-hidden="true">↗</span></a>
      </aside>

      <section class="dispatch-list" aria-label="Published transmissions">
        {''.join(dispatches)}
      </section>
    </div>

    <section class="colophon" aria-label="About the publication">
      <div class="colophon-left">
        <p class="colophon-label">/// THE LAST PAGE</p>
        <h2>Stay for the <em>signal.</em></h2>
        <p>Read these notes here or add the feed to any RSS reader. The page is intentionally static: no adverts, analytics, pop-ups or scripts competing for your attention.</p>
      </div>
      <div class="colophon-right">
        <span class="colophon-stamp" aria-hidden="true">✳</span>
        <p>01 / PUBLICATION</p>
        <strong>ELF//SHELL</strong>
        <span>INDEPENDENT SOFTWARE &amp; STORIES</span>
        <a href="feed.xml" type="application/rss+xml">FEED.XML <span aria-hidden="true">↗</span></a>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <span>ELF//SHELL — AYARIME / AN INDEPENDENT OPEN-SOURCE PROJECT</span>
    <span>NO TRACKERS · NO COOKIES · NO THIRD-PARTY SCRIPTS</span>
    <a href="#top">BACK TO TOP <span aria-hidden="true">↑</span></a>
  </footer>
</div>
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
