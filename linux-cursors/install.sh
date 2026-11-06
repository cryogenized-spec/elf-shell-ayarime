#!/usr/bin/env bash
# Offline, per-user installer for seven optional Ayarime Xcursor themes.
# Never uses sudo, changes system settings or installs a spellchecker.
set -euo pipefail
BASE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
TARGET="$HOME/.local/share/icons"
MODE="--install"
if [[ $# -gt 0 ]]; then MODE="$1"; fi
if [[ ! -d "$BASE/themes" ]]; then
  printf '%s\n' "Missing Ayarime themes directory. Extract the complete archive first." >&2
  exit 1
fi
case "$MODE" in
  --install|--remove|--list) ;;
  *) printf 'Usage: bash install.sh [--install|--remove|--list]\n' >&2; exit 2;;
esac
if [[ "$MODE" == --install ]]; then mkdir -p -- "$TARGET"; fi
count=0
for SOURCE in "$BASE"/themes/Ayarime-*; do
  [[ -d "$SOURCE" ]] || continue
  NAME="$(basename -- "$SOURCE")"
  DEST="$TARGET/$NAME"
  if [[ "$(cat "$SOURCE/.ayarime-cursor-theme" 2>/dev/null)" != "ayarime-cursors-v1" ]]; then
    printf 'Refusing unmarked theme: %s\n' "$SOURCE" >&2
    exit 1
  fi
  case "$MODE" in
    --list)
      if [[ -f "$DEST/.ayarime-cursor-theme" ]]; then
        printf 'Installed: %s\n' "$NAME"
      else
        printf 'Available: %s\n' "$NAME"
      fi
      ;;
    --install)
      if [[ -e "$DEST" ]]; then
        printf 'Already exists (not overwritten): %s\n' "$DEST"
        continue
      fi
      cp -R -- "$SOURCE" "$DEST"
      printf 'Installed: %s\n' "$NAME"; ((count+=1))
      ;;
    --remove)
      if [[ -f "$DEST/.ayarime-cursor-theme" ]] &&
         [[ "$(cat "$DEST/.ayarime-cursor-theme")" == "ayarime-cursors-v1" ]]; then
        rm -rf -- "$DEST"
        printf 'Removed: %s\n' "$NAME"; ((count+=1))
      elif [[ -e "$DEST" ]]; then
        printf 'Not Ayarime-managed; left untouched: %s\n' "$DEST"
      fi
      ;;
  esac
done
if [[ "$MODE" == --install ]]; then
  printf '\nInstalled %d new theme(s) for this user (no sudo).\n' "$count"
  printf '%s\n' 'Open Cinnamon → Themes → Mouse Pointer and select an Ayarime theme.'
  printf '%s\n' 'Restart affected applications or log out/in if the old cursor is cached.'
elif [[ "$MODE" == --remove ]]; then
  printf '\nRemoved %d Ayarime-managed theme(s). Switch to a system pointer before removal when possible.\n' "$count"
fi
