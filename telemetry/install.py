#!/usr/bin/env python3
"""Install the opt-in ELF//SHELL native host in a regular Linux Firefox profile."""
import json
from pathlib import Path
import sys

NAME = "com.elfshell.ayarime.telemetry"
EXTENSION_ID = "elf-shell-ayarime@local.theme"


def main():
    if sys.platform != "linux":
        raise SystemExit("This installer currently supports Linux Firefox only.")
    host = Path(__file__).resolve().parent / "host.py"
    if not host.is_file():
        raise SystemExit("Cannot locate telemetry/host.py")
    host.chmod(host.stat().st_mode | 0o111)
    target = Path.home() / ".mozilla" / "native-messaging-hosts" / (NAME + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "name": NAME, "description": "ELF//SHELL local read-only Linux sensor monitor",
        "path": str(host), "type": "stdio",
        "allowed_extensions": [EXTENSION_ID],
    }, indent=2) + "\n", encoding="utf-8")
    target.chmod(0o600)
    print("Native telemetry host installed:", target)
    print("Open a new ELF//SHELL tab and select ENABLE TELEMETRY.")
    print("The companion runs only when Firefox requests a reading.")
    print("To uninstall, delete:", target)


if __name__ == "__main__":
    main()
