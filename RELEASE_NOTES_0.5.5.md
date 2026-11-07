# ELF//SHELL — Ayarime v0.5.5 (first PUBLIC listing candidate)

The project owner authorised the switch to Mozilla's **listed/public** distribution channel on 7 November 2026. This is a public release candidate for the existing add-on ID, not proof of submission, approval or live publication. The previous AMO version 0.5.4 was unlisted.

## Changes since v0.5.4

- Adds an offline illustrated Memory Archive with the five original bilingual Ayarime story art masters for **Letters from the Lower City** and **Crushed Rainforest Beans**.
- Removes the accidental two-line clamp on compact English and Japanese Memory Trace passages.
- Adds a themed, separately branded ChatGPT website shortcut.
- Adds optional *local-only* Linux hardware readings (CPU/GPU temperatures, RAM, cooling fan RPM and load) using a separately installed, read-only Firefox Native Messaging companion. No network upload, no background daemon, no synthetic sensor readings.
- Retains the spelling-free release implementation and existing RSS/Atom consent protections. The native Linux cursor theme is still a separate package.
- Adds a guarded GitHub Actions workflow for verification and **public/listed** AMO submissions using private API credentials stored in protected GitHub secrets.

## Distribution and validation gate

1. Run complete `npm test`, native Firefox tests, Mozilla lint, reviewer source rebuild and reproducible package verification.
2. Use the existing add-on in Developer Hub; create new **listed** version 0.5.5, not a new add-on. The original ID stays `elf-shell-ayarime@local.theme`.
3. A manually invoked GitHub Actions run can use `submit-listed` (default: verify-only) after credentials are configured in `mozilla-listed`, providing the required public metadata and source archive. If the first conversion cannot be completed by API, use the existing add-on's Upload New Version page.
4. Await Mozilla review, signing and public listing acceptance. Do not claim live publication until verified. Subsequent approved listed updates can use Firefox's built-in AMO update service.

See `docs/AMO_AUTOMATION.md` and `amo/LISTING_COPY.md`.
