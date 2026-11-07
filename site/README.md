# ELF//SHELL // Transmission Log — publication source

**This is a public, editorial RSS 2.0 feed, not a network monitoring feed and not a Firefox software update manifest.** No reader analytics, third-party scripts, or server are required.

## Where it lives

Same repository, separate concern. Publication source is kept in `main` under `site/`; Firefox extension release branches remain independent. The generated website uses GitHub Pages, not a maintained `gh-pages` branch.

Proposed public addresses, **not live until GitHub Pages is enabled and deployed**:

- RSS subscription: https://cryogenized-spec.github.io/elf-shell-ayarime/feed.xml
- Readable archive: https://cryogenized-spec.github.io/elf-shell-ayarime/

The Python generator reads `site/posts.json`. Do not hand-edit generated XML or HTML. A short, deliberate post can announce development milestones, version releases **only after their actual status is verified**, or Ayarime's public illustrated-story journal.

## Add an announcement

Append to `site/posts.json` with a stable lowercase hyphenated `id`, editorial `title`, ISO 8601 timezone-aware `published`, `category`, and plain-text `summary`. Never edit an existing post ID after publication: RSS readers use it as the item's permanent GUID. Posts are sorted newest-first; a fix to published content may change its text, not its identity.

Locally check with Python 3.12 or later:

```bash
python3 -m unittest discover -s tests -p 'test_public_feed.py' -v
python3 scripts/build_public_feed.py --output dist/feed-site
```

Open `dist/feed-site/index.html` to inspect the readable archive and `dist/feed-site/feed.xml` to inspect the machine-readable RSS. The site is static, and generated files are published from `dist/feed-site` only, not checked into source.

## Enable GitHub Pages once

In GitHub repository **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. The committed `.github/workflows/rss-pages.yml` workflow runs public-feed regression tests on pull requests to `main`, and after merging approved content into `main` it builds and deploys the feed automatically. You can also run the workflow manually under GitHub Actions.

GitHub Pages might be disabled or unconfigured initially. A successful build does not mean the public URL is available until a successful Pages deployment has occurred. Do not show the URL as a verified live subscription until that succeeds.

The site is independently hosted from Mozilla Add-ons; it **cannot distribute signed Firefox extension updates** and does not contain an `updates.json` manifest. Adding extension auto-update delivery later requires a separate, reviewed pipeline for signed XPI releases, HTTPS hosting, and the Firefox `update_url`.

For authorisation and quality, publish only reviewed announcement copy. No automatic rewriting of change logs into public claims, and no automatic posts about pending Mozilla approvals.
