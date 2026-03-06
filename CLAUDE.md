# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Two-mode desktop assistant:
1. **Gesture mouse control** — hand tracking via MediaPipe/OpenCV controls the cursor, clicks, scroll, volume, and brightness.
2. **Quantum voice/text assistant** — Eel web UI + speech recognition + LLM integration for voice/text command dispatch.

## Setup and Running

### Environment Requirements
- Python 3.9+ (MediaPipe requires modern typing features)
- Windows: `requirements.txt` (includes `pycaw`, `comtypes`, `screen-brightness-control`)
- macOS: `requirements-mac.txt` (excludes Windows-only audio/brightness libs)

### Installation

```bash
# Conda (recommended)
conda create -n gest39 python=3.10 -y
conda activate gest39
pip install --upgrade pip
pip install -r requirements.txt          # Windows
pip install -r requirements-mac.txt     # macOS

# venv alternative (macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-mac.txt
```

### LLM Configuration (optional)

Copy `.env.example` to `.env` and set your API keys:
```
LLM_PROVIDER=gemini          # or groq / ollama
GEMINI_API_KEY=...
GROQ_API_KEY=...             # optional fallback
```
Without a key, `llm_helper.py` falls back to curated static responses. Ollama requires no key but needs `ollama serve` running locally.

### Running

```bash
# Full assistant (UI + voice/text + commands; can also launch gesture mode via command)
python Quantum.py

# Gesture controller only (standalone)
python Gesture_Controller.py
python Gesture_Controller.py --camera 1 --verbose
python Gesture_Controller.py --list-cameras
```

Exit the gesture window: ESC, Enter, or Q.

The Eel UI opens in Brave browser by default (`mode='brave'` in `app.py`). If Brave is not installed, change `mode` to `'chrome'` or `'default'`.

## Architecture

### File Roles

#### Gesture pipeline (modular)

| File | Role |
|---|---|
| `Gesture_Controller.py` | Entry point for gesture mode; imports from the modules below; contains only `GestureController` (camera loop + hand classification) |
| `gesture_enums.py` | `Gest` (IntEnum) and `HLabel` (IntEnum) definitions |
| `hand_recognizer.py` | `HandRecog` — converts MediaPipe landmarks to gesture enums |
| `controller.py` | `Controller` — executes system actions; macOS/Windows graceful fallback via `WINDOWS_FEATURES_AVAILABLE` |
| `utils.py` | `list_cameras()` helper |

#### Quantum assistant (modular)

| File | Role |
|---|---|
| `Quantum.py` | Entry point (~70 lines): starts Eel thread, greets user, runs main input loop |
| `quantum/state.py` | All shared mutable state (`is_awake`, `assistant_name`, `file_exp_status`, `pending_confirmation`, etc.) |
| `quantum/audio_io.py` | TTS engine init, `reply()`, `wish()`, `record_audio()` |
| `quantum/system_tools.py` | `get_startup_apps_status()`, `run_network_speed_test()`, `queue_confirmation()`, `execute_pending_confirmation()` |
| `quantum/commands.py` | `fuzzy_match()` + `respond()` — the full 50+ command dispatcher |
| `app.py` | Eel bridge — `getUserInput`, `getCommandSuggestions`, `setTextMode`; manages chatbot message queue |
| `llm_helper.py` | LLM abstraction (Gemini `gemini-2.5-flash`, Groq `llama-3.3-70b-versatile`, Ollama; cascading fallback to static responses) |
| `web/` | Frontend HTML/JS/CSS for the chat UI |

### Dependency Graph

```
Quantum.py
  ├── quantum/state.py
  ├── quantum/audio_io.py     → quantum/state.py, app
  ├── quantum/commands.py     → quantum/state.py, quantum/audio_io.py,
  │                              quantum/system_tools.py, Gesture_Controller,
  │                              app, llm_helper
  └── quantum/system_tools.py → quantum/state.py, quantum/audio_io.py

Gesture_Controller.py
  ├── gesture_enums.py
  ├── hand_recognizer.py  → gesture_enums.py
  ├── controller.py       → gesture_enums.py
  └── utils.py
```

### Shared State Pattern

All modules that need mutable assistant state do:
```python
import quantum.state as state
state.is_awake = True       # write
if state.file_exp_status:   # read
```
This avoids `global` declarations while keeping a single source of truth.

### Gesture Pipeline

```
Camera Frame → MediaPipe Hands → GestureController.classify_hands()
                                        ↓
                              HandRecog (major + minor)
                              set_finger_state() → get_gesture()
                                        ↓
                              Controller.handle_controls()
                                        ↓
                    System Actions (mouse, click, scroll, volume, brightness)
```

### Gesture Mappings

**Primary (any time):**
- V gesture → cursor movement mode (`Controller.flag = True`)
- Fist → click-and-drag
- Pinch dominant hand → volume (y-axis) / brightness (x-axis)
- Pinch non-dominant hand → scroll vertical (y) / horizontal (x)

**Secondary (require V gesture first):**
- Middle finger up → left click (clears flag)
- Index finger up → right click (clears flag)
- Two fingers closed → double click (clears flag)

### Adding a New Quantum Command

1. Add the command string to `getCommandSuggestions` in `app.py`
2. Add an `elif` branch in `respond()` in `quantum/commands.py`
3. If it needs risky-action confirmation, call `queue_confirmation('action_name')` and add a handler in `execute_pending_confirmation()` in `quantum/system_tools.py`
4. Document it in `cmds.md`

## Common Issues

- **Gesture jitter**: increase frame_count threshold in `HandRecog.get_gesture()` in `hand_recognizer.py` (default: 4) or adjust dampening ratios in `Controller.get_position()` in `controller.py`
- **Camera not found**: run `--list-cameras`; on Windows, DirectShow backend (`CAP_DSHOW`) is used automatically
- **MediaPipe broken**: `pip install mediapipe==0.10.5 protobuf -U`
- **pycaw / screen-brightness-control**: Windows-only; `controller.py` skips them gracefully via `WINDOWS_FEATURES_AVAILABLE` flag
- **Brave not installed**: change `mode='brave'` to `mode='chrome'` or `mode='default'` in `app.py::ChatBot.start()`
- **Gemini 404**: verify API key; the code uses `v1` API endpoint with `gemini-2.5-flash`

## Modifying Behavior

- **Cursor speed**: dampening ratios in `Controller.get_position()` in `controller.py`
- **Pinch sensitivity**: `Controller.pinch_threshold` in `controller.py` (default: 0.3)
- **Gesture stability**: frame_count check in `HandRecog.get_gesture()` in `hand_recognizer.py` (default: `> 4`)
- **Assistant name**: `assistant_name = "Quantum"` in `quantum/state.py`
- **LLM model**: `GROQ_MODEL`, `GEMINI_MODEL`, `OLLAMA_MODEL` constants in `llm_helper.py`
- **MediaPipe confidence**: `min_detection_confidence` / `min_tracking_confidence` in `GestureController.start()`
- **Adding gestures**: add to `Gest` in `gesture_enums.py` → detect in `hand_recognizer.py` → handle in `controller.py`
