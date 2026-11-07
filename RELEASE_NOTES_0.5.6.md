# ELF//SHELL — Ayarime v0.5.6 (development, not submitted)

**Status:** This is a development branch, not a signed Firefox build or a Mozilla listing. v0.5.5 was previously submitted to Mozilla for public review; keep that submitted package unchanged.

## Planned changes
- Add an optional Official ELF//SHELL Transmissions preset in the NET FEED subscription manager, targeting the project-owned RSS publication hosted with GitHub Pages.
- The preset prepares the URL, group and display name only. Subscribing remains a distinct user action and invokes Firefox's normal per-host permission request; no auto-subscription, permission grants or silently fetched headlines.
- Protect partially entered personal subscriptions from being overwritten by the preset.
- Continue to support all existing user-supplied RSS, Atom, and Substack sources, OPML backups, local-only cached headlines and per-source revocation.

## Hosting dependency
GitHub Pages must be explicitly enabled in repository Settings → Pages → Source: GitHub Actions, and its deployment must succeed before the official public RSS address is live. Until then, attempting to subscribe may report a fetch error; this does not affect other feeds.

## Release gate
Before publishing v0.5.6 to Mozilla, pass full source, packaging, Mozilla lint and native Firefox tests; validate the first-party RSS feed from the real public HTTPS URL; inspect installed-version migration; use `submit-listed` only for the approved new version.

The Gecko ID stays unchanged: `elf-shell-ayarime@local.theme`.
