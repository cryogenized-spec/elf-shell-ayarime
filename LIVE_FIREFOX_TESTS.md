# ELF//SHELL — v0.5.4 release-acceptance tests

Do **not** test tab deletion/discarding with irreplaceable work or unsaved forms. Use a separate Firefox profile or harmless example tabs. The source tests are automated; the following items require a real Firefox **142+** installation.

## A. Install, startup and console

1. If updating a temporary build, export the station's JSON settings first. Remove the previous temporary ELF//SHELL via `about:debugging#/runtime/this-firefox`.
2. Extract the source ZIP. Load **Temporary Add-on** by selecting `manifest.json`. Verify a new tab opens ELF//SHELL and the Firefox tab/toolbar palette changes.
3. In `about:debugging`, select **Inspect** for ELF//SHELL and check for exceptions and CSP violations. A single network failure for an unsubscribed feed is not expected: the app should make no RSS requests until there are subscriptions.
4. Check the UI at 1366×768 and a normal large desktop viewport. The new-tab artwork must remain visible and search, launcher, feed controls, notes, and quote controls should remain reachable.

## B. Search and personal preferences

5. Search normal text (should use the **current Firefox default engine**, not a hard-coded provider). Check `!gh firefox`, `!w galaxy`, and `= 15% of 2400`. Use `/`, arrow keys, Enter, and Escape (Escape must clear text and close the overlay).
6. Edit one dock shortcut; check its icon, label, link destination, and number-key shortcut. Open Settings and verify the saved value persists across new tabs.
7. Enter a note and daily focus. Export settings JSON. Change a setting, import JSON, and confirm restore. Avoid inserting passwords or private company data.
8. Open multiple new tabs: the Memory Trace quote should stay synchronised and change at the selected interval. Test language modes, favourite, pin, pause, and complete fragment dialog. Verify no duplicate quotes or missing text.

## C. RSS, consent and permissions

9. In NET FEED, subscribe to a **public Substack**, e.g. `https://thebrowser.substack.com/feed`, and an HTTPS Atom feed, e.g. `https://github.blog/feed/`. Confirm Firefox asks for host approval **per domain** and headlines are fetched only after you approve.
10. Reject permission for a third feed; ensure there is **no fetch**. Import OPML; subscriptions should appear but require individual permission before fetching. Export OPML and re-import it.
11. Try a URL from another domain ending `/p/example`: it must **not** be silently rewritten to `/feed`. Check an ordinary published article link opens in a new tab and no HTML markup is injected into titles. A feed that redirects should show a fetch error and explain that its canonical HTTPS feed URL is required.
12. Disable a feed; verify it disappears from the ticker. Revoke its host permission; verify there are no further authorised requests. Verify other enabled/authorised feeds continue working. Test the 15-minute and 30-minute refresh choices without causing excessive network requests.
13. In Browser Access, grant and revoke optional Tabs, Sessions, Bookmarks, and History. Each should be on demand and separable. If denied, search should offer to enable the appropriate permission without errors.

## D. Sessions and safety

14. Create harmless duplicate tabs and tabs with different URL fragments (`https://example.com/#a` vs `https://example.com/#b`). Duplicate cleanup must not close the fragment-distinct tab. A confirmation must appear before any removal. Verify that a new duplicate cleanup while an earlier recovery is pending does not erase either set of recoverable URLs. Exercise discarded-tab commands only on throwaway tabs.
15. Save a named workspace, restore it, and confirm private/incognito or internal Firefox pages were not captured. Open two new-tab dashboards and save distinct workspaces simultaneously; both must remain saved after reload. Test saving one while deleting another; the delete must not be undone. Test restoring a recently closed tab. Confirm tabs are not opened automatically when the extension first starts. In the same test profile, confirm pre-v0.5.4 session sets are preserved on first use.

## E. Production release gates

16. Run `npm test`, then `python3 scripts/package.py`, then `npx --yes web-ext@10.8.0 lint --source-dir dist/amo --warnings-as-errors` on a machine with npm network access. All checks must be green before the Mozilla submission.
17. Upload `dist/ELF-SHELL-Ayarime-v0.5.4-AMO.zip` to [Mozilla Add-ons Developer Hub](https://addons.mozilla.org/developers/). Select public **On this site** distribution if ready. Check privacy declarations and other listing questions carefully.
18. Mozilla must sign the extension. Install the signed XPI, restart Firefox, check that the extension persists, and re-run the important privacy, search, note, RSS, theme and restart tests.
19. Release only after Mozilla review and after verifying the signed package. Record Firefox version, date, test results, and any remaining known issues in the GitHub release notes.

**Release label until step 19 succeeds:** v0.5.4 release candidate. Do not claim full production stability based solely on Node syntax tests or a static ZIP check.

## Issue #2 acceptance: persistent recovery and RSS cross-tab changes

On a disposable Firefox 142+ profile, install the current release-candidate branch temporarily and open two dashboard/new-tab pages. In one, subscribe to a known public HTTPS RSS/Atom feed and explicitly allow only its site; verify the other dashboard reflects the new feed without losing any existing subscriptions. Repeat with another feed, a feed removal and a denied host permission. Confirm the grant ledger displays precisely the accepted hosts. Never use private/intranet feed URLs as test destinations.

Open two duplicate throwaway tabs in the same window, run a confirmed duplicate cleanup, and observe the saved recovery button. Close the dashboard, open another new tab (and later restart Firefox with a signed build), and verify the queue remains available. Reopen the URLs, verify the queue empties, repeat once using the explicit CLEAR RECOVERY HISTORY control. Note that these records are local and unencrypted; use test-only URLs, not authenticated services. Finally confirm a manually denied or failed storage write never results in the underlying tab being closed without a recovery reservation.
