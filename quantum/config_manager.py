"""
Config manager for Quantum/Gesture settings.

Reads and writes quantum_config.json at the project root.
All other modules call load() to get current settings.
The settings panel (web UI) calls save() via eel to persist changes.
"""

import json
import os

_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'quantum_config.json'
)

# Defaults — also serve as the schema (only these keys are accepted)
DEFAULTS = {
    "gesture_stability": 4,   # frames to confirm a gesture  (1 = fast/jittery, 10 = slow/stable)
    "pinch_threshold":   0.3, # displacement to register pinch (0.1 = very sensitive, 0.9 = stiff)
    "scroll_speed":      3,   # lines per scroll tick         (1 = slow, 10 = fast)
    "cursor_speed":      2.1, # max cursor movement ratio     (0.5 = slow, 5.0 = fast)
}


def load() -> dict:
    """Return current config, merged with defaults for any missing keys."""
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, encoding='utf-8') as f:
                data = json.load(f)
            return {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    except Exception:
        pass
    return dict(DEFAULTS)


def save(data: dict) -> bool:
    """Persist *data* (partial or full) by merging into current config."""
    try:
        current = load()
        for k, v in data.items():
            if k in DEFAULTS:
                current[k] = v
        with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2)
        return True
    except Exception:
        return False
