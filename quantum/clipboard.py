"""
Clipboard history manager for Quantum assistant.

Runs a background thread that polls the system clipboard every 0.5 s.
New, non-duplicate items are prepended to a capped list (max 10).
History is persisted to ~/.quantum_clipboard.json so it survives restarts.

Usage
-----
    from quantum.clipboard import start_monitor, get_history, paste_item, clear_history

    start_monitor()           # call once at startup
    get_history()             # → [(n, preview), ...]  1-indexed, newest first
    paste_item(2)             # copy item 2 back to clipboard and simulate Cmd/Ctrl+V
    clear_history()           # wipe everything
"""

import json
import os
import platform
import threading
import time

import pyperclip

_IS_MAC = platform.system() == 'Darwin'

_HISTORY_FILE = os.path.join(os.path.expanduser('~'), '.quantum_clipboard.json')
_MAX_ITEMS = 10
_POLL_INTERVAL = 0.5   # seconds between clipboard polls
_PREVIEW_LEN  = 60     # characters shown in listing

_lock = threading.Lock()
_history: list = []    # newest-first; each element is the raw string
_monitor_thread: threading.Thread | None = None
_stop_event = threading.Event()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _load() -> None:
    """Load history from disk into _history (called once on first start_monitor)."""
    global _history
    try:
        if os.path.exists(_HISTORY_FILE):
            with open(_HISTORY_FILE, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                _history = [str(item) for item in data[:_MAX_ITEMS]]
    except Exception:
        _history = []


def _save() -> None:
    """Write current _history to disk (called inside lock)."""
    try:
        with open(_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(_history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background monitor
# ---------------------------------------------------------------------------

def _monitor_loop() -> None:
    last_text = ''
    while not _stop_event.is_set():
        try:
            text = pyperclip.paste()
            text = text.strip() if text else ''
            if text and text != last_text:
                last_text = text
                with _lock:
                    # Remove duplicate if already in history
                    if text in _history:
                        _history.remove(text)
                    _history.insert(0, text)
                    if len(_history) > _MAX_ITEMS:
                        _history.pop()
                    _save()
        except Exception:
            pass
        time.sleep(_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_monitor() -> None:
    """Start the background clipboard monitor (idempotent)."""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _load()
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()


def stop_monitor() -> None:
    """Stop the background thread (called on app shutdown if needed)."""
    _stop_event.set()


def get_history() -> list:
    """
    Return clipboard history as a list of (n, text) tuples, 1-indexed, newest first.
    *text* is truncated to _PREVIEW_LEN characters for display.
    """
    with _lock:
        return [
            (i + 1, item[:_PREVIEW_LEN] + ('…' if len(item) > _PREVIEW_LEN else ''))
            for i, item in enumerate(_history)
        ]


def get_item(n: int) -> str | None:
    """Return the full text of the n-th clipboard item (1-indexed), or None if out of range."""
    with _lock:
        if 1 <= n <= len(_history):
            return _history[n - 1]
        return None


def paste_item(n: int) -> bool:
    """
    Copy the n-th item back to the clipboard and simulate a paste keystroke.
    Returns True on success, False if n is out of range.
    """
    text = get_item(n)
    if text is None:
        return False
    pyperclip.copy(text)
    # Simulate Cmd+V (macOS) or Ctrl+V (Windows/Linux)
    try:
        import pyautogui
        if _IS_MAC:
            pyautogui.hotkey('command', 'v')
        else:
            pyautogui.hotkey('ctrl', 'v')
    except Exception:
        pass
    return True


def clear_history() -> None:
    """Remove all clipboard history entries and delete the persistence file."""
    global _history
    with _lock:
        _history = []
        try:
            if os.path.exists(_HISTORY_FILE):
                os.remove(_HISTORY_FILE)
        except Exception:
            pass


def ordinal(n: int) -> str:
    """Return English ordinal string for n (1→'1st', 2→'2nd', …)."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"
