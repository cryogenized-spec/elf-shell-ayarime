# Ayarime six-state cursor assets

These transparent 48×48 and 64×64 PNGs were extracted from the user-supplied
ELF//SHELL — Ayarime Cursor Set v1.0 concept sheet.

| Filename prefix | Visual | Dashboard CSS state |
| --- | --- | --- |
| pointer | Silver-violet spearhead | Primary selection |
| ibeam | Illuminated violet I-beam | Text selection |
| busy | Segmented magenta progress wheel | Busy / progress |
| crosshair | Magenta precision star | Precision |
| resize | Diagonal twin-headed spear | Diagonal resize |
| link | Raised cybernetic hand | Links / buttons |

The 48px variants are used for actual dashboard CSS cursors, with explicit
hotspots and system keyword fallbacks; 64px variants are provided for previews
and HiDPI testing. PNG assets contain transparency and are local/offline.

Busy is STATIC. Do not describe it as animated: Firefox does not reliably
animate GIF/APNG CSS cursor images. This is an opt-in Firefox extension
dashboard theme, not a desktop or global Firefox window cursor theme.

Ayarime Core is an additional, opt-in primary cursor choice. The six original
choices remain available. Functional state images are coordinated with all
non-System pointer options; selecting System Default restores native cursors.

Native Firefox QA at 100%, 150% and 200% scaling is still required.
