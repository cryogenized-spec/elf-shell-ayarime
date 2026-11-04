# ELF//SHELL — Ayarime v0.5.4 (internal Firefox audit candidate)

This is not a signed or stable extension release.

- Scope duplicate-tab cleanup and idle-tab discard to the **current window**, protecting independent workspaces in other windows.
- Keep failed duplicate-URL reopens available for retry rather than silently clearing the recovery list.
- Report failed note writes as **SAVE ERROR** instead of mistakenly showing a save confirmation.
- Extend the mock-Firefox regression suite for these cases.

Still outstanding before public v1.0: real Firefox 140+ integration testing (host permission grant/deny/revoke, sessions, tabs, RSS, search and theme), successful Mozilla web-ext lint, AMO signing and signed add-on restart tests.
