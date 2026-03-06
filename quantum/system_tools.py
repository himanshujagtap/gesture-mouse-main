"""
System utility commands for Quantum assistant.

Handles:
- Startup apps listing (macOS LaunchAgents / Windows Startup folder + registry)
- Network speed test (latency + download sample)
- Risky-action confirmation queue (cleanup desktop, empty recycle bin)
"""

import os
import shutil
import subprocess
import datetime
import time

import quantum.state as state
from quantum.audio_io import IS_MAC, reply


# ---------------------------------------------------------------------------
# Startup apps
# ---------------------------------------------------------------------------

def get_startup_apps_status():
    """
    Return a list of startup app entries and an optional error string.

    Returns
    -------
    (list[str], str | None)
    """
    entries = []

    try:
        if IS_MAC:
            startup_dirs = [
                os.path.expanduser('~/Library/LaunchAgents'),
                '/Library/LaunchAgents'
            ]
            for startup_dir in startup_dirs:
                if os.path.isdir(startup_dir):
                    for item in os.listdir(startup_dir):
                        if item.endswith('.plist'):
                            entries.append(item.replace('.plist', ''))
        else:
            startup_folder = os.path.join(
                os.getenv('APPDATA', ''),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
            )
            if os.path.isdir(startup_folder):
                for item in os.listdir(startup_folder):
                    if not item.startswith('.'):
                        entries.append(item)

            try:
                reg_cmd = ['reg', 'query', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Run']
                result = subprocess.run(reg_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        if line and not line.startswith('HKEY_') and 'REG_' in line:
                            app_name = line.split('REG_')[0].strip()
                            if app_name:
                                entries.append(app_name)
            except Exception:
                pass

    except Exception as e:
        return [], f"Couldn't read startup apps: {e}"

    # Deduplicate while preserving order
    seen = set()
    unique_entries = []
    for item in entries:
        if item not in seen:
            seen.add(item)
            unique_entries.append(item)

    return unique_entries, None


# ---------------------------------------------------------------------------
# Network speed test
# ---------------------------------------------------------------------------

def run_network_speed_test():
    """
    Simple network check: latency + approximate download speed.

    Returns
    -------
    (float, float, int)
        latency_ms, speed_mbps, downloaded_bytes
    """
    import urllib.request

    start_ping = time.time()
    with urllib.request.urlopen('https://www.google.com/generate_204', timeout=7) as _:
        pass
    latency_ms = (time.time() - start_ping) * 1000

    test_urls = [
        'https://proof.ovh.net/files/10Mb.dat',
        'https://speed.hetzner.de/10MB.bin'
    ]

    downloaded = 0
    speed_mbps = None
    last_error = None

    for test_url in test_urls:
        try:
            start_dl = time.time()
            with urllib.request.urlopen(test_url, timeout=12) as response:
                chunk = response.read(2 * 1024 * 1024)
            elapsed = max(time.time() - start_dl, 0.001)
            downloaded = len(chunk)
            speed_mbps = (downloaded * 8) / (elapsed * 1_000_000)
            break
        except Exception as e:
            last_error = e

    if speed_mbps is None:
        raise Exception(f"Download test failed: {last_error}")

    return latency_ms, speed_mbps, downloaded


# ---------------------------------------------------------------------------
# Risky-action confirmation queue
# ---------------------------------------------------------------------------

def queue_confirmation(action, details=None):
    """Queue a risky action and ask the user for explicit confirmation."""
    state.pending_confirmation = {
        "action": action,
        "details": details or {}
    }
    reply("This action may change your system. Are you sure? Say 'confirm' to continue or 'cancel' to abort.")


def execute_pending_confirmation():
    """Execute the queued risky action once the user confirms."""
    if not state.pending_confirmation:
        reply("There is no pending action to confirm.")
        return

    action = state.pending_confirmation.get("action")

    try:
        if action == 'cleanup_desktop':
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            if not os.path.isdir(desktop):
                reply("Desktop folder not found on this system.")
                state.pending_confirmation = None
                return

            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            target_folder = os.path.join(desktop, f'Desktop_Cleanup_{stamp}')
            os.makedirs(target_folder, exist_ok=True)

            moved_count = 0
            for item in os.listdir(desktop):
                if item.startswith('.'):
                    continue
                src = os.path.join(desktop, item)
                if src == target_folder:
                    continue
                try:
                    shutil.move(src, os.path.join(target_folder, item))
                    moved_count += 1
                except Exception:
                    continue

            reply(f"Desktop cleanup complete. Moved {moved_count} item(s) to {target_folder}")

        elif action == 'empty_recycle_bin':
            if IS_MAC:
                os.system("osascript -e 'tell application \"Finder\" to empty trash'")
                reply("Trash has been emptied.")
            else:
                cmd = [
                    'powershell', '-NoProfile', '-Command',
                    'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'
                ]
                subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                reply("Recycle Bin has been emptied.")
        else:
            reply("Unknown pending action. Nothing executed.")

    except Exception as e:
        reply(f"Sorry, I couldn't complete that action: {e}")
    finally:
        state.pending_confirmation = None
