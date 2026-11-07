# elf-shell-ayarime
ELF//SHELL — Ayarime: a privacy-first cyber-elf Firefox new-tab extension with original OVA-inspired artwork, commands, notes and optional RSS feeds.

## Public transmission feed

The independent ELF//SHELL publication channel lives in [`site/`](site/) on the default branch. The small [Python RSS builder](scripts/build_public_feed.py) generates a static RSS 2.0 subscription and illustrated-style archive from reviewed JSON announcements, with [automated GitHub Pages publication](.github/workflows/rss-pages.yml) after changes are merged to `main`.

**Not yet a verified live site:** GitHub Pages needs to be enabled in Settings → Pages (select GitHub Actions). Once deployed, the intended public feed is `https://cryogenized-spec.github.io/elf-shell-ayarime/feed.xml`. Details: [site/README.md](site/README.md). This RSS channel does **not** install Firefox updates.

## Mozilla Add-ons — public listing transition (7 November 2026)

ELF//SHELL is preparing its first **publicly listed** Mozilla Add-ons version (v0.5.5) through the *existing* add-on identity. The old unlisted submission workflow has been retired. The manually triggered [public submission workflow](.github/workflows/amo-listed.yml) defaults to full verification only; sending a listed version to AMO requires choosing `submit-listed`, adding private Mozilla API keys to the `mozilla-listed` GitHub environment, and passing checks. [Listing copy and metadata](amo/) are in source control. This is **not** confirmation that Mozilla has approved or published the listing.
