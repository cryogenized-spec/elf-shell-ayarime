#!/usr/bin/env python3
"""Read-only, one-shot Firefox Native Messaging sensor bridge for ELF//SHELL.
No daemon, sockets, shell commands, user files, or telemetry uploads.
"""
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

HWMON = Path("/sys/class/hwmon")
THERMAL = Path("/sys/class/thermal")
MIB = 1024 * 1024


def read_text(path):
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""


def number(path):
    try:
        return float(read_text(path))
    except ValueError:
        return None


def reasonable_temp(millidegrees):
    if millidegrees is None:
        return None
    celsius = millidegrees / 1000.0
    return round(celsius, 1) if -20 <= celsius <= 120 else None


def sensors():
    cpu_candidates, gpu_candidates, fans = [], [], []
    if HWMON.exists():
        for node in HWMON.glob("hwmon*"):
            driver = read_text(node / "name").lower()
            for sensor in node.glob("temp*_input"):
                temp = reasonable_temp(number(sensor))
                if temp is None:
                    continue
                label = read_text(sensor.with_name(sensor.name.replace("_input", "_label"))).lower()
                if driver in ("coretemp", "k10temp", "zenpower"):
                    score = 0 if "package" in label or "tctl" in label else 1
                    cpu_candidates.append((score, temp))
                elif driver in ("amdgpu", "nouveau"):
                    gpu_candidates.append(temp)
            for sensor in node.glob("fan*_input"):
                rpm = number(sensor)
                if rpm is not None and 0 < rpm < 30000:
                    fans.append(int(rpm))
    cpu_candidates.sort()
    cpu = cpu_candidates[0][1] if cpu_candidates else None
    if cpu is None and THERMAL.exists():
        for zone in THERMAL.glob("thermal_zone*"):
            name = read_text(zone / "type").lower()
            if any(x in name for x in ("x86_pkg_temp", "cpu", "acpitz")):
                cpu = reasonable_temp(number(zone / "temp"))
                if cpu is not None:
                    break
    return cpu, (gpu_candidates[0] if gpu_candidates else None), fans[:4]


def nvidia_temperature():
    # Fixed arguments; never interpolate messages into commands.
    try:
        output = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            check=False, text=True, capture_output=True, timeout=2,
        )
        if output.returncode == 0:
            first = output.stdout.splitlines()[0].strip()
            if re.fullmatch(r"\d+(?:\.\d+)?", first):
                value = float(first)
                if 0 <= value <= 120:
                    return value
    except (OSError, subprocess.TimeoutExpired, IndexError):
        pass
    return None


def memory():
    fields = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            key, _, raw = line.partition(":")
            if key in ("MemTotal", "MemAvailable"):
                fields[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return None, None
    total = fields.get("MemTotal")
    available = fields.get("MemAvailable")
    if total is None or available is None or total < available:
        return None, None
    return round((total - available) / (1024 ** 3), 2), round(total / (1024 ** 3), 2)


def snapshot():
    cpu, gpu, fans = sensors()
    gpu = nvidia_temperature() if gpu is None else gpu
    used, total = memory()
    try:
        load = round(os.getloadavg()[0], 2)
    except OSError:
        load = None
    return {"ok": True, "cpu_c": cpu, "gpu_c": gpu, "fan_rpm": fans,
            "ram_used_gib": used, "ram_total_gib": total,
            "load_1m": load, "at": int(time.time())}


def main():
    # Firefox native messages are 32-bit little-endian length-prefixed JSON.
    length_bytes = sys.stdin.buffer.read(4)
    if len(length_bytes) != 4:
        return
    length = struct.unpack("<I", length_bytes)[0]
    if length > 4096:
        return
    request = sys.stdin.buffer.read(length)
    try:
        message = json.loads(request)
        result = snapshot() if message == {"action": "read"} else {"ok": False, "error": "Unsupported request"}
    except (UnicodeError, ValueError, TypeError):
        result = {"ok": False, "error": "Invalid request"}
    payload = json.dumps(result, separators=(",", ":"), allow_nan=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(payload)) + payload)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
