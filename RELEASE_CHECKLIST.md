# Before first public Firefox Add-ons release

- [ ] Test new-tab page in Firefox on Linux Mint and at least one additional platform.
- [ ] Confirm SVG shortcuts, responsive sizing, icon picker, settings migration, and theme contrast.
- [ ] Confirm optional permission requests and revocation behaviour in Firefox.
- [ ] Verify named workspaces restore expected tabs, never incognito tabs, and do not unexpectedly expose sensitive URLs.
- [ ] Test duplicate tab cleanup on a throwaway profile with unsaved form state.
- [ ] Test 30-minute idle tab discard on a throwaway profile.
- [ ] Run Mozilla `web-ext lint` and review any reported warnings.
- [ ] Verify `browser.search.search` and default search functionality.
- [x] Public repository `cryogenized-spec/elf-shell-ayarime` created by project owner.
- [ ] Open a public release-review PR and explicitly request Codex review; address review findings and rerun checks before merge.
- [ ] Add authentic Firefox screenshots, descriptions, privacy disclosure and icon to Mozilla Add-ons Developer Hub.
- [ ] Obtain Mozilla signing; test a signed distribution.
- [ ] Publish the first stable version with clear licence terms for code and artwork.


### v0.4 feed reader acceptance

- [x] Substack home/article links normalise to `/feed`; other RSS/Atom URLs retained.
- [x] Per-domain on-demand optional HTTPS permissions; revocation available in manager.
- [x] User-managed labels, groups, enabled states, refresh interval and privacy defaults.
- [x] Local metadata-only feed cache, XML parsing without injecting remote markup into DOM.
- [x] OPML import/export and JSON settings export/import (feed settings included).
- [x] Node syntax and RSS URL/OPML/safety smoke tests.
- [ ] Test runtime permissions and redirects in **Firefox on Linux Mint**.
- [ ] Test two real-world public feeds (one Substack and one Atom) in Firefox.
- [ ] Test migration from v0.3 and JSON backup restore after restart.
- [ ] Run `web-ext lint` before publication.


### 0.5.1 hardening checks
- [x] Declare Firefox 140+ and Mozilla built-in no-developer-data-collection disclosure.
- [x] Restrict packaged scripts/styles to local resources via CSP.
- [x] Reject non-Substack `/p/` URL rewrites and unsafe cached RSS links; block cross-site RSS redirects.
- [x] Compare exact URLs during duplicate-tab cleanup to preserve fragment-based app states.
- [x] Add a packaging script and release assertions.
- [ ] Confirm Mozilla `web-ext lint` clean in a network-enabled environment or CI.
- [ ] Complete real Firefox 140+ permission, search, RSS, theme, session and persistence acceptance tests.
- [ ] AMO review and signing; perform signed XPI upgrade test.

## v0.5.2 visual and packaging regression checklist

- [ ] Open 1600×900, 768×900, 390×844, and 320×568 viewports. Check six-across desktop, three-by-two tablet/mobile, and scrolling on short windows.
- [ ] Confirm RSS controls fit in two rows at 390px and headlines remain readable/ellipsised when long.
- [ ] Confirm no `/favicon.ico` request fails in browser console/network log.
- [ ] Re-test Firefox-native APIs, optional permission prompts, bookmarks/history/sessions, and theme under a temporary extension install.
