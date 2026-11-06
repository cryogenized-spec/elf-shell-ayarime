# Browser Integration — development feature (not in v0.5.4 stable)

This feature belongs to an isolated review branch. Nothing is signed, published, or
merged into the Firefox release candidate by adding this document.

## Settings

Open a new Ayarime tab → **STATION → CONFIGURE STATION → FIREFOX SPELLING INTEGRATION**.

- **Per-site (default):** use the extension toolbar icon to open a stable
  site-spelling settings tab. A second explicit click requests that one HTTPS
  site's optional permission. The toolbar popup itself never owns the Firefox
  permission prompt.
- **All approved HTTPS websites:** the user clicks Apply in Station and
  explicitly approves Firefox's broader optional host permission.
- **Firefox native only:** disables Ayarime's injected spelling and unregisters
  old per-site registrations. Native Firefox spelling remains active.
- **Revoke broad HTTPS access:** removes the optional wildcard permission;
  individual RSS and spelling host grants remain independently manageable.

The **website-wide cursor injector has been removed**; bundled custom cursors
are supported only on Ayarime's own new-tab dashboard. Linux-wide cursors are
a separate, optional future package.

## Scope and limits

Compatible rich-text editors use non-DOM-mutating highlight ranges. Ordinary
textarea and text/search fields retain native Firefox underlines/right-click
menus while Ayarime offers additional local left-click word suggestions.
Password, sensitive and code editors are excluded. Neither a Firefox
WebExtension nor a custom Linux theme can modify Firefox's privileged
internal page controls. No spellcheck network traffic or page text telemetry. Browser-wide spelling permission does not approve RSS sources: separate NET FEED consent is stored per exact subscribed URL. Existing legacy subscriptions may require one-time RSS reapproval.

## Test and review gates

- [ ] npm test (includes permission-mode, unauthorized-sender, revocation,
      native-fallback and packaging checks).
- [ ] GitHub Actions full Mozilla lint, reproducible spelling build and
      tracked-only source and runtime ZIP integrity.
- [ ] Isolated real-Firefox test of the **actual Station Apply gesture**,
      grant/deny, injection into existing tabs, and absence before consent.
- [ ] Actual user Firefox Linux Mint testing of cursor hotspots, selection,
      site compatibility, web editor spelling, IME, Undo and prompt behaviour.
- [ ] Check interaction with site-specific spelling and RSS subscriptions,
      plus Firefox host permission revocation, private browsing and restarts.
- [ ] Codex/security review on the exact final integrated feature commit.

Do **not** merge into release/v0.5.4-review or main before those gates.
