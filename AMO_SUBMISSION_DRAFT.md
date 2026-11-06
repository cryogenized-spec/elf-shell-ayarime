# ELF//SHELL — Ayarime v0.5.4 — Mozilla signing preparation

**Status:** Unsigned review candidate; do not claim Mozilla acceptance or
upload on behalf of the owner before authorization.

## Suggested public listing

**Name:** ELF//SHELL — Ayarime

**Summary:** An illustrated, privacy-conscious Firefox new-tab workstation
with local notes, command palette, workspaces, rotating bilingual memory
fragments and optional RSS/Atom feeds.

**Description:** Ayarime turns Firefox's new-tab page into an illustrated
1990s science-fiction workstation. Customize six launcher shortcuts, notes,
focus and typography; use the Ctrl+K action palette and calculator; organise
saved sessions and inspect your RSS/Atom subscriptions. Optional tools
ask for the relevant Firefox permissions at use time. RSS requests go
directly to publishers you approve, not through an ELF//SHELL backend.

The extension contains **no custom spelling engine** and does not inject
scripts into other websites. Firefox's native spelling checker is untouched.
Optional illustrated cursors apply only to the Ayarime dashboard. An
independently installable Linux cursor theme archive is **not required**.

There is no advertising, analytics or developer-operated service. Notes,
URLs and preferences are saved in Firefox extension-local **unencrypted**
storage; exported JSON/OPML files can contain private URLs.

**Compatibility:** Desktop Firefox 142 or later; Android is not claimed or
tested. Local fonts and icons are included.
Project-owned code: MPL-2.0. Artwork: ARTWORK_LICENSE.md. Bundled fonts
retain their OFL notices.

## Reviewer permissions and network explanation

- storage: local notes, preferences, feed cache and workspaces.
- theme: selected Firefox-chrome tint using a supported API.
- search: explicit search via Firefox's current default engine.
- Optional tabs, sessions, bookmarks, history: explicitly chosen utilities.
- Optional HTTPS site permission is **not** blanket access on installation.
  Each RSS feed requires per-host Firefox approval and separate stored
  per-feed consent. Imports cannot authorize fetching by themselves.

External connections are explicitly chosen browsing/searches and RSS
fetches to approved publishers. RSS fetches omit credentials/referrers
and reject redirects. No custom spelling, content script or AI provider
connection is included. See PRIVACY.md.

## Reviewer build instructions

From a clean checkout of the release candidate SHA (not stable main):

    npm test
    python3 scripts/package.py
    python3 scripts/package_source.py
    npx --yes web-ext@10.8.0 lint --source-dir dist/amo --warnings-as-errors

Upload the exact runtime Firefox ZIP and separate source-review ZIP;
both are deterministic from tracked files. The standalone Linux cursor
tarball is not an add-on file and must not be included in AMO.

## Final acceptance and submission gates

- [ ] Mozilla lint, release inventories, source reproduction and native
      Firefox regression pass on final post-merge SHA.
- [ ] Inspect dashboard, pointer fallback, theme tint, launchers, notes,
      and settings export/import on Linux Mint.
- [ ] Confirm optional RSS host Deny/Allow/Revoke and direct feed refresh,
      with imported feeds blocked until separately approved.
- [ ] Verify tabs/workspaces, browser restart persistence and saved-session
      safeguards on disposable data.
- [ ] Final independent security review and resolution of findings.
- [ ] Genuine screenshots, support contact and publicly accessible privacy URL.
- [ ] Owner approves Mozilla Developer Hub upload and signing; install
      resulting signed build and check the upgrade.
- [ ] Merge stable main only after the owner authorizes release.

The optional Linux cursor package has separate visual acceptance and is
never described as Mozilla-signed.
