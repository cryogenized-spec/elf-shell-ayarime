# Experimental offline spelling module

This is an optional Firefox WebExtension module, not a system-wide spellchecker.

## Enable

Open the ELF//SHELL toolbar button while viewing an HTTPS site and select
**Enable spelling on this site**. Firefox may ask for host access. Site-specific
access is used to dynamically register content scripts; nothing runs on
unapproved hosts. Existing tabs are initialized after enabling; new tabs
receive the script automatically.

## What works in this draft

- Purely offline, bundled Hunspell-compatible English checking (nspell).
- Red wavy highlights and a quiet **left-click** popup on supported
  `contenteditable` editors.
- Up to six correction proposals, Ignore (current content-script session), and
  Add to Dictionary (extension-local persistent words).
- Native Firefox `spellcheck` is disabled **only after** the replacement checker
  successfully responds for that editor. When the replacement is unavailable,
  the prior `spellcheck` attribute is restored.
- Right-click Copy/Paste and other native menu entries are not intercepted.
- Uses `document.execCommand("insertText")` for selection replacement to
  preserve native undo and rich-editor event behavior as far as supported.
  Incompatible editors must fail without direct DOM rewriting.

## Explicit limitations

- Textareas and ordinary input fields retain the Firefox native spelling
  interface until a reliable underline overlay is implemented. There is no
  duplicate correction menu on those controls.
- Rich editor behavior varies by framework. Native Firefox tests are mandatory
  for editor selection, undo, composition/IME, accessibility and zoom.
- The extension's personal dictionary is **separate** from Firefox's native
  `persdict.dat` personal dictionary. Import/export is a planned follow-up;
  this draft does not modify the native file.
- Disabling the site registration retains any already-granted host access
  because other ELF//SHELL features (RSS) might share that grant. The
  permission can be revoked in Firefox Add-ons settings; a page reload may be
  needed to restore already injected editors.
- No grammar checking, telemetry, external requests or AI calls are performed.
- The custom cursor concept is intentionally not included. Firefox themes
  cannot replace the Linux desktop pointer or consistently style GTK windows.

## Third-party resources

- `nspell-bundle.js`: browserified MIT-licensed nspell by Titus Wormer.
  Licensed under `NSPELL-LICENSE.txt`; the bundle was sourced from
  [Melker/Spell-Checker](https://github.com/melker12345/Spell-Checker)
  and must be reviewed against the upstream nspell source before a release.
- `en.aff` and `en.dic`: British English dictionary from
  [wooorm/dictionaries](https://github.com/wooorm/dictionaries/tree/main/dictionaries/en-GB).
  Licensing and attribution are preserved verbatim in
  `DICTIONARY-LICENSE.txt` (MIT AND BSD).

## Developer checks

Run `npm test` and `python3 scripts/package.py`. The package includes
all files under `spelling/`. Native Firefox verification is still required
and release PR #1 remains separate.

## Review fixes

- Disabling spelling unregisters the site script first and notifies matching open tabs. Tabs that cannot be reached may need reloading; enabling/disabling never automatically revokes host access shared with RSS.
- Long or unusually dense rich-text editors retain native Firefox spellchecking rather than disabling it after a partial 350-token / 4500-character scan.
- Add-to-dictionary writes are serialised in the extension background so concurrent additions from separate tabs cannot overwrite one another.

## Permission/editor safety review

Each spelling request (including initial activation) is checked against the sender's actual HTTPS origin, the exact registered per-site script and current host permission. Immediate injection refuses a tab that has navigated, and permission revocation revalidates already injected tabs. The suggestion menu uses a closed shadow root and trusted user input; pending suggestions close on typing or IME composition, and stale DOM ranges cannot replace changed text.
