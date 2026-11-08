# ELF//SHELL // Transmission Log — publication source

**This is a public, editorial RSS 2.0 feed, not a network monitoring feed and not a Firefox software update manifest.** No reader analytics, third-party scripts, or server are required.

## Where it lives

Same repository, separate concern. Publication source is kept in `main` under `site/`; Firefox extension release branches remain independent. The generated website uses GitHub Pages, not a maintained `gh-pages` branch.

Public subscription and reading addresses (**GitHub Pages deployment verified on 7 November 2026**):

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

GitHub Pages was enabled, and the `rss-pages.yml` workflow confirmed successful deployment on 7 November 2026. As a general safeguard, GitHub Actions validation and deployment remain separate: a successful build by itself does not prove publication. Check the deploy job and public page before making a new live-site claim.

The site is independently hosted from Mozilla Add-ons; it **cannot distribute signed Firefox extension updates** and does not contain an `updates.json` manifest. Adding extension auto-update delivery later requires a separate, reviewed pipeline for signed XPI releases, HTTPS hosting, and the Firefox `update_url`.

For authorisation and quality, publish only reviewed announcement copy. No automatic rewriting of change logs into public claims, and no automatic posts about pending Mozilla approvals.

## Visual publication design

The public site is a deliberately art-directed **editorial transmission register**, not a generic dashboard or JavaScript feed viewer. It has an original CSS-only Ayarime signal drawing, a numbered and accessible dispatch index, a typographic reading column, a clear RSS subscription link and responsive, print-friendly layouts. The language and visible text are editorial, not a fake control panel with fabricated signal strength, status telemetry or placeholder headlines. It uses no images from remote hosts, external fonts, JavaScript, trackers or third-party services. The small footer identifies an independent project without overstating legal disclaimers.

The generator uses **the same real published entries** from `site/posts.json` for both the HTML register and its canonical RSS 2.0 XML. Never add invented entries just to fill the layout. All user-supplied editorial strings are escaped in the static HTML. Accessibility and injection tests live in `tests/test_public_feed.py`.

## Illustrated project release dispatches

A curated **From the Workshop** transmission can link to a dedicated editorial page instead of only a fragment on the main archive. Set the optional `page` field on the corresponding `site/posts.json` item to a checked relative pathname under `dispatches/*.html`; never use absolute/external URLs in this field. The RSS item then points to the local article while its permanent GUID remains `urn:elfshell:transmission:<id>`. Archive index links still scroll to that entry and offer a separate link to the full page.

The first such page is `site/dispatches/clickup-serviteur-v0.3.0-beta.1.html`. It covers the **verified** `cryogenized-spec/ClickUp-Serviteur-MCP` public GitHub prerelease `v0.3.0-beta.1`, published 7 November 2026, source commit `7aadec22b326a5d9767d47762b506642a8c41ddc`. This is **not** a public ClickUp integration, hosted subscription, official ClickUp endorsement, or a completed general-availability product.

The page uses its own local static stylesheet, `site/dispatches/serviteur.css`, and two visually approved original four-sliver illustrations under `site/media/`. The first is the temple discovery (01–04); the second is the underground maintenance vault (05–08) with the stunned green gremlin. Both sliver sheets are preserved, avoiding arbitrary crop at panel boundaries. The site builder copies the HTML, CSS and WebP assets into GitHub Pages. All of them are included in the deployed artifact; no remote image host, fonts, tracking script or external CDN.

The cat is **not** included in these story slivers. A subtle Git-familiar pictogram remains in the release-identification section, where future separately approved cat artwork can eventually appear.

Only add a release to this archive when its GitHub tag, exact public release status, version and link are verified. Changes are reviewed through a pull request and the publishing workflow; they are not imported automatically from unrelated repositories. An RSS/HTML release announcement is editorial, not a software auto-updater.
