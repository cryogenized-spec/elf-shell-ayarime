# Browser Integration — development feature (not in v0.5.4 stable)

This feature belongs to an isolated review branch. Nothing is signed, published, or
merged into the Firefox release candidate by adding this document.

## Settings

Open a new Ayarime tab → **STATION → CONFIGURE STATION → BROWSER INTEGRATION**.

- **Cursors → Across approved HTTPS websites:** Uses Ayarime's bundled
  six-state cursor artwork on eligible HTTPS pages, and follows the current
  dashboard pointer selection for the default cursor where possible.
- **Offline spelling → Across approved HTTPS websites:** Enables the bundled,
  offline British-English checker on **compatible contenteditable editors**
  and left-click suggestions on standard textareas and single-line text/search
  inputs. Contenteditable words use an experimental custom highlight; ordinary
  controls retain Firefox's native underlines, native right-click suggestions
  and Undo while the extension provides an additional left-click menu. Password,
  private, code and unsupported fields are excluded.
- Choose each mode independently. Both broader modes share one optional
  Firefox grant for **all HTTPS sites**. Neither feature is activated by
  installation, and a per-site RSS grant does not turn on broad spelling.
- **APPLY** requests this optional Firefox host grant from a genuine click
  on the new-tab extension page. Denying the request preserves the previous
  settings. The background process **cannot request it silently**.
- **REVOKE BROAD HTTPS ACCESS** deactivates both global modes and removes
  the all-HTTPS grant. Individually granted RSS/spelling hosts remain under
  Firefox's independent permissions settings. If an inaccessible tab retains
  old injected styles or spelling state, reload that tab.

Defaults on existing installs remain dashboard-only cursors and per-site
spelling. These are **opt-in capabilities**, not a new silent default.

## Scope and limits

The extension cannot style the Firefox address bar, tab strip, privileged
browser pages or the Linux desktop pointer. Some webpages with custom mouse
interaction may use native cursor shapes; user-selected high-contrast cursor
settings or important accessibility requirements may call for disabling
the custom cursor mode.

Offline spelling never contacts an external text service; scanned word tokens
stay within the browser extension's background worker. It provides correction
menus only after successful local checking and restores native Firefox checking
when a field cannot be processed safely. **No claim of universal editor support**.

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
