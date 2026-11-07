# ELF//SHELL / Linux hardware telemetry

Firefox extensions cannot directly interrogate Linux hardware sensors. This **optional**, read-only Native Messaging host provides CPU temperature (coretemp/k10temp), GPU temperature (NVIDIA nvidia-smi or exposed hwmon), RAM usage, available fan speeds and one-minute system load.

## Install (Linux Mint / native Firefox)

From the checked-out repository directory:

```bash
python3 telemetry/install.py
```

Then open an ELF//SHELL new tab and click **ENABLE TELEMETRY**, confirming Firefox's optional `nativeMessaging` permission. Sensor refreshes occur about every 15 seconds while a dashboard tab is open. Disabling it revokes the permission and stops polling. The host is launched on demand, not a permanent background daemon.

If no compatible hardware sensor is exported, its value shows **N/A**. On NVIDIA systems, `nvidia-smi` is used when available. Standard Linux sensor paths are read using the Python standard library; no extra Python packages or root privileges are needed. If Firefox is packaged as a Snap or Flatpak, native-messaging host setup may instead require its portal/proxy integration.

## Privacy and removal

The host communicates **only through local Firefox native-message standard input/output**. It does not read browsing history, contact a network server, report serial numbers or collect analytics. It only recognises the fixed `{"action":"read"}` message. The Firefox allowed extension ID is `elf-shell-ayarime@local.theme`.

Disable the feature from the dashboard. To remove the native host registration entirely:

```bash
rm ~/.mozilla/native-messaging-hosts/com.elfshell.ayarime.telemetry.json
```

Removing the registration does not delete or modify the Python files.
