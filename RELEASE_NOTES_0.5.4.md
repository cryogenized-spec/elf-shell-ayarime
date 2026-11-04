# ELF//SHELL — Ayarime v0.5.4 (internal Firefox audit candidate)

This is not a signed or stable extension release.

- Scope duplicate-tab cleanup and idle-tab discard to the **current window**, protecting independent workspaces in other windows.
- Keep failed duplicate-URL reopens available for retry rather than silently clearing the recovery list.
- Report failed note writes as **SAVE ERROR** instead of mistakenly showing a save confirmation.
- Extend the mock-Firefox regression suite for these cases.

Still outstanding before public v1.0: real Firefox 142+ integration testing (host permission grant/deny/revoke, sessions, tabs, RSS, search and theme), AMO signing and signed add-on restart tests. GitHub Actions Mozilla `web-ext lint --warnings-as-errors` has passed on the candidate.

### CI compatibility correction

GitHub Actions successfully ran all source and packaging tests but `web-ext lint --warnings-as-errors` raised `KEY_FIREFOX_ANDROID_UNSUPPORTED_BY_MIN_VERSION` for the Firefox data-collection declaration at desktop minimum 140. The manifest minimum is now Firefox 142 to satisfy the current linter without announcing untested Android support; this excludes Firefox 140 ESR until Mozilla fixes the Android false-positive or a suitable alternative is adopted. The stable Gecko add-on ID is unchanged.

### Codex P1 review fixes

- Replace whole-workspace snapshot writes with independently stored fields, preserving previous v2/v3 settings as a read-only migration baseline. Synchronise field changes between open new-tab instances and keep dirty inputs protected while saves are pending. Concurrent edits to the same field remain last-write-wins.
- Debounce note and focus independently so rapid changes to both are not accidentally cancelled.
- Keep settings dialogs and workspace names retryable after rejected storage writes; do not report a failed saved workspace or JSON import as successful. Make partial imports explicit and check Memory Trace persistence.
- Append newly closed duplicate-tab URLs to any existing unresolved recovery queue rather than replacing earlier failed entries.
- Add cross-instance storage tests and mock-Firefox acceptance scenarios for both batches of recovery and failed saves.

GitHub Actions Mozilla lint passed after the Firefox 142 minimum-version compatibility correction; remaining release gates are real Firefox permission/session/RSS/theme testing and Mozilla signing.

### Codex P2 review fixes (follow-up)

- Saved workspaces are now mutated by one **serialised background message queue**, rather than independent dashboard read-modify-write operations. Saves, deletions and JSON-import replacements share the same queue, preserving earlier v2/v3 saved sessions on first use. The 10-workspace limit is enforced without silently dropping an older saved workspace; rapid identical saves get distinct identities.
- Duplicate-tab recovery now removes only successfully reopened entries from the **live** recovery queue. New cleanup batches added while a reopen is awaiting Firefox remain available. Overlapping reopen attempts are prevented.
- Added `tests/session_races.cjs` and an in-flight reopen scenario in mock Firefox QA. These checks simulate simultaneous dashboard actions, storage rejection and retry, import replacement and the tab-recovery timing race.

All GitHub CI results must be checked on the new commit. This is still a **release candidate**, not an installed or signed Firefox extension.

### GitHub Issue #2 — Claude's Observation (source fixes)

- Public HTTPS RSS validation now rejects dotless hostnames, trailing-dot FQDNs, `.lan`, `.internal`, `.home.arpa`, `.local`, `.localhost`, and reserved `.test`/`.invalid`/`.example` suffixes. IPv4 literal spellings, including browser-normalized shorthand and hexadecimal notation, remain rejected. Each feed still needs an explicit per-site Firefox permission grant.
- The RSS XML parser only accepts the appropriate RSS/RDF `<link>` for RSS entries; an `<atom:link>` extension does not impersonate an RSS article link. Missing or self-only Atom article URLs are not substituted with the feed URL.
- Subscription rows render into a detached fragment. A generation counter discards out-of-order asynchronous permission-check results, preventing duplicated rows after overlapping renders.
- Feed subscriptions, enabled state, groups, refresh interval, imports and per-feed cache updates are serialized in the Firefox background script. Concurrent changes across multiple new-tab dashboards merge rather than replacing stale whole-object snapshots. Removed publications cannot be revived by in-flight cache updates.
- Duplicate-tab recovery records are now stored, without encryption, in `browser.storage.local` and handled by a second serialized background queue. Every URL is reserved *before* its tab is closed, an unsuccessful local-storage write prevents that tab from being closed, and each successfully reopened URL is acknowledged individually. The recovery queue survives navigation and browser restarts and can be explicitly cleared. URLs may contain sensitive query parameters.
- Added `tests/recovery_persistence.cjs`, `tests/rss_concurrency.cjs`, and browser-side `tests/rss_render_qa.py`. Expanded the static, URL, privacy and mock-Firefox checks. These do not replace live Firefox permission, RSS, and signing acceptance tests.

Source review and automated validation are still distinct from the **native Firefox 142+** release gate. Import of a multi-component settings backup can still report `Import incomplete` if one later component fails; backup restoration is not an all-or-nothing transaction.

### Codex Issue #2 follow-up: two further race-condition guards

- A dashboard now tracks cache entries that its own RSS fetch changed and submits **only those entries**. Cached headlines from other publications no longer get replayed as stale writes by another dashboard. The background RSS mutation queue also rejects an older `attemptedAt` value and preserves newer successfully checked headlines when a later fetch attempt fails.
- Duplicate-tab cleanup rechecks each tab’s current URL, window and protected status after the recovery reservation is stored and immediately before removal. A tab that navigated, moved, became active/pinned/audible, or ceased to be a duplicate is **not closed**. Unused reservations are acknowledged; any uncertain state retains its recovery record for manual inspection.
- Expanded tests for stale RSS writes, failed-refresh item preservation, changed-only dashboard cache writes, and a tab navigating/moving mid-cleanup.

These changes are source fixes pending GitHub CI and Codex's follow-up review. Firefox-native acceptance and AMO signing remain **not complete**.

### Codex follow-up: late success after a more recent failed RSS attempt

RSS cache updates now merge **successful article content** using `checkedAt`, independently of `attemptedAt` and the most recent error. A delayed successful response with newer headlines can no longer be thrown away merely because a later failed request wrote an error first. The latest attempt metadata remains truthful. The reverse-order case is exercised by `tests/rss_concurrency.cjs`.

The source and CI checks do not replace native Firefox tests.

- Recovery clear/close race hardening: the background now serialises durable recovery reservation, tab revalidation and tab removal as one operation. History clearing targets explicitly confirmed IDs; concurrent tab closure cannot lose its recovery URL. Added an overlapping clear/close regression test.

- **Codex P1 final-query race:** Duplicate cleanup now checks the selected tab in the last `tabs.query()` snapshot and performs one more `tabs.get()` check before calling `tabs.remove()`. Regression tests change target URL, window, active/pinned state during the final query and after it. Browser tab removal has no atomic URL-conditional variant, so this is a best-effort safety check rather than a guarantee against changes after the final read.


### Six-state Ayarime cursor artwork

Added a seventh opt-in cursor choice using the supplied six-state artwork:
Pointer, I-beam, Busy, Crosshair, Diagonal Resize and Link Hand. Transparent
48/64-pixel offline PNG variants are bundled, with native CSS fallbacks,
scoped to the extension dashboard. Existing pointer options remain intact.
The Busy cursor is static; real Firefox hotspot/contrast testing is pending.
