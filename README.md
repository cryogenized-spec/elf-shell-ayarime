# elf-shell-ayarime
ELF//SHELL — Ayarime: a privacy-first cyber-elf Firefox new-tab extension with original OVA-inspired artwork, commands, notes and optional RSS feeds.

## Public transmission feed

The independent ELF//SHELL publication channel lives in [`site/`](site/) on the default branch. The small [Python RSS builder](scripts/build_public_feed.py) generates a static RSS 2.0 subscription and illustrated-style archive from reviewed JSON announcements, with [automated GitHub Pages publication](.github/workflows/rss-pages.yml) after changes are merged to `main`.

**Not yet a verified live site:** GitHub Pages needs to be enabled in Settings → Pages (select GitHub Actions). Once deployed, the intended public feed is `https://cryogenized-spec.github.io/elf-shell-ayarime/feed.xml`. Details: [site/README.md](site/README.md). This RSS channel does **not** install Firefox updates.
