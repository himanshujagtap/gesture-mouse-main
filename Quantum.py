"""
Quantum Assistant — entry point.

Starts the Eel chat UI in a background thread, then runs the main
voice/text input loop.  All heavy logic lives in the quantum/ package:

    quantum/state.py        — shared mutable state
    quantum/audio_io.py     — TTS, speech recognition, reply(), wish()
    quantum/system_tools.py — system utilities, confirmation flow
    quantum/commands.py     — fuzzy_match(), respond()
"""

import time
from threading import Thread

import app
import quantum.state as state
from quantum.audio_io import wish, record_audio, reply
from quantum.commands import respond

# ---------------------------------------------------------------------------
# Start Eel UI in a background thread
# ---------------------------------------------------------------------------
t1 = Thread(target=app.ChatBot.start)
t1.start()

# Lock main thread until ChatBot has started
while not app.ChatBot.started:
    time.sleep(0.5)

# Give Eel a moment to fully initialise
time.sleep(1)

# ---------------------------------------------------------------------------
# Greet the user
# ---------------------------------------------------------------------------
wish()

# ---------------------------------------------------------------------------
# Main input loop
# ---------------------------------------------------------------------------
voice_data = None
while True:
    # Check if there's text input from GUI
    if app.ChatBot.isUserInput():
        voice_data = app.ChatBot.popUserInput()
        state.text_input_mode = True
    # Only record audio if in voice mode (text_mode is False)
    elif not app.ChatBot.getTextMode():
        voice_data = record_audio()
        state.text_input_mode = False
    else:
        # In text mode, don't record audio - just sleep and continue
        time.sleep(0.1)
        continue

    # Skip empty voice data
    if not voice_data or voice_data.strip() == '':
        continue

    # For text input, skip wake word check; for voice input, require wake word
    if state.text_input_mode or 'quantum' in voice_data or 'proton' in voice_data:
        try:
            respond(voice_data)
        except SystemExit:
            reply("Exit Successfull")
            break
        except Exception:
            print("EXCEPTION raised while closing.")
            break
