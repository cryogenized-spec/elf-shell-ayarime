# Privacy statement — ELF//SHELL — Ayarime

ELF//SHELL is a locally run Firefox new-tab dashboard and optional browser
theme. It has no developer-operated server and does not collect or transmit
analytics, telemetry, crash reports, or browsing history to the developer.
Runtime artwork, fonts, scripts and icons are bundled locally.

**There is no custom website spellchecker in this release.** The extension
does not inject content scripts into other sites, read typed words in
webpage editors or send text to an AI/spelling service. Firefox's own
native spelling checker remains the user's choice.

Firefox extension-local storage holds dashboard notes, focus, configuration,
launcher URLs, memory-quote preferences, subscriptions, locally cached
public feed headlines, and optionally named browser tab sets and duplicate
recovery URLs. It is **not encrypted**. URLs sometimes contain private
tokens and query parameters. JSON and OPML exports contain user-defined
settings/URLs and should be handled as potentially sensitive documents.
Bookmark and browsing-history APIs are used only when the user explicitly
requests the corresponding feature.

## Browser permissions

- Required: theme, search, storage. Firefox chrome tint and user-initiated
  searches use Mozilla's supported browser APIs.
- Optional: tabs, sessions, bookmarks, history for explicitly requested
  workspace utilities; these may be denied or revoked.
- Optional HTTPS host access (https://*/* declaration): **only** for
  user-chosen RSS/Atom publications. This is not an installation-time blanket
  grant. Each publisher requires explicit Firefox permission during
  subscription, plus a distinct stored record of approved feed URLs.
  Importing an OPML/JSON backup never grants RSS approval. Previously saved
  feeds may require a one-time reapproval.

The extension never sends a user's notes, saved tabs, locally stored
settings or editor text to a developer-controlled server. Search terms,
user-opened links and restored tabs naturally contact websites selected by
the user. Opt-in RSS requests go **directly** to approved publishers;
those hosts see ordinary connection metadata, including IP addresses.
RSS requests omit credentials and referrers and reject redirects.
Cached feed metadata contains titles, dates and URLs, not article bodies.

## Native Linux cursor package

The optional Ayarime Linux cursor archive is **not a Firefox extension
dependency** and contains no networking or spelling component. Its installer
copies locally compiled Xcursor theme files into the user's
~/.local/share/icons directory without sudo or automatically changing
the active cursor. It can be removed independently. Artwork licensing
is documented in ARTWORK_LICENSE.md.

## Mozilla data-collection disclosure

The manifest's Firefox data-collection declaration is required: none.
This means there is no developer data-collection endpoint; it does
not claim user-authorized searches and RSS requests never contact
external websites.
