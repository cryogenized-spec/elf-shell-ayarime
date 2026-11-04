# ELF//SHELL — Ayarime v0.5.1 (release candidate)

**Status:** Source-tested and packaged; not yet a stable Mozilla release. Lint, live Firefox acceptance, and AMO signing/review still required.

This release is a targeted stability and security pass over v0.5.0. No new major features were introduced.

## Corrections

- Adds Firefox `browser_specific_settings.gecko.data_collection_permissions.required = ["none"]`, indicating that no user data is collected/transmitted to developer-controlled services. Optional RSS downloads still contact user-approved publisher domains.
- Raises minimum desktop Firefox version from 109 to **140**, compatible with the built-in data collection disclosure experience.
- Adds explicit extension-page CSP to load scripts and styles locally, disallow plugins and restrict image sources.
- Fixes erroneous rewriting of unrelated `/p/article` URLs into `/feed` addresses (known Substack-hosted domains only; custom domains require explicit `/feed`).
- Refuses RSS redirects rather than potentially contacting another host without prior approval. Validates cached article links before presenting them.
- Compares complete URLs in duplicate-tab cleanup, preserving hash-fragment-specific app views.
- Escape clears the current search query and dismisses the overlay.
- Makes the AMO upload archive deterministic and avoids including source tests and auxiliary documentation in the runtime package.
- Introduces a GitHub Actions release-quality gate: source tests, clean package, Mozilla linter (warning-as-error), and package verification.

## Automated evidence

- `npm test`: PASS (syntax, 12 icons, command routing, arithmetic, session data sanitation, RSS URL/OPML hygiene, 28 story fragments, privacy manifest and release asset checks)
- `python3 scripts/package.py --verify-only`: PASS (31 runtime files; byte-for-byte verified)
- `tinycss2` CSS parser: no top-level syntax errors
- `web-ext lint`: NOT EXECUTED (npm registry DNS unavailable in this container; CI configured to run it)
- Live Firefox tests: NOT EXECUTED (Firefox binary unavailable here; Chromium refuses localhost navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`)
- AMO signing/public listing: NOT EXECUTED; approval is required for stable install.

For the final release gate, follow `LIVE_FIREFOX_TESTS.md` on a real Firefox installation.
