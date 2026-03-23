"""
App context detection for Quantum assistant.

Detects which application is currently frontmost so commands can
behave differently depending on what the user is working in.

Usage
-----
    from quantum.context import get_frontmost_app, get_app_category

    app_name = get_frontmost_app()        # e.g. "Google Chrome"
    category = get_app_category()         # e.g. "browser"

Categories
----------
    browser   — Chrome, Safari, Firefox, Brave, Edge, Opera
    vscode    — VS Code, Cursor, Code-OSS
    editor    — PyCharm, IntelliJ, Xcode, Sublime, Atom
    terminal  — Terminal, iTerm2, Alacritty, Warp, Windows Terminal, CMD, PowerShell
    finder    — Finder (macOS), Explorer (Windows)
    office    — Word, Excel, PowerPoint, Pages, Numbers, Keynote
    notes     — Notes, TextEdit, Notepad, Notion, Obsidian
    other     — anything not in the list above
"""

import platform
import subprocess

_IS_MAC = platform.system() == 'Darwin'

# ── App name → category mapping ───────────────────────────────────────────────
_APP_CATEGORIES = {
    # Browsers
    'google chrome':    'browser',
    'chrome':           'browser',
    'safari':           'browser',
    'firefox':          'browser',
    'brave browser':    'browser',
    'brave':            'browser',
    'microsoft edge':   'browser',
    'edge':             'browser',
    'opera':            'browser',
    'arc':              'browser',
    'vivaldi':          'browser',

    # VS Code / forks
    'visual studio code': 'vscode',
    'code':               'vscode',
    'code - insiders':    'vscode',
    'cursor':             'vscode',
    'vscodium':           'vscode',

    # Other editors / IDEs
    'pycharm':            'editor',
    'pycharm ce':         'editor',
    'intellij idea':      'editor',
    'webstorm':           'editor',
    'xcode':              'editor',
    'sublime text':       'editor',
    'atom':               'editor',
    'android studio':     'editor',

    # Terminals
    'terminal':           'terminal',
    'iterm2':             'terminal',
    'iterm':              'terminal',
    'alacritty':          'terminal',
    'kitty':              'terminal',
    'warp':               'terminal',
    'hyper':              'terminal',
    'windows terminal':   'terminal',
    'cmd':                'terminal',
    'powershell':         'terminal',

    # File managers
    'finder':             'finder',
    'explorer':           'finder',
    'windows explorer':   'finder',

    # Office suites
    'microsoft word':     'office',
    'word':               'office',
    'microsoft excel':    'office',
    'excel':              'office',
    'microsoft powerpoint': 'office',
    'powerpoint':         'office',
    'pages':              'office',
    'numbers':            'office',
    'keynote':            'office',
    'libreoffice':        'office',

    # Notes / text editors
    'notes':              'notes',
    'textedit':           'notes',
    'notepad':            'notes',
    'notepad++':          'notes',
    'notion':             'notes',
    'obsidian':           'notes',
    'bear':               'notes',
    'typora':             'notes',
}


def get_frontmost_app() -> str:
    """
    Return the name of the currently active application (lowercase).
    Returns empty string on failure.
    """
    try:
        if _IS_MAC:
            result = subprocess.run(
                ['osascript', '-e',
                 'tell application "System Events" to get name of '
                 'first process whose frontmost is true'],
                capture_output=True, text=True, timeout=1,
            )
            return result.stdout.strip()
        else:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            # Window title includes doc name — try to extract just the app name
            title = buf.value
            # Common pattern: "Document — App Name"
            if ' - ' in title:
                title = title.split(' - ')[-1]
            elif ' — ' in title:
                title = title.split(' — ')[-1]
            return title.strip()
    except Exception:
        return ''


def get_app_category(app_name: str = None) -> str:
    """
    Return the category of the given app name (or the frontmost app if None).
    Always returns a non-empty string (falls back to 'other').
    """
    if app_name is None:
        app_name = get_frontmost_app()

    lower = app_name.lower().strip()

    # Exact match first
    if lower in _APP_CATEGORIES:
        return _APP_CATEGORIES[lower]

    # Partial match (e.g. "Google Chrome" contains "chrome")
    for key, category in _APP_CATEGORIES.items():
        if key in lower:
            return category

    return 'other'
