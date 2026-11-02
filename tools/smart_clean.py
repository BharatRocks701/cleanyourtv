#!/usr/bin/env python3
"""Safe Android TV cleaning over the repository's existing ADB transport.

Read-only by default. With --apply, ask Android to trim *recreatable app
caches* toward a free-space target. This deliberately never disables packages,
uninstalls apps, clears app data, deletes downloads, or kills system processes.

Example:
    TV_HOST=192.168.1.50 python3 tools/smart_clean.py
    TV_HOST=192.168.1.50 python3 tools/smart_clean.py --apply
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TV_TOOL = Path(__file__).resolve().with_name("tv.py")


class TVCommandError(RuntimeError):
    pass


def tv_shell(command: str, timeout: int = 60) -> str:
    """Run a fixed ADB command via tv.py; never invoke a local shell."""
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(TV_TOOL), command],
            text=True, capture_output=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TVCommandError(f"TV did not answer within {timeout}s: {command}") from exc
    except OSError as exc:
        raise TVCommandError(f"Could not launch TV client: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise TVCommandError(f"TV command failed ({command}): {detail}")
    return result.stdout.strip()


def parse_storage(output: str):
    """Read only /data disk usage from df -k; report KiB as bytes."""
    for line in reversed(output.splitlines()):
        columns = line.split()
        if len(columns) < 6 or columns[-1] != "/data":
            continue
        try:
            total, used, free = [int(x) * 1024 for x in columns[1:4]]
        except ValueError:
            continue
        return {"total_bytes": total, "used_bytes": used, "free_bytes": free}
    return None


def parse_memory(output: str):
    result = {}
    for key in ("MemTotal", "MemAvailable"):
        match = re.search(rf"^{key}:\s*(\d+)\s+kB", output, re.MULTILINE)
        if match:
            result[key.lower() + "_bytes"] = int(match.group(1)) * 1024
    return result


def take_snapshot():
    # None of these commands change the TV.
    props = {name: tv_shell(f"getprop {name}") for name in (
        "ro.product.brand", "ro.product.model", "ro.build.version.release")}
    storage = parse_storage(tv_shell("df -k /data"))
    memory = parse_memory(tv_shell("cat /proc/meminfo"))
    third_party = tv_shell("pm list packages -3")
    disabled = tv_shell("pm list packages -d")
    return {
        "brand": props["ro.product.brand"],
        "model": props["ro.product.model"],
        "android_version": props["ro.build.version.release"],
        "storage": storage,
        "memory": memory,
        "third_party_apps": sum(line.startswith("package:") for line in third_party.splitlines()),
        "disabled_packages": sum(line.startswith("package:") for line in disabled.splitlines()),
    }


def mb(byte_count):
    return "unavailable" if byte_count is None else f"{byte_count / 1024**2:.0f} MiB"


def show(label, snapshot):
    print(f"\n{label}: {snapshot['brand']} {snapshot['model']} (Android {snapshot['android_version']})")
    disk = snapshot["storage"]
    if disk:
        print(f"  Storage: {mb(disk['free_bytes'])} free / {mb(disk['total_bytes'])} total")
    else:
        print("  Storage: unable to read /data; no space estimate available")
    mem = snapshot["memory"]
    print(f"  RAM available: {mb(mem.get('memavailable_bytes'))}")
    print(f"  Installed user apps: {snapshot['third_party_apps']}; disabled packages: {snapshot['disabled_packages']}")


def trim_caches(target_mb: int):
    # Android Package Manager semantics: target desired free space, NOT MB to delete.
    answer = tv_shell(f"pm trim-caches {target_mb}M", timeout=180)
    if re.search(r"(?im)^(error:|exception|failure|unknown command|securityexception)", answer):
        raise TVCommandError(f"Android did not accept cache trimming: {answer}")
    return answer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Ask Android to trim disposable caches; otherwise report only")
    parser.add_argument("--target-free-mb", type=int, default=1024,
                        help="Desired free disk space, NOT bytes to delete (default 1024 MiB; 256..2048)")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args(argv)
    if not 256 <= args.target_free_mb <= 2048:
        parser.error("--target-free-mb must be between 256 and 2048")
    if not os.environ.get("TV_HOST"):
        parser.error("Set TV_HOST to your TV IP or paired ADB endpoint before running")
    try:
        before = take_snapshot()
        after = None
        reply = ""
        if args.apply:
            reply = trim_caches(args.target_free_mb)
            after = take_snapshot()
    except TVCommandError as exc:
        parser.exit(2, f"Smart Clean stopped: {exc}\nNo apps were disabled or uninstalled.\n")

    result = {"mode": "apply" if args.apply else "report-only",
              "target_free_mb": args.target_free_mb if args.apply else None,
              "before": before, "after": after, "android_reply": reply}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        show("Before", before)
        if after:
            show("After", after)
            a, b = before["storage"], after["storage"]
            if a and b:
                delta = b["free_bytes"] - a["free_bytes"]
                print(f"  Free-space change: {delta / 1024**2:+.0f} MiB (measured, not estimated)")
        else:
            print("  Read-only scan complete. Use --apply to request a cache trim.")
        print("  No apps/data/downloads removed; Android may rebuild caches later.")
        print("  Note: this is an ADB utility, not an on-TV cleaning APK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
