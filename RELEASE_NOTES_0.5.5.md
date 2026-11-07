# ELF//SHELL — Ayarime v0.5.5 (unlisted update candidate)

This is a proposed new **unlisted** Firefox Add-ons submission, not an already-signed or publicly listed release. The previous AMO unlisted version is v0.5.4.

## Changes since v0.5.4

- Adds an offline illustrated Memory Archive with the five original bilingual Ayarime story art masters for **Letters from the Lower City** and **Crushed Rainforest Beans**.
- Removes the accidental two-line clamp on compact English and Japanese Memory Trace passages.
- Adds a themed, separately branded ChatGPT website shortcut.
- Adds optional *local-only* Linux hardware readings (CPU/GPU temperatures, RAM, cooling fan RPM and load) using a separately installed, read-only Firefox Native Messaging companion. No network upload, no background daemon, no synthetic sensor readings.
- Retains the spelling-free release implementation and existing RSS/Atom consent protections. The native Linux cursor theme is still a separate package.
- Adds a guarded GitHub Actions workflow for verification and **unlisted** AMO submissions using API credentials stored in protected GitHub secrets.

## Distribution and validation gate

1. Run complete `npm test`, native Firefox tests, package verification, reviewer source rebuild and strict Mozilla lint.
2. Have the project owner explicitly select **submit-unlisted** in the manually invoked Actions workflow (default: verify-only). The optional protected `mozilla-unlisted` environment can require a reviewer.
3. Mozilla processes the update after API submission; the upload request alone does not prove that the version was approved or signed.
4. Retain `elf-shell-ayarime@local.theme` unchanged and do not switch to the `listed` channel without a separate decision.
5. The signed unlisted XPI must be distributed independently. Do not assume installed clients will update automatically until a self-hosted update manifest and signed-XPI distribution flow exist.

See `docs/AMO_AUTOMATION.md` for setup, secrets and release steps.
