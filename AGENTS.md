# ELF//SHELL — Ayarime contributor guidance

This is a Firefox WebExtension. Work toward a privacy-first, no-telemetry release. Keep browser permissions optional where practical and preserve the established Ayarime visual identity.

## Code Review Rules

### Permissions and browser safety
Do not request blanket runtime host access or access browsing data without an explicit user gesture. Feed permissions must be per HTTPS host. Tab cleanup must be scoped to the current browser window, exclude incognito tabs, and preserve a recoverable URL list on failure.

### Remote feed content
Treat feed XML, titles, links and imported OPML as untrusted. Use DOMParser and textContent, never inject remote strings with innerHTML. Reject javascript:, data: and unsafe redirects. Keep fetching bounded by time and byte caps; cache only the locally needed metadata.

### Storage and release integrity
Local notes and browser state are unencrypted; avoid claiming otherwise. Never report a successful save if the storage write fails. Preserve the extension's stable Firefox ID and storage keys on upgrade, and do not claim real-Firefox verification from Chromium or mocks.


Issue #2 review priorities: reject local/reserved RSS hostnames including dotted `localhost.`, atom namespace links cannot impersonate RSS item links, generation-guard async feed renders, background-serialize subscription/cache changes across dashboard instances, and reserve duplicate-recovery addresses in unencrypted local storage *before* closing tabs. Check failed browser-storage writes and explicit recovery-history clearing. Native Firefox confirmation remains mandatory before release.

### Additional cache and tab race safety
Do not replay every RSS cache entry when only one feed changed; send only changed records and protect successful headlines from older background writes. After any async recovery reservation, recheck the actual browser tab URL/window/protected status before closing it. Tests must simulate tab navigation and window moves while storage is pending.

For RSS cache reviews, compare successful article revisions by `checkedAt`, not solely by `attemptedAt`; a later failed attempt must never block a delayed successful batch with newer checked headlines.
