# ELF//SHELL — Ayarime v0.5.4 (internal release audit)

**An original, free and open-source Firefox new-tab workstation and matching browser theme.** A 1990s science-fiction OVA aesthetic, locally bundled illustrated and vector shortcut icons, and a softly melancholic cyber-elf called Ayarime (あやりめ).

Source and bundled images run locally. **No analytics, telemetry, advertisements, remote code, remote fonts, or favicon services.** Your normal web searches and any quick links go to the destinations you explicitly choose. **Optional RSS subscriptions contact their chosen publication sites on the user’s behalf after permission is granted.**

## Install in Firefox for testing

1. Extract the ZIP to a folder on your computer. The `manifest.json` file must be at the top level of that folder.
2. Open `about:debugging#/runtime/this-firefox` in Firefox.
3. Click **Load Temporary Add-on**, then select the extracted `manifest.json`.
4. Open a new tab. If a previous version is still temporarily loaded, unload it first (export settings first).

**Temporary development add-ons disappear when Firefox restarts.** For permanent use, the extension must be signed by Mozilla. This build is **not yet signed or published on addons.mozilla.org**.

The extension reads previous `elfshell-workspace-v3` and `elfshell-workspace-v2` settings automatically when Firefox retains the same extension storage. Temporary add-ons can lose that storage when unloaded; first export the old settings JSON, and then import it into v0.5.2 if needed.

## New in v0.3

- Twelve carefully designed **local SVG launcher icons**; six displayed by default. No live favicon service requests. Choose an icon for each shortcut under **Configure Station**.
- An on-demand **search/action palette** that dims the background only while open. `/` focuses it; `Ctrl+K` also works where Firefox permits a page to receive it.
- `> actions`: fuzzy text filter for local commands, settings, notes, saved workspaces, tab tools and JSON export.
- **Custom search bangs** with editable HTTPS URL templates, such as `!gh firefox`. The template must include `{query}`.
- **Named browser workspaces**: save up to ten sets of up to 40 website tabs and restore each into a new Firefox window. Requires optional **Tabs** permission; all addresses remain stored locally and unencrypted.
- **Manual tab housekeeping**: find duplicate background tabs and discard tabs not accessed for 30 minutes or more. Requires optional **Tabs** permission, and explicit confirmation for each operation. Active, pinned and audible tabs are excluded.
- **Visible permission ledger**: shows mandatory access and optional grants; optional tabs, sessions, bookmarks, and history permissions may be granted or revoked individually.
- Keeps the earlier clock, local notes, focus field, recently closed tabs, calculator, browser search, contrast options, keyboard quick links, privacy controls, and browser-chrome theme.

## Search / keyboard commands

- Plain query + Enter: your Firefox **default search engine**, using the Firefox search API.
- `!yt`, `!gh`, `!ddg`, `!w`: configurable website searches (the URLs and search terms necessarily go to those websites when you choose to search).
- `@ keywords`: search and activate open tabs (**Tabs**, optional).
- `# keywords`: search bookmarks (**Bookmarks**, optional).
- `^ keywords`: search browser history (**History**, optional).
- `> notes`, `> saved`, `> permissions`: filter and run local actions.
- `= 15% of 2400` or `15% of 2400`: offline calculator; Enter copies the result where clipboard access is available.
- `/`: focus the command palette; Escape closes it; arrows select suggestions; number keys 1–6 open launcher links when not typing.

## Privacy details

Required: `theme`, `search`, `storage`. Optional: `tabs`, `sessions`, `bookmarks`, `history`. Optional HTTPS site access is declared for custom RSS feeds but is requested **per exact publication host at the time you subscribe**. No content scripts, management permission, native messaging or developer-controlled analytics. Browser-chrome colours are applied through `browser.theme.update()`.

Notes, settings, user-defined URLs, and named session URLs are stored in Firefox extension-local storage **without encryption**. Avoid putting secrets or authentication tokens in notes and be careful when exporting session URLs (URLs can have sensitive query strings). Local backup JSON files may contain this information. The extension does not automatically read or upload page content. Opt-in subscribed RSS feeds are downloaded directly from their original websites after you grant host access.

The `navigator.onLine` system indicator is only a connectivity hint. The clock is your computer's clock, not an invented year. Firefox may reserve the browser address-bar focus and keyboard shortcuts; we do not override those browser policies.

**Note:** Tab cleanup has been tested at the source/logic level, not yet live in your Firefox profile. Confirm the proposed tab counts carefully before performing destructive actions.

## Build / checks

On any machine with Node.js:

```bash
npm test
```

For Mozilla validation, build the minimal runtime tree and lint that tree with a current version of `web-ext`:

```bash
python3 scripts/package.py
npx --yes web-ext@10.8.0 lint --source-dir dist/amo --warnings-as-errors
```

This step requires an npm network connection (or a previously installed copy of `web-ext`) and **must pass before AMO submission**. See `LIVE_FIREFOX_TESTS.md` for real-browser acceptance steps.

The project uses no npm runtime dependencies; `package.json` exists for repeatable tests and public contributions. A small GitHub Actions workflow runs `npm test` on pushes and pull requests.

## Licence and publishing

- Source code: **MIT** (`LICENSE`).
- Generated Ayarime artwork and locally authored SVG icon assets: permissive project dedication detailed in `ARTWORK_LICENSE.md` (to the extent the contributor has rights to license them). Names and third-party trademarks remain with their respective owners.
- Intended public repository: `cryogenized-spec/elf-shell-ayarime` (not created yet).
- Planned Firefox distribution: signed Firefox Add-ons (AMO) extension, after live testing, Mozilla linting and review. The new-tab override makes it an extension, even though it also themes the browser frame.

**Contributions welcome.** See `CONTRIBUTING.md` for the lightweight workflow.


## v0.4: NET FEED / RSS and Substack subscriptions

The new `NET FEED` button opens a personal publication reader. Nothing is subscribed or fetched by default. Paste a Substack publication homepage (e.g. `example.substack.com`, which is converted to `https://example.substack.com/feed`), a Substack article link, or a direct HTTPS RSS/Atom URL. For a non-Substack site, provide its actual RSS/Atom endpoint rather than its homepage.

Each source receives a separate, visible **host-access approval** in Firefox before its feed is fetched. Rejecting access doesn't add the subscription. You can rename and group subscriptions, enable/disable individual publications, remove subscriptions, and revoke access to a particular domain in the subscription manager. Revoking a host affects all feeds from that same host. The add-on never fetches a publication unless its host is authorised.

Feed metadata (titles, published dates and links) is cached in Firefox local storage. No article bodies, remote images, cookies, private account data, or credentials are requested or stored. Fetches use `credentials: 'omit'` and `referrerPolicy: 'no-referrer'`; only RSS/Atom XML is parsed and text is displayed using DOM text nodes (not raw HTML). At most 32 subscriptions are supported, 36 entries per feed are cached, and the ticker displays the 180 newest distinct links. Sources update when a new-tab page is open, not through a constantly running background service; the default minimum interval is 30 minutes. You can change it or pause the ticker.

**Backups:** Station Settings → Export JSON includes feed names, groups, enabled state, refresh interval and source URLs (not cached headlines). The RSS manager also exports standard OPML and imports OPML subscriptions without requesting website permissions; users can authorise individual imported hosts afterward. Settings are saved to Firefox `storage.local` and survive normal restarts; uninstalling an extension can remove its local data, so export first.

**Supported feeds:** Public Substack RSS and ordinary public HTTPS RSS 2.0 / Atom / RDF feeds. Private or paid newsletter bodies do not become publicly accessible through RSS; a paid article may only offer a preview, as published by the source. Hosts that block extensions, redirect to an unapproved domain, or require authentication may not load.

**Development status:** RSS logic has passed local Node syntax, URL-permission, settings, OPML and archive integrity checks. Real Firefox WebExtension testing and Mozilla `web-ext lint` still need to be completed before AMO release.

## v0.4.1 — Illustrated default launcher icons

The six default shortcuts now use locally bundled, transparent 256×256 WebP artwork for Browser, Mail, Calendar, Drive, Video and Library. The remaining six selectable icons remain vector SVGs. No off-site icon services or additional permissions are needed. Your existing shortcut labels, destinations and preferences are unchanged.

The artwork is an original themed interpretation, not an official icon set from Mozilla, Google or YouTube. Third-party marks are retained by their owners.


## v0.5 — Ayarime's Memory Trace

The small left-hand quotation panel is now a compact bilingual carousel drawing from **28 curated, original story fragments**, based on the author's dialogue for Ayarime. The quotes establish her nature as a manufactured bio-synthetic sage, her relationship with W.O.T.A.N., the post-collapse world, her informational and quantum abilities, and her role maintaining the elevated biome and extraterrestrial communication relays.

- **Default rotation:** once every 90 seconds. The same quote stays visible across newly opened tabs by using a locally stored time anchor. There are previous/next buttons, pause/resume, and mouse-hover pause.
- **Fragment viewer:** click the quotation to open a full, readable bilingual passage with its unique ID and lore category. The compact HUD displays only a short excerpt; long dialogue is never squeezed into the panel.
- **Language:** Japanese + English (default), Japanese only, English only. Text is displayed in system-installed Japanese-capable fonts, with fallback.
- **Preferences:** set rotation speed (off/30s/90s/3min/5min), categories, favourites (including a favourites-only view), and pinned fragments. All are saved in Firefox extension-local storage, without an account or any network access.
- **Backup:** Station Configuration JSON exports and imports the Memory Trace preferences as well as station settings and optional RSS subscriptions. Earlier v2–v4 backups remain readable.
- **Privacy:** The quotation dataset `assets/ayarime-quotes.json` is bundled locally. Reading or cycling quotes does not transmit any data or require further permissions. The library is editorially curated; it does not contact an AI service or a remote quote API.

The user-supplied fictional dialogue has received **minor Japanese wording adjustments** for clarity and narrative consistency. The full archive is inspectable and editable in `assets/ayarime-quotes.json` for future releases. No story or literary quotation is scraped or fetched from outside sources.

**Development status:** JSON structure, local module, source syntax, DOM IDs, version metadata, and existing station tests are automated. Live Firefox integration and Mozilla AMO lint are still required before public release.

## 0.5.1 — release hardening

- Firefox **140+** is required. Gecko ID remains `elf-shell-ayarime@local.theme`, preserving the existing extension identity across updates.
- Mozilla's built-in **no developer data collection** disclosure is declared in the manifest. This means no developer-controlled analytics or data transmission. Optional RSS requests still contact the **publications selected by the user**, revealing normal connection information to those publications; details are in `PRIVACY.md`.
- RSS URLs belonging to other domains are no longer silently rewritten when their paths start `/p/`; custom-domain Substack feeds can be added as explicit `https://example.com/feed` addresses.
- Feed redirects are refused to avoid silently contacting an unauthorised site. If a publisher has moved, subscribe to its canonical HTTPS feed address.
- Cached RSS article links are validated before being shown; requests omit credentials and referrer headers. New-tab scripts use a restrictive CSP and no remote code.
- Duplicate tab cleanup now compares **full URLs**, preserving pages whose URL fragments represent different application views.
- Escape clears and closes the search palette.
- Source tests and Mozilla validation are separate gates. Run `npm test` and `npx --yes web-ext@10.8.0 lint --source-dir dist/amo --warnings-as-errors` before submission (after running the packaging script).
- To build the AMO-specific ZIP without development files, run `python3 scripts/package.py`. The source distribution is not the same as the AMO upload package.

This is a **release candidate**, not a signed Mozilla release. Complete the manual Firefox acceptance checklist before calling it production-stable.

### Release checklist

See [`LIVE_FIREFOX_TESTS.md`](LIVE_FIREFOX_TESTS.md) for the required manual acceptance plan. Do not distribute a ZIP as a permanent install: Firefox requires Mozilla signing to keep the extension installed.


### v0.5.2–0.5.3 Station and preview notes

The seven auxiliary links are now under the **Station** menu. Press **Ctrl+K**
(or **Cmd+K** on supported platforms) to open the grouped action palette with
`>` selected. Use arrows and Enter to select, or Escape to close; `/` focuses
normal search. In Browser Access, granted feed-site domains are individually
listed and can be revoked. Duplicate-tab cleanup offers a same-session **reopen
URLs** action; this is not a replacement for restoring unsaved forms.

A locally served preview is useful for UI checks, but Firefox extension
permissions, theme changes, RSS host authorization, and sessions must be verified
in an installed temporary Firefox add-on before release. See `LIVE_FIREFOX_TESTS.md`.

### v0.5.3 Station spacing fix

The Station control uses a two-line centered heading and hint, with a larger gap after the launcher cards. No user settings or permissions are changed.

### v0.5.4 release audit (internal, unsigned)

- Restricts **duplicate cleanup** and **idle tab discard** to the current Firefox window. A matching URL in another window is not a duplicate to close.
- Makes the reopen-URL recovery action retryable if tab creation temporarily fails. This still does not restore unsaved page state.
- Corrects the note-save indicator: rejected storage writes now show **SAVE ERROR**, not **SAVED**.
- Chromium/mock regressions cover cross-window protection, failed-reopen recovery, and storage-write errors.
- **Not final**: requires native Firefox tests, Mozilla `web-ext lint`, and signing.
