# ELF//SHELL — Ayarime v0.5.2

**Status:** release candidate. Live Chromium visual testing was conducted on v0.5.1; the updated v0.5.2 needs its final browser/Firefox verification.

## Improvements

- Replaced responsive launcher wrapping with a predictable six-column desktop dock and a balanced three-by-two dock at tablet and narrow widths; avoids the five-plus-one icon layout observed at 768 px.
- Reworked the RSS footer on small windows into two rows, reserving meaningful horizontal space for the headline while retaining both navigation arrows and the subscription action.
- Added a local multi-size `favicon.ico`, linked in `newtab.html`, and included it in the AMO package to eliminate the preview's missing-favicon request.
- Allowed vertical scrolling at very short, narrow viewport sizes so search and launcher controls remain reachable.
- Increased static regression checks for all three fixes and bumped version references to 0.5.2 without changing any persistent preference keys or the add-on ID.

## Verification

Run `npm test`, `npm run package:amo`, `python3 scripts/package.py --verify-only` and, when network access permits, `npx web-ext lint --source-dir .`. For an actual Firefox test, use `about:debugging` → **This Firefox** → **Load Temporary Add-on** → select `manifest.json` from the extracted source folder.

Publishing/signing has **not** been done. Static preview tests do not verify Firefox theme, permission prompts, or session APIs.

## Review-driven usability and permission improvements

- Consolidated seven station actions into a single, accessible **Station** menu, closed by default. Click it to reveal the same controls. This clears the former orphaned second line of text links.
- Refined **Ctrl+K** so it opens the command palette directly in `>` actions mode, with grouped results, Up/Down navigation, selection tracking, and Escape dismissal. `/` still focuses ordinary search. Actual Firefox key handling must be verified in an installed add-on.
- Added breathing room and clearer contrast around the **NETWORK / ENTRY POINT** caption, quick-link headings and category sublabels without requiring the optional high-contrast setting.
- Expanded the **Browser Access** permission ledger: it now lists each currently granted host origin and offers an individual **REVOKE** control. Both built-in optional browser permissions and feed-host grants remain opt-in. The HTTP preview intentionally reports permissions unavailable.
- Added a **REOPEN JUST-CLOSED DUPLICATE URLS** action after successful duplicate cleanup. It re-creates closed tabs' URLs (best effort) but **cannot restore unsaved page content**. Confirmation remains mandatory before closing; active/pinned/audible/private tabs remain excluded.
- Confirmed that the existing feed module already requests per-site HTTPS permissions, parses XML using `DOMParser`, displays untrusted titles through `textContent`, uses bounded/timeout fetches and timestamped local cache, refuses unapproved redirects, excludes `javascript:`/`data:` article URLs and uses `noopener noreferrer` for article links.
- Confirmed `background.js` already applies the Ayarime toolbar/chrome palette through `browser.theme.update()`. A screenshot of the web-served new-tab page cannot verify it; this needs installed-Firefox testing.

## Additional regression checks

- `python3 tests/visual_qa.py` passed using a real headless Chromium renderer with locally inlined source and assets: desktop (1600×900), tablet (768×900) and mobile (390×844) layout, collapsed Station menu, Ctrl+K action grouping, arrow keys, Escape, and caption spacing.
- `python3 tests/mock_firefox_qa.py` passed using a simulated Firefox WebExtensions API: host permissions ledger/revoke and duplicate-tab URL reopening. These tests do not replace actual Firefox tests.
- No telemetry or external libraries added. Existing local storage identifiers and add-on ID are preserved.

**Still required before general release:** Mozilla `web-ext lint`, Firefox temporary add-on installation, host grant/revoke (including after restart), live RSS fetching, native tabs/sessions/bookmarks/history, duplicate-tab restoration behavior, and actual toolbar tint confirmation.
