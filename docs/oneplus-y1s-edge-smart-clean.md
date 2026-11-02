# OnePlus TV 32 Y1S Edge: Safe Smart Clean

The OnePlus TV 32 Y1S Edge ships with Android TV 11, approximately **1 GB RAM and 8 GB storage**, and a **1366 x 768** panel. Favor reclaiming real storage and reducing confirmed optional bloat over aggressive task killers. The supplied tool is an **ADB-side helper**, not an APK installed on the TV.

## Usage

Connect your computer to the same network, enable/authorize Android TV debugging as in the main README, install tools/requirements.txt, and set TV_HOST.

Linux/macOS:

    TV_HOST=192.168.1.50 python3 tools/smart_clean.py
    TV_HOST=192.168.1.50 python3 tools/smart_clean.py --apply
    TV_HOST=192.168.1.50 python3 tools/smart_clean.py --apply --target-free-mb 768

Windows PowerShell:

    $env:TV_HOST = '192.168.1.50'
    python tools/smart_clean.py
    python tools/smart_clean.py --apply

The script uses the same connection supported by tools/tv.py, including a paired TV_ADB_BINARY transport if configured.

- **Default:** read-only scan of device model, Android version, /data free space, available RAM, user-app count and disabled-package count.
- **--apply:** invokes Android's pm trim-caches with a *desired free-space target* (default 1024 MiB), then measures free space again. This does NOT mean it deletes 1024 MiB. Android may choose to free nothing, and caches can be rebuilt later.
- **--json:** prints a before/after comparison. No IP addresses, Wi-Fi names, or installed-app names are included.
- **Never:** clears accounts or app data, deletes downloads/media, uninstalls or force-stops apps, disables packages, changes the launcher, touches audio/HDMI/DRM components, or promises artificial RAM boosts.

## Deeper, reversible debloating

Before creating a Y1S Edge-specific debloat list, collect the **actual installed package list** with:

    python tools/tv.py "pm list packages"

Do not blindly reuse the example profiles for OnePlus Y1, Dosa, Cebu, or Dubai: the firmware and critical services can differ. The existing tools/disable.sh and tools/restore.sh include critical-package guards and recovery records. Keep the stock HOME handler until a reliable replacement is verified, and preserve Settings, Google Play services, voice, Cast, HDMI/input, Wi-Fi, Bluetooth, software updater, audio/Dolby, and DRM unless a component is identified as genuinely optional and the change is tested and reversible.

Turn off ADB/network debugging after the operation. Keep your own device inventory private rather than posting identifiable TV information in public issues.
