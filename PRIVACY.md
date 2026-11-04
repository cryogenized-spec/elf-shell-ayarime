# Privacy statement — ELF//SHELL

ELF//SHELL does not collect or transmit analytics, telemetry, crash reports, browsing history, page contents, or personal information to a developer-controlled server. It has no developer-controlled server. Scripts, styles, wallpaper and launcher images are included in the extension package.

Firefox extension-local storage holds local notes, preferences, quick-link URLs, editable search templates and optionally saved sets of tab URLs. This storage is not encrypted. A JSON export includes this information. Users should avoid storing credentials or exporting private session URLs.

The extension requests the `theme`, `search` and `storage` permissions for its browser appearance, default-engine search and local settings. The `tabs`, `sessions`, `bookmarks` and `history` permissions are optional, explained in the interface and revocable. No remote host access is requested for content scripts. The optional `https://*/*` host permission is available solely so users can choose arbitrary HTTPS RSS or Substack publications, and access is requested at runtime for each exact feed domain before fetching. Rejecting permission prevents that feed from being fetched. Host permissions can be revoked in the NET FEED manager or Firefox settings.

Searches submitted through Firefox or a custom bang, quick links clicked by the user and websites restored from saved sessions necessarily contact the corresponding external service. Those services' own privacy policies apply. ELF//SHELL does not send anything to these services except in response to the user's chosen action, or periodic RSS feed checks after the user has opted into a subscription and granted its website access. These requests go directly to the chosen publication and disclose the normal connection information such as IP address to that publication. RSS checks omit cookies and referrer headers. No developer-controlled tracking service is involved.

RSS publication URLs, custom titles, groups, source status and recent article headlines and URLs are stored locally without encryption. JSON export contains subscriptions, but not cached headline data; OPML export contains feed addresses and names. Importing OPML does not contact those publications until the user separately grants permission.

Ayarime Memory Trace quotations are packaged in a local JSON asset and involve no external requests. Quote display preferences, favourites, pinned entries, category filters and rotation timestamp are stored in Firefox extension-local storage without encryption. JSON station exports include these quote preferences.

## Mozilla manifest disclosure (0.5.1)

`browser_specific_settings.gecko.data_collection_permissions.required` is `['none']`: the extension itself does not collect or transmit user data to a developer, analytics provider, or its own servers. Users can **optionally** authorise direct HTTPS fetches to their selected public RSS/Atom publishers. The destination sees the usual network request/IP address, but the extension does not relay browsing history, personal notes, or quick links to those publishers. Redirects are refused. As with any browser, manually opening search results or quick links contacts the selected website.
