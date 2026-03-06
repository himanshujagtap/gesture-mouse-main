"""
Audio I/O for Quantum assistant.

Handles:
- Text-to-speech (pyttsx3 with macOS 'say' fallback)
- Speech recognition (Google Speech via SpeechRecognition)
- reply() and wish() output helpers
"""

import os
import platform
import datetime

import speech_recognition as sr
import pyttsx3

import quantum.state as state

IS_MAC = platform.system() == 'Darwin'

# ---------------------------------------------------------------------------
# TTS initialisation
# ---------------------------------------------------------------------------
engine = None
TTS_AVAILABLE = False

try:
    if IS_MAC:
        try:
            engine = pyttsx3.init()
            TTS_AVAILABLE = True
        except Exception as e:
            print(f"pyttsx3 not available on macOS: {e}")
            print("Quantum will use macOS 'say' command for speech instead")
    else:
        engine = pyttsx3.init('sapi5')
        TTS_AVAILABLE = True

    if TTS_AVAILABLE and engine:
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
except Exception as e:
    print(f"Text-to-speech initialization failed: {e}")
    print("Quantum will run without voice feedback")

# ---------------------------------------------------------------------------
# Speech recogniser + microphone calibration
# ---------------------------------------------------------------------------
r = sr.Recognizer()

with sr.Microphone() as _source:
    r.energy_threshold = 500
    r.dynamic_energy_threshold = False


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def reply(audio):
    """Send a response to the UI and speak it aloud."""
    import app  # deferred to avoid import-time circular dependency
    app.ChatBot.addAppMsg(audio)
    print(audio)

    if TTS_AVAILABLE and engine:
        try:
            engine.say(audio)
            engine.runAndWait()
        except Exception:
            if IS_MAC:
                os.system(f'say "{audio}"')
    elif IS_MAC:
        os.system(f'say "{audio}"')


def wish():
    """Greet the user based on the current time of day."""
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        reply("Good Morning!")
    elif 12 <= hour < 18:
        reply("Good Afternoon!")
    else:
        reply("Good Evening!")
    reply(f"I am {state.assistant_name}, how may I help you?")


def record_audio():
    """Listen to the microphone and return the recognised text (lowercase)."""
    with sr.Microphone() as source:
        r.pause_threshold = 0.8
        voice_data = ''
        audio = r.listen(source, phrase_time_limit=5)
        try:
            voice_data = r.recognize_google(audio)
        except sr.RequestError:
            reply('Sorry my Service is down. Plz check your Internet connection')
        except sr.UnknownValueError:
            print('cant recognize')
        return voice_data.lower()
