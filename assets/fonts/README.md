# Locally bundled typography for ELF//SHELL — Ayarime

The nine Latin font files in this directory are WOFF2 assets sourced from
[Fontsource's public font-files collection](https://github.com/fontsource/font-files)
at `fonts/google/<family>/files/<family>-latin-<weight>-<style>.woff2`.
All assets are distributed under the SIL Open Font License 1.1.
Each font family's original copyright and full licence are preserved
verbatim under `licenses/<family>-OFL.txt`.

| Font family | Bundled weights/styles | Role |
| --- | --- | --- |
| Cormorant Garamond | 400 normal, 400 italic | Ayarime Classic headings |
| Rajdhani | 400 normal, 600 normal | Futuristic controls |
| IBM Plex Mono | 400 normal | Diagnostics |
| Oxanium | 400 normal | Neural Interface headings |
| JetBrains Mono | 400 normal | Neural Interface diagnostics |
| Marcellus | 400 normal | Archive headings |
| IBM Plex Sans | 400 normal | Archive controls |

The Japanese typography options use **locally installed** Noto Serif JP /
Noto Sans JP (including installed Noto CJK family alternatives), with
standard Japanese font fallbacks. Large Japanese language font files are
intentionally not bundled. This keeps the add-on compact, avoids remote
requests, and preserves usable Japanese glyphs through Firefox's font
fallback mechanism.

All font URLs in `typography.css` are extension-relative. The add-on makes
no connection to Google Fonts, Fontsource, or other font delivery services
at runtime. The Original preset avoids the new typography overrides, so
existing appearances remain unchanged for existing users.
