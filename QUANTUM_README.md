# 🚀 Quantum - Cross-Platform Voice & Gesture Assistant

**Quantum** is your intelligent voice-controlled assistant with hand gesture recognition.

## Platform Support

- ✅ **Windows**: Full support (all features)
- ✅ **macOS**: Full support (uses native `say` command for TTS)

## Features

### Voice Commands
Say "Quantum" or "Proton" followed by:

- **"hello"** - Greet Quantum
- **"what is your name"** - Quantum introduces itself
- **"time"** - Get current time
- **"date"** - Get current date
- **"search [query]"** - Google search
- **"location [place]"** - Google Maps search
- **"launch gesture recognition"** - Start hand gesture control
- **"stop gesture recognition"** - Stop hand gesture control
- **"copy"** - Copy selected text (Cmd+C on Mac, Ctrl+C on Windows)
- **"paste"** - Paste clipboard (Cmd+V on Mac, Ctrl+V on Windows)
- **"list"** - List files in home directory (Mac) or C:// (Windows)
- **"bye"** - Put Quantum to sleep
- **"exit"** or **"terminate"** - Quit Quantum

### Gesture Control
Once gesture recognition is launched:
- **V gesture** (peace sign) - Move cursor
- **Fist** - Click and drag
- **Pinch (minor hand)** - Scroll
- **Pinch (major hand)** - Volume/brightness (Windows only)
- **Middle finger up** - Left click
- **Index finger up** - Right click
- **Two fingers closed** - Double click

## Setup & Running

### macOS
```bash
cd "/Users/himanshu/Desktop/final project/gesture-mouse"
source .venv/bin/activate
python Quantum.py
```

### Windows
```bash
cd "path/to/gesture-mouse"
.venv\Scripts\activate
python Quantum.py
```

## Permissions Required (macOS)

1. **Microphone** - For voice commands
2. **Camera** - For gesture recognition
3. **Accessibility** - For keyboard/mouse control

Grant these in: **System Settings → Privacy & Security**

## How It Works

1. **Speech Recognition**: Listens for "Quantum" or "Proton" wake word
2. **Text-to-Speech**:
   - macOS: Uses built-in `say` command
   - Windows: Uses SAPI5 speech engine
3. **Gesture Recognition**: MediaPipe hand tracking
4. **Web Interface**: Eel-based chat interface

## Troubleshooting

### Camera not detected
```bash
python Gesture_Controller.py --list-cameras
```

### Microphone not working
Check System Settings → Privacy → Microphone

### Speech not working on macOS
Test: `say "Quantum is ready"` in Terminal

## Code Compatibility

✅ **Single codebase works on both Windows and macOS**
- Automatic platform detection
- Platform-specific features handled gracefully
- Cross-platform keyboard shortcuts (Cmd on Mac, Ctrl on Windows)

---

Created with ❤️ by Himanshu | Powered by MediaPipe, Eel, and pyttsx3
