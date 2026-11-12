#!/usr/bin/env bash
# Non-root user-only setup. Does not silently change the current cursor or
# turn on an always-running accessibility service.
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:-all}"
case "$mode" in
 cursor|spellcheck|all) ;;
 *) echo "Usage: $0 [cursor|spellcheck|all] [--autostart]" >&2; exit 2;;
esac
if [[ "$mode" == cursor || "$mode" == all ]]; then
  mkdir -p "$HOME/.local/share/icons"
  if [[ -f "$base/prebuilt/ELF-SHELL-Rose/index.theme" ]]; then
    # All three native Xcursor themes are bundled; Pillow isn't needed.
    cp -a "$base"/prebuilt/ELF-SHELL-* "$HOME/.local/share/icons/"
    echo 'Installed ELF-SHELL-Rose, ELF-SHELL-Teal and ELF-SHELL-Gold.'
  else
    if ! /usr/bin/python3 -c 'from PIL import Image' >/dev/null 2>&1; then
      echo 'Install python3-pil before building cursor themes from source.' >&2
      exit 1
    fi
    /usr/bin/python3 "$base/cursors/build.py"
  fi
  echo 'Select a new cursor in Mint System Settings → Themes → Mouse Pointer.'
fi
if [[ "$mode" == spellcheck || "$mode" == all ]]; then
  if ! /usr/bin/python3 -c 'import gi, enchant; gi.require_version("Atspi","2.0"); from gi.repository import Atspi' >/dev/null 2>&1; then
    echo 'Spellcheck prerequisites missing: sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-atspi-2.0 python3-enchant hunspell-en-gb' >&2
    exit 1
  fi
  echo 'Spelling overlay ready. To try: /usr/bin/python3' "\"$base/spellcheck/ayarime_spell.py\""
  if [[ "${2:-}" == '--autostart' ]]; then
    mkdir -p "$HOME/.config/autostart"
    desktop="$HOME/.config/autostart/ayarime-spellcheck.desktop"
    # Desktop Entry Exec quoting is supported for paths containing spaces.
    printf '[Desktop Entry]\nType=Application\nVersion=1.0\nName=Ayarime Spelling Suggestions (experimental)\nComment=Opt-in X11 editable text suggestions\nExec=/usr/bin/python3 "%s" --language en_GB\nTerminal=false\nX-GNOME-Autostart-enabled=true\n' "$base/spellcheck/ayarime_spell.py" > "$desktop"
    echo "Autostart enabled: $desktop"
  else
    echo 'Autostart remains off. Use --autostart only after field testing.'
  fi
fi
