# ELF//SHELL — Ayarime v0.5.4: AMO listing and reviewer handoff (DRAFT)

**Status:** Internal submission preparation only. **Do not upload or publish** until the release gates in [issue #7](https://github.com/cryogenized-spec/elf-shell-ayarime/issues/7) are satisfied. This document contains draft copy, not an assertion of signed or production readiness.

## Suggested listing

**Name:** ELF//SHELL — Ayarime

**Short summary:** A privacy-conscious, illustrated Firefox new-tab station with custom launchers, local notes, a command palette, optional RSS/Atom feeds and opt-in offline spelling.

**Detailed description:**

ELF//SHELL — Ayarime turns Firefox's new-tab page into an illustrated workstation inspired by 1990s OVA aesthetics. Configure six launchers, search using Firefox's selected default engine, use the command palette and calculator, and keep local notes, daily focus and rotating bilingual Memory Trace quotations.

Optional tools include named tab sessions, duplicate-tab recovery, tab management and user-selected RSS/Atom feeds. Browser permissions are requested as needed; feeds require permission for the corresponding HTTPS publication. The extension can also offer an **experimental offline British-English spellchecker** on supported rich-text editors when explicitly enabled for a site. Its discreet left-click suggestions are generated locally. Standard textareas, unsupported editors and other sites retain Firefox's native spelling support.

The artwork, fonts and spelling resources are bundled with the extension. There is no developer-operated backend, advertising or analytics. Personal notes, saved URLs, feed details, spelling dictionary additions and other preferences live in Firefox's **unencrypted local extension storage**. JSON/OPML export may contain private URLs; treat exported files accordingly.

**Compatibility:** Firefox desktop 142 or later. Firefox for Android is not a tested or advertised target.

**Licence:** MPL-2.0 for project-owned software. Bundled fonts, dictionary, third-party spelling code and original artwork have their own applicable notices; consult LICENSE_SCOPE.md and ARTWORK_LICENSE.md.

## Privacy and permissions explanation

The canonical detailed policy is [PRIVACY.md](PRIVACY.md). Mozilla's manifest declaration of **no data collection by the developer** must not be marketed as "no network activity": searches and user-opened links contact the chosen destination, and subscribed RSS/Atom publishers receive direct feed fetches (and normal connection metadata such as IP address).

- `storage`: remember notes, shortcuts, feeds, preferences, sessions and personal spelling words locally.
- `theme`: optionally colour supported Firefox chrome to match the station.
- `search`: submit a user-initiated search via Firefox's selected engine.
- `scripting` and `activeTab`: support user-initiated enabling and disabling of the local spellchecker on eligible HTTPS sites.
- Optional `tabs`, `sessions`, `bookmarks` and `history`: enable explicitly requested browser utilities; users can deny or revoke them.
- Optional `https://*/*` **declaration**: permits *per-origin*, runtime requests for two features, not blanket installation-time access: direct RSS/Atom fetches and site-by-site offline spelling. Both are opt-in. Disabling spelling leaves a host grant in place when another feature such as RSS may use it; revoke the grant in Firefox's add-on settings to remove origin access.

**External communication:** RSS retrieval contacts only authorised HTTPS publications; searches, shortcuts and restored tabs contact destinations chosen by the user. The spelling checker uses the packaged dictionary and an extension-local worker, not a remote text-processing service. There is no developer-controlled collection endpoint.

## Suggested notes for AMO reviewers

**Build inputs:** Release branch `release/v0.5.4-review` contains readable source, tracked-only runtime archive packaging and a separate reviewer-source archive. See `spelling/vendor/README.md` for the pinned `nspell@2.1.5` + Browserify 17.0.1 rebuild and licence provenance. From a clean checkout with Node/npm and Python available, run `npm test`, `npm run verify:spelling`, `python3 scripts/package.py`, and `python3 scripts/package_source.py`. Follow the resulting source archive's included rebuild instructions. Do not provide an untracked or locally modified archive as the reviewed source.

**Review walkthrough (temporary Firefox profile):**

1. Install the prepared extension; open a new tab, inspect the dashboard, six launchers, local note and command palette. It does not automatically grant website access.
2. In NET FEED, subscribe to a public HTTPS source such as `https://github.blog/feed/`. Verify the native site permission prompt; Deny blocks fetching and Allow permits a feed refresh. Revoke the origin permission and confirm fetching is blocked.
3. On a separate public HTTPS page with a compatible `contenteditable` editor, click the extension's toolbar button and select **Enable spelling on this site**. After approving its site permission, type a misspelling. The optional local checker should underline it; a normal user left-click should show suggestions. Choose a suggestion and use Ctrl+Z to check Undo. The native spelling checker remains in unsupported fields.
4. Use the toolbar to disable spelling. Check that site access may still exist for RSS and can be revoked in Firefox settings. Never use a private document or confidential feed in review tests.
5. Verify optional browser utilities only on throwaway tabs; do not use tab cleanup with unsaved forms or personal sessions.

**Existing automated evidence, not a substitute for final acceptance:** Release commit `1af702d5084471f32a768b82a8f7284c6da506bc` passed [release validation](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/runs/42069417903) and [22 real-Firefox browser checks](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/runs/42069402625) on 5 November 2026. These include genuine RSS host grant/revoke and limited spelling click/Undo coverage in temporary Firefox. They do **not** verify every toolbar gesture, Linux Mint desktop visual behaviour, IME composition, signed upgrade or a second independent live feed source.

## Unfinished release items — keep unchecked until evidenced

- [ ] Test actual spelling toolbar Enable/Disable workflow with pointer interaction in a real desktop Firefox session.
- [ ] Complete Firefox Linux Mint X11 visual, cursor hotspots, responsive sizing, theme tint and keyboard/IME/editor interoperability acceptance.
- [ ] Verify two independently hosted live feeds (including a Substack source), optional tabs/sessions/bookmarks/history and duplicate-tab recovery with throwaway data.
- [ ] Verify settings/session persistence across a real Firefox restart and signed-XPI upgrade without losing the stable extension identity.
- [ ] Obtain final integrated security/code review and resolve any new findings.
- [ ] Capture **authentic**, current screenshots and enter the final AMO listing, privacy link, support contact and permission rationale. No screenshots or support address are fabricated here.
- [ ] Upload the exact validated runtime and reviewer source archives to AMO with the developer's approval; complete Mozilla signing and any review, then verify signed release behaviour.
- [ ] Only then merge release PR #1 into `main` and declare a stable release.

**References:** [Mozilla's current source-code submission guide](https://extensionworkshop.com/documentation/publish/source-code-submission/), [submitting an add-on](https://extensionworkshop.com/documentation/publish/submitting-an-add-on/), [add-on policies](https://extensionworkshop.com/documentation/publish/add-on-policies/). Check policy changes again immediately before submission.
