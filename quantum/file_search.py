"""
File Search for Quantum assistant.

Searches ~/Desktop, ~/Documents, ~/Downloads and a few other common
directories using fuzzy + keyword matching on filenames.

Usage
-----
    from quantum.file_search import search_files, open_path

    results = search_files("invoice march")
    # → [(score, path, is_dir), ...]  sorted best-first

    open_path("/Users/him/Documents/invoice_march.pdf")
"""

import os
import difflib
import platform
import threading

_IS_MAC = platform.system() == 'Darwin'

# Directories searched in order of priority
_SEARCH_ROOTS = [
    os.path.expanduser('~/Desktop'),
    os.path.expanduser('~/Documents'),
    os.path.expanduser('~/Downloads'),
    os.path.expanduser('~/Projects'),
    os.path.expanduser('~/Developer'),
    os.path.expanduser('~/dev'),
    os.path.expanduser('~/code'),
    os.path.expanduser('~/workspace'),
]

# Folders that are almost always irrelevant — skip them
_SKIP_DIRS = {
    '.git', '.svn', '__pycache__', 'node_modules', '.venv', 'venv',
    '.idea', '.vscode', 'Library', 'System', 'Applications',
}

MAX_DEPTH = 3       # directory recursion limit
MAX_ENTRIES = 300   # entries scanned per directory (performance guard)
MAX_RESULTS = 8     # results returned
SCORE_CUTOFF = 0.25 # minimum score to include

# Common filler words stripped from the query before matching
_STOP_WORDS = {
    'from', 'the', 'a', 'an', 'my', 'for', 'of', 'in', 'on', 'at',
    'last', 'this', 'that', 'which', 'about', 'file', 'folder',
    'document', 'month', 'year', 'week', 'day',
}


def _clean_query(raw: str) -> list:
    """Split query into meaningful words, removing stop words."""
    words = raw.lower().split()
    cleaned = [w for w in words if w not in _STOP_WORDS and len(w) > 1]
    return cleaned if cleaned else words   # fallback: use all words


def _score(query_words: list, entry_name: str) -> float:
    """
    Return a 0–1 relevance score between query words and a file/folder name.
    Prioritises: exact > starts-with > word-contains > fuzzy.
    """
    name_lower = entry_name.lower()
    base = os.path.splitext(name_lower)[0]   # strip extension for matching

    # Exact match on base name
    q_joined = ' '.join(query_words)
    if q_joined == base or q_joined == name_lower:
        return 1.0

    # All query words present in the name
    hits = sum(1 for w in query_words if w in base)
    if hits == len(query_words):
        return 0.90

    # Partial word match: score proportional to fraction matched
    if hits > 0:
        return 0.55 + 0.30 * (hits / len(query_words))

    # Starts-with first query word
    if base.startswith(query_words[0]):
        return 0.55

    # Fuzzy ratio on the first (most important) query word vs base
    ratio = difflib.SequenceMatcher(None, query_words[0], base).ratio()
    return ratio * 0.6   # down-weight fuzzy matches


def _walk(directory: str, query_words: list, results: list,
          seen: set, depth: int, stop_event: threading.Event) -> None:
    """Recursively walk directory up to MAX_DEPTH, collecting scored matches."""
    if depth > MAX_DEPTH or stop_event.is_set():
        return
    try:
        entries = list(os.scandir(directory))
    except (PermissionError, OSError):
        return

    count = 0
    for entry in entries:
        if stop_event.is_set():
            return
        if entry.name.startswith('.') or entry.name in _SKIP_DIRS:
            continue
        if count >= MAX_ENTRIES:
            break
        count += 1

        path = entry.path
        if path in seen:
            continue
        seen.add(path)

        score = _score(query_words, entry.name)
        if score >= SCORE_CUTOFF:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            results.append((score, path, is_dir))

        if entry.is_dir(follow_symlinks=False) and depth < MAX_DEPTH:
            _walk(path, query_words, results, seen, depth + 1, stop_event)


def search_files(query: str, timeout: float = 4.0) -> list:
    """
    Search common directories for files/folders matching *query*.

    Returns a list of (score, path, is_dir) tuples, sorted best-first,
    capped at MAX_RESULTS. Stops after *timeout* seconds.
    """
    query_words = _clean_query(query)
    results: list = []
    seen: set = set()
    stop_event = threading.Event()

    roots = [d for d in _SEARCH_ROOTS if os.path.isdir(d)]

    def _run():
        for root in roots:
            if stop_event.is_set():
                break
            _walk(root, query_words, results, seen, depth=0,
                  stop_event=stop_event)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    stop_event.set()   # signal worker to stop if still running

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:MAX_RESULTS]


def open_path(path: str) -> None:
    """Open a file or folder in the default system application / Finder."""
    if _IS_MAC:
        os.system(f'open "{path}"')
    else:
        os.startfile(path)
