# ELF//SHELL — Ayarime contributor guidance

This is a Firefox WebExtension. Work toward a privacy-first, no-telemetry release. Keep browser permissions optional where practical and preserve the established Ayarime visual identity.

## Code Review Rules

### Permissions and browser safety
Do not request blanket runtime host access or access browsing data without an explicit user gesture. Feed permissions must be per HTTPS host. Tab cleanup must be scoped to the current browser window, exclude incognito tabs, and preserve a recoverable URL list on failure.

### Remote feed content
Treat feed XML, titles, links and imported OPML as untrusted. Use DOMParser and textContent, never inject remote strings with innerHTML. Reject javascript:, data: and unsafe redirects. Keep fetching bounded by time and byte caps; cache only the locally needed metadata.

### Storage and release integrity
Local notes and browser state are unencrypted; avoid claiming otherwise. Never report a successful save if the storage write fails. Preserve the extension's stable Firefox ID and storage keys on upgrade, and do not claim real-Firefox verification from Chromium or mocks.
