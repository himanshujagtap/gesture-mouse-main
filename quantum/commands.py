"""
Command dispatcher for Quantum assistant.

Contains:
- fuzzy_match()  — corrects typos in the command portion of user input
- respond()      — the main command router (50+ commands)
"""

import os
import sys
import time
import webbrowser
import datetime
import pyautogui
import wikipedia
from os import listdir
from os.path import isfile, join
from threading import Thread
from difflib import get_close_matches
from pynput.keyboard import Key, Controller as KeyboardController

import Gesture_Controller
import app

import quantum.state as state
from quantum.audio_io import IS_MAC, reply, record_audio
from quantum.system_tools import (
    get_startup_apps_status,
    run_network_speed_test,
    queue_confirmation,
    execute_pending_confirmation,
)

# ---------------------------------------------------------------------------
# Keyboard controller (cross-platform)
# ---------------------------------------------------------------------------
keyboard = KeyboardController()
CMD_KEY = Key.cmd if IS_MAC else Key.ctrl

# ---------------------------------------------------------------------------
# LLM (optional)
# ---------------------------------------------------------------------------
try:
    import llm_helper
    LLM_AVAILABLE = True
    print("[LLM] Helper loaded successfully!")
except Exception as e:
    LLM_AVAILABLE = False
    print(f"[LLM] Not available: {e}. Using fallback responses.")


# ---------------------------------------------------------------------------
# Fuzzy command matching
# ---------------------------------------------------------------------------

def fuzzy_match(input_text):
    """Apply fuzzy matching to correct common typos in commands ONLY, not parameters."""
    command_keywords = [
        'hello', 'time', 'date', 'search', 'location', 'launch gesture recognition',
        'stop gesture recognition', 'copy', 'paste', 'change name to', 'rename to',
        'call yourself', 'screenshot', 'scroll up', 'scroll down', 'volume up',
        'volume down', 'mute', 'unmute', 'wikipedia', 'type', 'minimize', 'maximize',
        'lock', 'open app', 'close app', 'open', 'close', 'weather', 'play music',
        'pause music', 'next song', 'previous song', 'brightness up', 'brightness down',
        'new tab', 'close tab', 'close window', 'incognito', 'refresh', 'reload',
        'joke', 'flip a coin', 'roll a dice', 'set timer', 'battery', 'cpu',
        'system info', 'list', 'back', 'sleep', 'go to sleep', 'exit', 'terminate',
        'wake up', 'what is your name', 'who are you', 'tell me a joke',
        'next track', 'previous track', 'coin flip', 'roll dice',
        'calculate', 'convert', 'youtube search', 'youtube', 'github search', 'github',
        'stackoverflow', 'stack overflow', 'translate', 'define', 'ip address', 'show ip',
        'wifi name', 'wifi', 'motivational quote', 'motivate me', 'inspire me',
        'random fact', 'fun fact', 'tell me a fact', 'magic 8 ball', 'magic eight ball',
        'compliment me', 'say something nice', 'insult me', 'roast me', 'help', 'commands',
        'what can you do', 'sing', 'dance', 'tell me about yourself', 'about yourself',
        'what do you think about ai', 'thoughts on ai', 'good job', 'well done',
        'great job', 'thank you', 'are you alive', 'are you real', 'are you conscious',
        'cleanup desktop', 'empty recycle bin', 'empty trash', 'startup apps status',
        'network speed test', 'confirm', 'cancel'
    ]

    words = input_text.split()
    if not words:
        return input_text

    # Try to match first N words against multi-word commands (longest first)
    sorted_commands = sorted(command_keywords, key=len, reverse=True)
    for cmd in sorted_commands:
        cmd_words = cmd.split()
        if len(cmd_words) > 1 and len(words) >= len(cmd_words):
            first_n_words = ' '.join(words[:len(cmd_words)])
            matches = get_close_matches(first_n_words, [cmd], n=1, cutoff=0.75)
            if matches:
                rest_of_input = ' '.join(words[len(cmd_words):])
                return f"{matches[0]} {rest_of_input}".strip()

    # Fall back to fuzzy-matching the first word only
    first_word = words[0]
    rest_of_input = ' '.join(words[1:])
    single_word_commands = [kw for kw in command_keywords if ' ' not in kw]
    matches = get_close_matches(first_word, single_word_commands, n=1, cutoff=0.75)
    if matches:
        return f"{matches[0]} {rest_of_input}".strip()

    return input_text


# ---------------------------------------------------------------------------
# Main command dispatcher
# ---------------------------------------------------------------------------

def respond(voice_data):
    """Route voice/text input to the appropriate command handler."""
    print(f"[DEBUG] Received: {voice_data}")

    # Handle blank/empty input
    if not voice_data or voice_data.strip() == '':
        reply(state.blank_input_responses[state.blank_response_index])
        state.blank_response_index = (state.blank_response_index + 1) % len(state.blank_input_responses)
        return

    # Confirmation flow for risky commands
    normalized_input = voice_data.strip().lower()
    if normalized_input in ['confirm', 'yes confirm']:
        execute_pending_confirmation()
        return
    elif normalized_input in ['cancel', 'abort', 'nevermind', 'never mind'] and state.pending_confirmation:
        state.pending_confirmation = None
        reply('Cancelled. No action was taken.')
        return

    # Strip assistant name prefix (case-insensitive)
    voice_data_lower = voice_data.lower()
    for name in ['quantum', 'proton', 'jarvis', state.assistant_name.lower()]:
        voice_data_lower = voice_data_lower.replace(name, '')
    voice_data = voice_data_lower.strip()

    # Apply fuzzy matching to correct typos
    voice_data = fuzzy_match(voice_data)
    print(f"[DEBUG] After fuzzy match: {voice_data}")

    app.eel.addUserMsg(voice_data)()

    # -----------------------------------------------------------------------
    # SLEEP / WAKE
    # -----------------------------------------------------------------------
    if state.is_awake == False:
        if 'wake up' in voice_data or 'wakeup' in voice_data or 'wake' in voice_data:
            state.is_awake = True
            reply("I'm awake now!")
            from quantum.audio_io import wish
            wish()
        return

    # -----------------------------------------------------------------------
    # BASIC COMMANDS
    # -----------------------------------------------------------------------
    elif 'hello' in voice_data:
        from quantum.audio_io import wish
        wish()

    elif 'what is your name' in voice_data or 'who are you' in voice_data:
        reply(f'My name is {state.assistant_name}!')

    elif 'date' in voice_data:
        reply(datetime.date.today().strftime("%B %d, %Y"))

    # TIMER (before 'time' to avoid conflict)
    elif 'timer' in voice_data or 'set timer' in voice_data:
        try:
            duration = 1
            for word in voice_data.split():
                if word.isdigit():
                    duration = int(word)
                    break
            reply(f"Starting {duration} minute timer")

            def timer_alert(minutes):
                time.sleep(minutes * 60)
                if IS_MAC:
                    os.system(f'say "Timer of {minutes} minutes is complete"')
                    os.system('afplay /System/Library/Sounds/Glass.aiff')
                else:
                    reply(f"Timer of {minutes} minutes is complete")

            timer_thread = Thread(target=timer_alert, args=(duration,))
            timer_thread.daemon = True
            timer_thread.start()
        except Exception:
            reply("I couldn't set the timer. Try 'set timer 5'")

    elif 'time' in voice_data:
        reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])

    elif 'search' in voice_data and 'youtube' not in voice_data and 'github' not in voice_data and 'stackoverflow' not in voice_data:
        query = voice_data.split('search')[1]
        reply('Searching for ' + query)
        url = 'https://google.com/search?q=' + query
        try:
            webbrowser.get().open(url)
            reply('This is what I found Sir')
        except Exception:
            reply('Please check your Internet')

    elif 'location' in voice_data:
        reply('Which place are you looking for ?')
        temp_audio = record_audio()
        app.eel.addUserMsg(temp_audio)()
        reply('Locating...')
        url = 'https://google.nl/maps/place/' + temp_audio + '/&amp;'
        try:
            webbrowser.get().open(url)
            reply('This is what I found Sir')
        except Exception:
            reply('Please check your Internet')

    elif ('bye' in voice_data) or ('by' in voice_data) or ('sleep' in voice_data) or ('go to sleep' in voice_data):
        reply(f"Good bye! Going to sleep mode. Say '{state.assistant_name} wake up' to wake me again.")
        state.is_awake = False

    elif ('exit' in voice_data) or ('terminate' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
        app.ChatBot.close()
        sys.exit()

    # -----------------------------------------------------------------------
    # GESTURE RECOGNITION
    # -----------------------------------------------------------------------
    elif 'launch gesture recognition' in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            reply('Gesture recognition is already active')
        else:
            gc = Gesture_Controller.GestureController()
            t = Thread(target=gc.start)
            t.start()
            reply('Launched Successfully')

    elif ('stop gesture recognition' in voice_data) or ('top gesture recognition' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            reply('Gesture recognition stopped')
        else:
            reply('Gesture recognition is already inactive')

    # -----------------------------------------------------------------------
    # CLIPBOARD
    # -----------------------------------------------------------------------
    elif 'copy' in voice_data:
        with keyboard.pressed(CMD_KEY):
            keyboard.press('c')
            keyboard.release('c')
        reply('Copied')

    elif 'page' in voice_data or 'pest' in voice_data or 'paste' in voice_data:
        with keyboard.pressed(CMD_KEY):
            keyboard.press('v')
            keyboard.release('v')
        reply('Pasted')

    # -----------------------------------------------------------------------
    # NAME CHANGE
    # -----------------------------------------------------------------------
    elif 'change name to' in voice_data or 'rename to' in voice_data or 'call yourself' in voice_data:
        if 'change name to' in voice_data:
            new_name = voice_data.split('change name to')[1].strip()
        elif 'rename to' in voice_data:
            new_name = voice_data.split('rename to')[1].strip()
        else:
            new_name = voice_data.split('call yourself')[1].strip()

        if new_name:
            state.assistant_name = new_name.title()
            reply(f"Okay! From now on, call me {state.assistant_name}!")
            try:
                app.eel.updateAssistantName(state.assistant_name)()
            except Exception:
                pass
        else:
            reply("What should I call myself?")

    # -----------------------------------------------------------------------
    # SYSTEM CONTROLS
    # -----------------------------------------------------------------------
    elif 'screenshot' in voice_data or 'take screenshot' in voice_data:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        screenshot_path = os.path.join(os.path.expanduser('~'), 'Desktop', filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        reply(f"Screenshot saved to Desktop as {filename}")

    elif 'scroll up' in voice_data:
        reply("Scrolling up")
        for _ in range(15):
            pyautogui.scroll(20)
            time.sleep(0.01)

    elif 'scroll down' in voice_data:
        reply("Scrolling down")
        for _ in range(15):
            pyautogui.scroll(-20)
            time.sleep(0.01)

    elif 'volume up' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 10)'")
        else:
            pyautogui.press('volumeup')
        reply("Volume increased")

    elif 'volume down' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 10)'")
        else:
            pyautogui.press('volumedown')
        reply("Volume decreased")

    elif 'mute' in voice_data or 'unmute' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'set volume output muted not (output muted of (get volume settings))'")
        else:
            pyautogui.press('volumemute')
        reply("Volume toggled")

    elif 'minimize' in voice_data or 'minimise' in voice_data:
        if IS_MAC:
            pyautogui.hotkey('command', 'm')
        else:
            pyautogui.hotkey('win', 'd')
        reply("Minimized")

    elif 'maximize' in voice_data or 'maximise' in voice_data:
        if IS_MAC:
            pyautogui.hotkey('ctrl', 'command', 'f')
        else:
            pyautogui.hotkey('win', 'up')
        reply("Maximized")

    elif 'lock' in voice_data or 'lock screen' in voice_data:
        if IS_MAC:
            os.system("pmset displaysleepnow")
        else:
            os.system('rundll32.exe user32.dll,LockWorkStation')
        reply("Locking screen")

    # -----------------------------------------------------------------------
    # APP CONTROL
    # -----------------------------------------------------------------------
    elif 'open app' in voice_data or ('open' in voice_data and not state.file_exp_status):
        app_name = voice_data.replace('open app', '').replace('open', '').strip()
        if app_name:
            try:
                if IS_MAC:
                    mac_apps = {
                        'calculator': 'Calculator', 'notes': 'Notes', 'safari': 'Safari',
                        'chrome': 'Google Chrome', 'firefox': 'Firefox', 'finder': 'Finder',
                        'mail': 'Mail', 'calendar': 'Calendar', 'music': 'Music',
                        'photos': 'Photos', 'messages': 'Messages', 'terminal': 'Terminal',
                        'vscode': 'Visual Studio Code', 'slack': 'Slack', 'spotify': 'Spotify',
                        'discord': 'Discord', 'zoom': 'zoom.us'
                    }
                    app_to_open = mac_apps.get(app_name.lower(), app_name.title())
                    check_cmd = f'mdfind "kMDItemKind == Application && kMDItemFSName == \'{app_to_open}.app\'" 2>/dev/null'
                    result = os.popen(check_cmd).read().strip()
                    if result:
                        os.system(f'open -a "{app_to_open}" 2>/dev/null')
                        reply(f"Opening {app_to_open}")
                    else:
                        reply(f"Sorry, {app_name} is not installed on your system. Please install it first.")
                else:
                    win_apps = {
                        'notepad': 'notepad.exe', 'calculator': 'calc.exe',
                        'paint': 'mspaint.exe', 'wordpad': 'write.exe',
                        'explorer': 'explorer.exe', 'cmd': 'cmd.exe',
                        'command prompt': 'cmd.exe', 'chrome': 'chrome.exe',
                        'firefox': 'firefox.exe'
                    }
                    app_to_open = win_apps.get(app_name.lower(), app_name + '.exe')
                    try:
                        os.startfile(app_to_open)
                        reply(f"Opening {app_name}")
                    except FileNotFoundError:
                        reply(f"Sorry, {app_name} is not installed on your system. Please install it first.")
            except Exception:
                reply(f"Sorry, I couldn't open {app_name}. It might not be installed.")
        else:
            reply("Which application should I open?")

    elif 'close app' in voice_data or ('close' in voice_data and not state.file_exp_status):
        app_name = voice_data.replace('close app', '').replace('close', '').strip()
        if 'tab' in voice_data or 'window' in voice_data:
            pass  # handled by browser controls below
        elif app_name:
            try:
                if IS_MAC:
                    mac_apps = {
                        'calculator': 'Calculator', 'notes': 'Notes', 'safari': 'Safari',
                        'chrome': 'Google Chrome', 'firefox': 'Firefox', 'finder': 'Finder',
                        'mail': 'Mail', 'terminal': 'Terminal'
                    }
                    app_to_close = mac_apps.get(app_name.lower(), app_name.title())
                    os.system(f'osascript -e \'quit app "{app_to_close}"\'')
                    reply(f"Closing {app_to_close}")
                else:
                    os.system(f'taskkill /F /IM {app_name}.exe 2>nul')
                    reply(f"Closing {app_name}")
            except Exception:
                reply(f"Couldn't close {app_name}")
        else:
            reply("Which application should I close?")

    # -----------------------------------------------------------------------
    # WEATHER
    # -----------------------------------------------------------------------
    elif 'weather' in voice_data:
        try:
            import urllib.request
            location = voice_data.replace('weather', '').strip() or 'auto'
            url = f"http://wttr.in/{location}?format=3"
            with urllib.request.urlopen(url, timeout=5) as response:
                weather = response.read().decode('utf-8')
            reply(f"Current weather: {weather}")
        except Exception:
            reply("Sorry, I couldn't fetch the weather. Check your internet connection.")

    # -----------------------------------------------------------------------
    # MUSIC
    # -----------------------------------------------------------------------
    elif 'play music' in voice_data or 'pause music' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'tell application \"Music\" to playpause'")
        else:
            pyautogui.press('playpause')
        reply("Music toggled")

    elif 'next song' in voice_data or 'next track' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'tell application \"Music\" to next track'")
        else:
            pyautogui.press('nexttrack')
        reply("Next track")

    elif 'previous song' in voice_data or 'previous track' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'tell application \"Music\" to previous track'")
        else:
            pyautogui.press('prevtrack')
        reply("Previous track")

    # -----------------------------------------------------------------------
    # BRIGHTNESS
    # -----------------------------------------------------------------------
    elif 'brightness up' in voice_data or 'increase brightness' in voice_data:
        if IS_MAC:
            for _ in range(5):
                os.system("osascript -e 'tell application \"System Events\" to key code 144'")
        else:
            pyautogui.press('brightnessup')
        reply("Brightness increased")

    elif 'brightness down' in voice_data or 'decrease brightness' in voice_data:
        if IS_MAC:
            for _ in range(5):
                os.system("osascript -e 'tell application \"System Events\" to key code 145'")
        else:
            pyautogui.press('brightnessdown')
        reply("Brightness decreased")

    # -----------------------------------------------------------------------
    # BROWSER CONTROLS
    # -----------------------------------------------------------------------
    elif 'new tab' in voice_data:
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 't')
        reply("Opening new tab")

    elif 'close tab' in voice_data:
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'w')
        reply("Closing tab")

    elif 'incognito' in voice_data or 'private' in voice_data:
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'shift', 'n')
        reply("Opening incognito window")

    elif 'refresh' in voice_data or 'reload' in voice_data:
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'r')
        reply("Refreshing page")

    # -----------------------------------------------------------------------
    # POWER USER SYSTEM UTILITIES
    # -----------------------------------------------------------------------
    elif 'cleanup desktop' in voice_data:
        queue_confirmation('cleanup_desktop')

    elif 'empty recycle bin' in voice_data or 'empty trash' in voice_data:
        queue_confirmation('empty_recycle_bin')

    elif 'startup apps status' in voice_data:
        apps, err = get_startup_apps_status()
        if err:
            reply(err)
        elif apps:
            preview = ', '.join(apps[:12])
            extra = len(apps) - 12
            if extra > 0:
                reply(f"Found {len(apps)} startup app entries. First entries: {preview} ... and {extra} more.")
            else:
                reply(f"Found {len(apps)} startup app entries: {preview}")
        else:
            reply('No startup app entries found.')

    elif 'network speed test' in voice_data:
        try:
            reply('Running network speed test. This may take a few seconds...')
            latency_ms, speed_mbps, downloaded = run_network_speed_test()
            reply(f"Network check complete. <br> Latency: {latency_ms:.0f} ms. <br> Approx download speed: {speed_mbps:.2f} Mbps (sampled {downloaded // 1024} KB).")
        except Exception as e:
            reply(f"Couldn't complete speed test: {e}")

    # -----------------------------------------------------------------------
    # WIKIPEDIA
    # -----------------------------------------------------------------------
    elif 'wikipedia' in voice_data:
        topic = voice_data.replace('wikipedia', '').strip()
        if topic:
            try:
                reply(f"Searching Wikipedia for {topic}")
                summary = wikipedia.summary(topic, sentences=2)
                reply(summary)
            except wikipedia.exceptions.DisambiguationError as e:
                reply(f"Multiple results found. Please be more specific: {', '.join(e.options[:3])}")
            except wikipedia.exceptions.PageError:
                reply(f"Sorry, I couldn't find anything about {topic} on Wikipedia")
            except Exception:
                reply("Wikipedia search failed. Please check your internet connection")
        else:
            reply("What should I search on Wikipedia?")

    # -----------------------------------------------------------------------
    # TEXT INPUT
    # -----------------------------------------------------------------------
    elif 'type' in voice_data:
        text_to_type = voice_data.replace('type', '').strip()
        if text_to_type:
            time.sleep(2)
            pyautogui.typewrite(text_to_type, interval=0.1)
            reply(f"Typed: {text_to_type}")
        else:
            reply("What should I type?")

    # -----------------------------------------------------------------------
    # WEB SEARCHES
    # -----------------------------------------------------------------------
    elif 'youtube search' in voice_data or 'youtube' in voice_data:
        query = voice_data.replace('youtube search', '').replace('youtube', '').strip()
        if query:
            url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching YouTube for {query}")
        else:
            reply("What should I search on YouTube?")

    elif 'github search' in voice_data or 'github' in voice_data:
        query = voice_data.replace('github search', '').replace('github', '').replace('search', '').strip()
        if query:
            url = f'https://github.com/search?q={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching GitHub for {query}")
        else:
            reply("What should I search on GitHub?")

    elif 'stackoverflow' in voice_data or 'stack overflow' in voice_data:
        query = voice_data.replace('stackoverflow', '').replace('stack overflow', '').replace('search', '').strip()
        if query:
            url = f'https://stackoverflow.com/search?q={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching Stack Overflow for {query}")
        else:
            reply("What should I search on Stack Overflow?")

    # -----------------------------------------------------------------------
    # TRANSLATION
    # -----------------------------------------------------------------------
    elif 'translate' in voice_data:
        try:
            parts = voice_data.split(' to ')
            if len(parts) == 2:
                text = parts[0].replace('translate', '').strip()
                target_lang = parts[1].strip()
                if text:
                    try:
                        from googletrans import Translator
                        translator = Translator()
                        lang_codes = {
                            'spanish': 'es', 'french': 'fr', 'german': 'de', 'italian': 'it',
                            'portuguese': 'pt', 'russian': 'ru', 'japanese': 'ja', 'chinese': 'zh',
                            'hindi': 'hi', 'arabic': 'ar', 'korean': 'ko', 'dutch': 'nl',
                            'swedish': 'sv', 'polish': 'pl', 'turkish': 'tr', 'greek': 'el'
                        }
                        lang_code = lang_codes.get(target_lang.lower(), target_lang[:2])
                        result = translator.translate(text, dest=lang_code)
                        reply(f"'{text}' in {target_lang} is: {result.text}")
                    except ImportError:
                        reply("Translation library not installed. Install with: pip install googletrans==4.0.0-rc1")
                    except Exception as e:
                        print(f"Translation error: {e}")
                        reply("Translation failed. Try again or check your internet connection.")
                else:
                    reply("What should I translate?")
            else:
                reply("Use format: translate hello to spanish")
        except Exception:
            reply("Translation format: translate hello to spanish")

    # -----------------------------------------------------------------------
    # DICTIONARY
    # -----------------------------------------------------------------------
    elif 'define' in voice_data:
        word = voice_data.replace('define', '').strip()
        if word:
            try:
                import urllib.request
                import json
                import urllib.error
                api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                with urllib.request.urlopen(api_url, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                if data:
                    meanings = data[0].get('meanings', [])
                    if meanings:
                        first_meaning = meanings[0]
                        part_of_speech = first_meaning.get('partOfSpeech', '')
                        definitions = first_meaning.get('definitions', [])
                        if definitions:
                            definition_text = definitions[0].get('definition', '')
                            example = definitions[0].get('example', '')
                            response_text = f"{word}"
                            if part_of_speech:
                                response_text += f" ({part_of_speech})"
                            response_text += f": {definition_text}"
                            if example:
                                response_text += f" <br>Example: {example}"
                            reply(response_text)
                        else:
                            reply(f"Sorry, no definition found for {word}")
                    else:
                        reply(f"Sorry, no definition found for {word}")
                else:
                    reply(f"Sorry, couldn't find a definition for {word}")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    reply(f"Word '{word}' not found in dictionary. Check your spelling.")
                else:
                    reply("Dictionary service unavailable. Check your internet connection.")
            except Exception as e:
                print(f"Definition error: {e}")
                reply("Couldn't fetch definition. Check your internet connection.")
        else:
            reply("What word should I define?")

    # -----------------------------------------------------------------------
    # CALCULATIONS & CONVERSIONS
    # -----------------------------------------------------------------------
    elif 'calculate' in voice_data or 'math' in voice_data:
        try:
            expression = voice_data.replace('calculate', '').replace('math', '').strip()
            allowed_chars = set('0123456789+-*/()., ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                reply(f"The answer is: {result}")
            else:
                reply("Sorry, I can only calculate basic math expressions with numbers and operators.")
        except Exception:
            reply("I couldn't calculate that. Try something like: calculate 25 times 48")

    elif 'convert' in voice_data and (
        'usd' in voice_data or 'eur' in voice_data or 'gbp' in voice_data or
        'km' in voice_data or 'miles' in voice_data or
        'celsius' in voice_data or 'fahrenheit' in voice_data
    ):
        try:
            if 'km' in voice_data and 'miles' in voice_data:
                for word in voice_data.split():
                    try:
                        num = float(word)
                        if 'km' in voice_data.split('to')[0]:
                            reply(f"{num} kilometers equals {num * 0.621371:.2f} miles")
                        else:
                            reply(f"{num} miles equals {num * 1.60934:.2f} kilometers")
                        break
                    except Exception:
                        continue
            elif 'celsius' in voice_data or 'fahrenheit' in voice_data:
                for word in voice_data.split():
                    try:
                        num = float(word)
                        if 'celsius' in voice_data.split('to')[0]:
                            reply(f"{num}°C equals {(num * 9/5) + 32:.2f}°F")
                        else:
                            reply(f"{num}°F equals {(num - 32) * 5/9:.2f}°C")
                        break
                    except Exception:
                        continue
            else:
                reply("Currency conversion requires an API. Try unit conversions like: convert 5 km to miles")
        except Exception:
            reply("Conversion failed. Try: convert 5 km to miles")

    # -----------------------------------------------------------------------
    # NETWORK INFO
    # -----------------------------------------------------------------------
    elif 'ip address' in voice_data or 'show ip' in voice_data:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = socket.gethostbyname(socket.gethostname())
            finally:
                s.close()
            reply(f"Your local IP address is {local_ip}")
        except Exception:
            reply("Couldn't retrieve IP address. Check your network connection.")

    elif 'wifi name' in voice_data or 'wifi' in voice_data:
        try:
            if IS_MAC:
                wifi_output = os.popen("networksetup -getairportnetwork en0 2>/dev/null").read().strip()
                if "Current Wi-Fi Network:" in wifi_output:
                    wifi_name = wifi_output.split("Current Wi-Fi Network:")[1].strip()
                elif "not associated" in wifi_output.lower():
                    reply("Not connected to WiFi")
                    return
                else:
                    wifi_name = wifi_output.split(":")[-1].strip() if ":" in wifi_output else ""

                if not wifi_name:
                    wifi_name = os.popen("airport -I 2>/dev/null | awk '/ SSID/ {print substr($0, index($0, $2))}'").read().strip()
                if not wifi_name:
                    wifi_name = os.popen("system_profiler SPAirPortDataType 2>/dev/null | awk '/Current Network/ {getline; gsub(/^[ \\t]+|:$/, \"\"); print}'").read().strip()

                if wifi_name and "not associated" not in wifi_name.lower():
                    reply(f"Connected to: {wifi_name}")
                else:
                    reply("Not connected to WiFi or couldn't detect network")
            else:
                wifi_name = os.popen("netsh wlan show interfaces | findstr SSID").read()
                reply(f"WiFi info: {wifi_name}" if wifi_name else "Not connected to WiFi")
        except Exception:
            reply("Couldn't get WiFi information")

    # -----------------------------------------------------------------------
    # SYSTEM INFO
    # -----------------------------------------------------------------------
    elif 'battery' in voice_data:
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                reply(f"Battery is at {battery.percent}% and {'plugged in' if battery.power_plugged else 'on battery'}")
            else:
                reply("No battery found")
        except Exception:
            reply("Couldn't get battery information. Install psutil: pip install psutil")

    elif 'cpu' in voice_data:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            reply(f"CPU usage: {cpu}% <br> Memory usage: {memory}%")
        except Exception:
            reply("Install psutil to check system stats: pip install psutil")

    elif 'system info' in voice_data:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            info = (
                f"System Information: <br>"
                f"CPU: {cpu_count} cores ({cpu_count_logical} logical), {cpu_percent}% usage. <br>"
                f"Memory: {round(memory.used/(1024**3),2)}GB / {round(memory.total/(1024**3),2)}GB ({memory.percent}% used). <br>"
                f"Disk: {round(disk.used/(1024**3),2)}GB / {round(disk.total/(1024**3),2)}GB ({disk.percent}% used). <br>"
                f"Uptime: {uptime.days} days, {uptime.seconds // 3600} hours."
            )
            reply(info)
        except Exception:
            reply("Install psutil to check system stats: pip install psutil")

    # -----------------------------------------------------------------------
    # FUN COMMANDS (LLM-powered with static fallback)
    # -----------------------------------------------------------------------
    elif 'joke' in voice_data or 'tell me a joke' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Tell me a funny joke", "joke"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("joke"))
        else:
            reply(llm_helper._get_fallback_response("joke"))

    elif 'flip a coin' in voice_data or 'coin flip' in voice_data:
        import random
        reply(f"The coin landed on: {random.choice(['Heads', 'Tails'])}")

    elif 'roll a dice' in voice_data or 'roll dice' in voice_data:
        import random
        reply(f"The dice rolled: {random.randint(1, 6)}")

    elif 'magic 8 ball' in voice_data or 'magic eight ball' in voice_data:
        import random
        responses = [
            "It is certain", "Without a doubt", "Yes, definitely", "You may rely on it",
            "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes",
            "Reply hazy, try again", "Ask again later", "Better not tell you now",
            "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful"
        ]
        reply(random.choice(responses))

    elif 'motivational quote' in voice_data or 'motivate me' in voice_data or 'inspire me' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Give me a motivational quote", "quote"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("quote"))
        else:
            reply(llm_helper._get_fallback_response("quote"))

    elif 'random fact' in voice_data or 'tell me a fact' in voice_data or 'fun fact' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Tell me an interesting fact", "fact"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("fact"))
        else:
            reply(llm_helper._get_fallback_response("fact"))

    elif 'compliment me' in voice_data or 'say something nice' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Give me a compliment", "compliment"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("compliment"))
        else:
            reply(llm_helper._get_fallback_response("compliment"))

    elif 'insult me' in voice_data or 'roast me' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Give me a playful roast", "roast"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("roast"))
        else:
            reply(llm_helper._get_fallback_response("roast"))

    # -----------------------------------------------------------------------
    # EASTER EGGS
    # -----------------------------------------------------------------------
    elif 'sing' in voice_data or 'sing a song' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Sing a short funny song", "easter_egg_sing"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("easter_egg_sing"))
        else:
            reply(llm_helper._get_fallback_response("easter_egg_sing"))

    elif 'dance' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response("Describe your dance moves", "easter_egg_dance"))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("easter_egg_dance"))
        else:
            reply(llm_helper._get_fallback_response("easter_egg_dance"))

    elif 'tell me about yourself' in voice_data or 'about yourself' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response(
                    f"Tell the user about yourself. Your name is {state.assistant_name}.",
                    "easter_egg_about"
                ))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("easter_egg_about"))
        else:
            reply(llm_helper._get_fallback_response("easter_egg_about"))

    elif 'what do you think about ai' in voice_data or 'thoughts on ai' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response(
                    "What are your thoughts on AI and its role in the future?",
                    "easter_egg_ai_thoughts"
                ))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("easter_egg_ai_thoughts"))
        else:
            reply(llm_helper._get_fallback_response("easter_egg_ai_thoughts"))

    elif 'are you alive' in voice_data or 'are you real' in voice_data or 'are you conscious' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response(
                    "Are you alive? Are you conscious? Give a philosophical answer.",
                    "easter_egg_alive"
                ))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("easter_egg_alive"))
        else:
            reply(llm_helper._get_fallback_response("easter_egg_alive"))

    elif 'good job' in voice_data or 'well done' in voice_data or 'great job' in voice_data or 'thank you' in voice_data:
        if LLM_AVAILABLE:
            try:
                reply(llm_helper.get_creative_response(
                    f"The user thanked you. Respond warmly as {state.assistant_name}.",
                    "appreciation"
                ))
            except Exception as e:
                print(f"[LLM ERROR] {e}")
                reply(llm_helper._get_fallback_response("appreciation"))
        else:
            reply(llm_helper._get_fallback_response("appreciation"))

    # -----------------------------------------------------------------------
    # HELP
    # -----------------------------------------------------------------------
    elif voice_data == 'help' or voice_data == 'commands' or voice_data == 'what can you do':
        help_text = "Available commands: <br>"
        help_text += "• Basic: hello, time, date, search, weather <br>"
        help_text += "• Apps: open app [name], close app [name] <br>"
        help_text += "• System: volume up/down, brightness, screenshot, lock <br>"
        help_text += "• Search: youtube search, github search, stackoverflow <br>"
        help_text += "• Tools: calculate, convert, translate, define <br>"
        help_text += "• Power: cleanup desktop, empty recycle bin, startup apps status, network speed test <br>"
        help_text += "• Info: battery, cpu, system info, ip address, wifi name <br>"
        help_text += "• Fun: joke, flip coin, roll dice, magic 8 ball, motivational quote, random fact <br>"
        help_text += "• Easter eggs: Try 'quantum sing', 'good job quantum' <br>"
        help_text += "Say 'quantum' before each command!"
        reply(help_text)

    # -----------------------------------------------------------------------
    # FILE NAVIGATION
    # -----------------------------------------------------------------------
    elif 'list' in voice_data:
        counter = 0
        state.path = (os.path.expanduser('~') + '/') if IS_MAC else 'C://'
        state.files = listdir(state.path)
        filestr = ""
        for f in state.files:
            counter += 1
            print(str(counter) + ':  ' + f)
            filestr += str(counter) + ':  ' + f + '<br>'
        state.file_exp_status = True
        reply('These are the files in your root directory')
        app.ChatBot.addAppMsg(filestr)

    elif state.file_exp_status:
        counter = 0
        if 'open' in voice_data:
            file_path = join(state.path, state.files[int(voice_data.split(' ')[-1]) - 1])
            if isfile(file_path):
                if IS_MAC:
                    os.system(f'open "{file_path}"')
                else:
                    os.startfile(file_path)
                state.file_exp_status = False
            else:
                try:
                    separator = '/' if IS_MAC else '//'
                    state.path = state.path + state.files[int(voice_data.split(' ')[-1]) - 1] + separator
                    state.files = listdir(state.path)
                    filestr = ""
                    for f in state.files:
                        counter += 1
                        filestr += str(counter) + ':  ' + f + '<br>'
                        print(str(counter) + ':  ' + f)
                    reply('Opened Successfully')
                    app.ChatBot.addAppMsg(filestr)
                except Exception:
                    reply('You do not have permission to access this folder')

        if 'back' in voice_data:
            filestr = ""
            root_path = (os.path.expanduser('~') + '/') if IS_MAC else 'C://'
            if state.path == root_path:
                reply('Sorry, this is the root directory')
            else:
                separator = '/' if IS_MAC else '//'
                parts = state.path.split(separator)[:-2]
                state.path = separator.join(parts) + separator
                state.files = listdir(state.path)
                for f in state.files:
                    counter += 1
                    filestr += str(counter) + ':  ' + f + '<br>'
                    print(str(counter) + ':  ' + f)
                reply('ok')
                app.ChatBot.addAppMsg(filestr)

    else:
        reply('I am not functioned to do this !')
