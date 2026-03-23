"""
Session statistics for the Quantum Dashboard.

Tracks command history and response times during the current session.
All other modules call track_command() once per command; the dashboard
reads get_dashboard_data() via Eel every few seconds.
"""

import datetime
import collections
import os
import json

_session_start = datetime.datetime.now()
_command_history = []       # [{cmd, time, ms}]  — capped at 100
_command_counts = collections.Counter()
_GESTURE_STATS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gesture_stats.json')


def track_command(cmd: str, response_ms: float = 0) -> None:
    """Record one command execution. Call this at the start of respond()."""
    _command_history.append({
        'cmd': cmd[:80],                                          # truncate long inputs
        'time': datetime.datetime.now().strftime('%H:%M:%S'),
        'ms': round(response_ms),
    })
    _command_counts[cmd.split()[0] if cmd.split() else cmd] += 1  # count first word
    if len(_command_history) > 100:
        _command_history.pop(0)


def get_dashboard_data() -> dict:
    """Return all dashboard data as a JSON-serialisable dict."""
    import psutil

    uptime_s = int((datetime.datetime.now() - _session_start).total_seconds())
    hours, rem = divmod(uptime_s, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours:02d}:{mins:02d}:{secs:02d}"

    # System stats
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    battery = None
    try:
        b = psutil.sensors_battery()
        if b:
            battery = {'percent': round(b.percent), 'charging': b.power_plugged}
    except Exception:
        pass

    # Gesture stats (written by Gesture_Controller subprocess)
    gesture_stats = {}
    try:
        if os.path.exists(_GESTURE_STATS_FILE):
            with open(_GESTURE_STATS_FILE) as f:
                gesture_stats = json.load(f)
    except Exception:
        pass

    return {
        'session_start': _session_start.strftime('%I:%M %p'),
        'uptime': uptime_str,
        'total_commands': len(_command_history),
        'command_history': list(reversed(_command_history[-20:])),   # newest first
        'top_commands': dict(_command_counts.most_common(8)),
        'cpu_percent': cpu,
        'ram_percent': ram.percent,
        'ram_used_gb': round(ram.used / 1024 ** 3, 1),
        'ram_total_gb': round(ram.total / 1024 ** 3, 1),
        'battery': battery,
        'gesture_stats': gesture_stats,
    }
