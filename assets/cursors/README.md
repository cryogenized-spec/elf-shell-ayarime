# Ayarime — six cursor concepts

These six transparent 64 × 64 PNG prototypes were extracted from the **original six-design AYARIME CURSOR CONCEPTS sheet** created in the project conversation on 4 November 2026.

They deliberately preserve the artwork's six identities:

| Concept | Image |
| --- | --- |
| 01 — Classic Spearhead | ![Classic Spearhead](classic-spearhead.png) |
| 02 — Crystal-Tech Shard | ![Crystal-Tech Shard](crystal-tech-shard.png) |
| 03 — Elven Feather | ![Elven Feather](elven-feather.png) |
| 04 — Hollow Frame | ![Hollow Frame](hollow-frame.png) |
| 05 — Rune-Edged | ![Rune-Edged](rune-edged.png) |
| 06 — Minimal Precision | ![Minimal Precision](minimal-precision.png) |

## Current integration

**Station Configuration → Pointer Design** provides an opt-in choice of the six designs, plus **System Default** (the default).

The selected design is stored in a dedicated ELF//SHELL workspace field, included in configuration backup/import, and synchronised across open ELF//SHELL new-tab pages. Cursor paths are strictly allowlisted—no arbitrary filesystem or URL values are imported.

The pointer is **only applied to the ELF//SHELL dashboard**. Firefox's address bar, native context menus, other websites, and the Linux Mint system pointer remain unchanged. On dashboard inputs/textarea, the normal I-beam text cursor is preserved.

## Design and QA status

- Original artwork → foreground-masked, palette-optimised transparent PNGs. These are **prototypes**, not a pixel-perfect vector trace; source art can be reworked after visual review.
- 64 × 64 with a top-left 2 × 2 hotspot for every design; this is an initial alignment subject to live Firefox and high-DPI testing.
- Verify under 100%, 150%, 200% display scaling, with left/right mouse handedness and high-contrast system settings.
- Browser cursor size support may differ by platform; the final theme can include 32/48-pixel versions if necessary.
- The separate optional native Linux Xcursor distribution in linux-cursors/ can install these designs per-user, reversibly, without changing system preferences automatically.

All assets are local: no runtime downloads, external image hosts, telemetry, or remote assets.


## Ayarime six-state functional cursor family

The optional **Ayarime Core · Six States** choice is derived from the six-state
concept sheet supplied for the project: Pointer, Text (I-beam), Busy,
Crosshair, diagonal Resize and Link Hand.

Transparent 48×48 PNGs are used for CSS cursor images, with native keyword
fallbacks. 64×64 variants are bundled for previews and HiDPI evaluation.
The silhouettes exclude the decorative selection circles, labels and frames.

The six original pointer alternatives are still available, with their normal
cursor appearance unchanged. When any custom pointer is selected, common
interactive, text, busy, precision and resize targets use the coordinating
state artwork. System Default overrides nothing.

The Busy design is currently STATIC. Gecko may display only the first frame
of an animated GIF/APNG in a CSS cursor. Browser-native Firefox chrome,
menus, other websites and operating-system cursors remain unaffected.

Test hotspot accuracy and contrast on actual Firefox/Linux Mint at
100%, 150% and 200% display scaling before stable release.
