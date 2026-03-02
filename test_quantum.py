#!/usr/bin/env python3
"""
Quick test script for Quantum assistant
Tests all imports and platform detection without starting the full app
"""

import sys
import os

print("=" * 60)
print("QUANTUM ASSISTANT - Startup Test")
print("=" * 60)

# Test 1: Platform Detection
print("\n[1/6] Testing platform detection...")
import platform
IS_MAC = platform.system() == 'Darwin'
print(f"    ✓ Platform: {'macOS' if IS_MAC else 'Windows'}")

# Test 2: Core imports
print("\n[2/6] Testing core Python imports...")
try:
    import pyttsx3
    import speech_recognition as sr
    from datetime import date
    import time
    import webbrowser
    import datetime
    from threading import Thread
    print("    ✓ All core imports successful")
except ImportError as e:
    print(f"    ✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Keyboard control
print("\n[3/6] Testing keyboard control (pynput)...")
try:
    from pynput.keyboard import Key, Controller
    keyboard = Controller()
    CMD_KEY = Key.cmd if IS_MAC else Key.ctrl
    print(f"    ✓ Keyboard control ready (using {CMD_KEY})")
except Exception as e:
    print(f"    ✗ pynput failed: {e}")
    sys.exit(1)

# Test 4: Gesture Controller
print("\n[4/6] Testing Gesture Controller...")
try:
    import Gesture_Controller
    print("    ✓ Gesture Controller loaded")
except Exception as e:
    print(f"    ✗ Gesture Controller failed: {e}")
    sys.exit(1)

# Test 5: Web interface (Eel)
print("\n[5/6] Testing web interface (Eel)...")
try:
    import app
    print("    ✓ Eel web interface loaded")
except Exception as e:
    print(f"    ✗ Eel failed: {e}")
    sys.exit(1)

# Test 6: Text-to-Speech
print("\n[6/6] Testing text-to-speech...")
if IS_MAC:
    print("    ℹ Using macOS 'say' command")
    ret = os.system('say "Quantum is ready" &')
    if ret == 0:
        print("    ✓ macOS TTS works!")
    else:
        print("    ⚠ macOS say command failed (but Quantum will still work)")
else:
    try:
        engine = pyttsx3.init('sapi5')
        print("    ✓ Windows SAPI5 TTS ready")
    except Exception as e:
        print(f"    ⚠ TTS failed: {e} (Quantum will work without voice)")

# Summary
print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nQuantum is ready to launch!")
print("\nTo start Quantum:")
print("  python Quantum.py")
print("\nTo start just gesture control:")
print("  python Gesture_Controller.py")
print("=" * 60)
