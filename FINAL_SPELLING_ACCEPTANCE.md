# ELF//SHELL — Ayarime: final spelling acceptance (Firefox desktop)

**Purpose:** User-led acceptance **before** Mozilla signing. Use only disposable public
text on a known public website. Do not open private notes, saved credentials,
customer information, work email, or financial records during this exercise.

**Target:** v0.5.4 review candidate after PR #21 is merged into
`release/v0.5.4-review`. The native Linux cursor-theme work is separate.
Website-wide cursor injection is intentionally removed; the dashboard-only
pointer gallery remains.

## Load and back up

1. Export your existing Ayarime settings to a safe private JSON file, if
   using a previous temporary installation. Avoid uploading that file: it can
   contain personal shortcut URLs, notes and saved workspaces.
2. Fetch the latest **release/v0.5.4-review** commit from the repository and
   use Firefox's `about:debugging#/runtime/this-firefox` → Load Temporary
   Add-on → `manifest.json` (or Reload for an already loaded add-on).
3. Open a fresh tab: confirm the six launchers, dashboard pointer styles,
   typography, search/calculator, notes and workspace links still work.
   Firefox website tabs should use the system cursor, not forced Ayarime CSS.
4. In **STATION → CONFIGURE STATION → FIREFOX SPELLING INTEGRATION**, choose
   **Enable separately per website** for the first test. Do not grant
   all-HTTPS access yet.

## Per-site permission and local spellchecking

1. Open a public, compatible rich-text demo, e.g. https://prosemirror.net/.
2. Click the **ELF//SHELL toolbar icon**, then **OPEN SITE SPELLING CONTROLS**.
   A *separate Ayarime browser tab* opens. Click **ENABLE SPELLING FOR THIS
   SITE**, then explicitly approve Firefox's request for that site.
3. Return to the demo and type: `This is a mispeled sentance.`
4. Expected: misspelled words receive underlines after the local checker
   completes. A **left click** on `mispeled` shows suggestions; choosing
   `misspelled` changes only that word. **Ctrl+Z** restores the original.
   A right-click still offers normal Firefox context actions.
5. If the manager specifically says that *immediate activation failed*
   and instructs you to reload, first save any web editing work, **manually
   reload that website tab**, and retry. Do not reload unsaved content.
   Report the exact manager message if it fails after reload.
6. Return to the persistent site-controls tab, click **DISABLE SPELLING FOR
   THIS SITE** and verify Firefox's native spelling is restored without
   changing the text already entered.

## Normal fields, keyboard, exclusions

1. Enable all-HTTPS spelling explicitly from STATION only if comfortable
   granting Firefox the optional broader website access.
2. On a **public test form**, type `Unusualy spelt word` into a normal
   textarea and a single-line text input. Left-click within `Unusualy`:
   Ayarime should offer `Unusually`, replacing just that word. Ctrl+Z
   should undo, and Firefox's native spelling underlines/right-click menu
   should remain available on these standard fields.
3. When the suggestions open, press **Tab** or **ArrowDown**, then
   **Escape**. The menu should close and focus should return to the original
   field. Normal typing must continue.
4. Check an editor that explicitly sets `spellcheck=false` or inherits
   `spellcheck=FALSE`; Ayarime must respect that choice. Password, code,
   private, readonly and disabled fields must be ignored.
5. Check a real framework-controlled editor you use (for example ChatGPT)
   with disposable text. If it rejects a correction or interferes with typing,
   report the precise behaviour and keep the native Firefox fallback; do not
   treat one demo success as universal compatibility.

## Permissions, RSS privacy and final result

1. In STATION choose **Firefox native spelling only**, then verify injected
   spelling stops on already-open test tabs. To revoke global website access,
   click **REVOKE BROAD HTTPS ACCESS**.
2. Importing a public OPML file must **not** cause network requests solely
   because all-HTTPS spelling access was approved. Each feed requires its own
   explicit **NET FEED → ALLOW HOST** (or Subscribe) approval.
   Existing RSS subscriptions from older versions may need a one-time
   Allow Host confirmation after this privacy hardening.
3. Inspect the Firefox extension Debug Console if any step fails; capture
   only technical errors, not contents of unrelated websites.
4. Report PASS / FAIL / NOT TESTED for the areas above, plus exact Firefox
   version and whether Linux Mint uses an X11 or Wayland session. A failed
   step means **no Mozilla submission** until investigated.

**No AMO submission, signing or public listing should be attempted until the
owner explicitly approves this final acceptance.** A temporary Firefox add-on
is automatically removed on a browser restart; permanent installation comes
only from a Mozilla-signed build.
