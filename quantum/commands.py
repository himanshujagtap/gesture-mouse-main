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

import subprocess as _subprocess
import os as _os
_GESTURE_SCRIPT = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'Gesture_Controller.py')
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

_BROWSERS_MAC = ['Brave Browser', 'Google Chrome', 'Safari', 'Firefox', 'Microsoft Edge']

def _focus_browser():
    """Bring the browser window to front before sending keyboard shortcuts."""
    if IS_MAC:
        for b in _BROWSERS_MAC:
            r = _subprocess.run(
                ['osascript', '-e', f'tell application "{b}" to activate'],
                capture_output=True
            )
            if r.returncode == 0:
                time.sleep(0.4)
                return
    else:
        # Windows: send shortcut directly — browser usually stays focused
        pass

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

    sorted_commands = sorted(command_keywords, key=len, reverse=True)

    # Pass 1: Exact prefix match — return unchanged if input already starts with a valid command
    for cmd in sorted_commands:
        cmd_words = cmd.split()
        if len(cmd_words) > 1 and len(words) >= len(cmd_words):
            if ' '.join(words[:len(cmd_words)]) == cmd:
                return input_text
    if len(words) == 1 and words[0] in [kw for kw in command_keywords if ' ' not in kw]:
        return input_text

    # Pass 2: Fuzzy matching — try to correct typos
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

    # Strip assistant name prefix (case-insensitive, prefix only)
    voice_data_lower = voice_data.lower()
    for name in ['quantum', 'proton', 'jarvis', state.assistant_name.lower()]:
        if voice_data_lower.startswith(name):
            voice_data_lower = voice_data_lower[len(name):].strip()
            break
    voice_data = voice_data_lower.strip()

    # Apply fuzzy matching to correct typos
    voice_data = fuzzy_match(voice_data)
    print(f"[DEBUG] After fuzzy match: {voice_data}")

    app.eel.addUserMsg(voice_data)()

    # Track for dashboard (silent — never raises)
    try:
        from quantum import stats as _stats
        _stats.track_command(voice_data)
    except Exception:
        pass

    # -----------------------------------------------------------------------
    # SLEEP / WAKE
    # -----------------------------------------------------------------------
    if state.is_awake == False:
        if 'wake up' in voice_data or 'wakeup' in voice_data or 'wake' in voice_data:
            state.is_awake = True
            app.eel.setAwakeStatus(True)()
            reply("I'm awake now!")
            from quantum.audio_io import wish
            wish()
        return

    # -----------------------------------------------------------------------
    # TEXT INPUT  (must come before 'hello' so "type hello …" isn't intercepted)
    # -----------------------------------------------------------------------
    elif voice_data.startswith('type '):
        text_to_type = voice_data[5:].strip()
        if text_to_type:
            time.sleep(2)
            pyautogui.typewrite(text_to_type, interval=0.1)
            reply(f"Typed: {text_to_type}")
        else:
            reply("What should I type?")

    # -----------------------------------------------------------------------
    # BASIC COMMANDS
    # -----------------------------------------------------------------------
    elif voice_data.startswith('hello') or voice_data == 'hello':
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
        now = datetime.datetime.now()
        reply(f"{now.hour} hours {now.minute} minutes and {now.second} seconds")

    elif 'search' in voice_data and 'youtube' not in voice_data and 'github' not in voice_data and 'stackoverflow' not in voice_data and 'history' not in voice_data and 'search history' not in voice_data:
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
        app.eel.setAwakeStatus(False)()

    elif ('exit' in voice_data) or ('terminate' in voice_data):
        if state.gesture_process and state.gesture_process.poll() is None:
            state.gesture_process.terminate()
            state.gesture_process = None
        app.ChatBot.close()
        sys.exit()

    # -----------------------------------------------------------------------
    # GESTURE RECOGNITION
    # -----------------------------------------------------------------------
    elif 'launch gesture recognition' in voice_data:
        if state.gesture_process and state.gesture_process.poll() is None:
            reply('Gesture recognition is already active')
        else:
            state.gesture_process = _subprocess.Popen([sys.executable, _GESTURE_SCRIPT])
            reply('Launched Successfully')

    elif ('stop gesture recognition' in voice_data) or ('top gesture recognition' in voice_data):
        if state.gesture_process and state.gesture_process.poll() is None:
            state.gesture_process.terminate()
            state.gesture_process = None
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

    elif 'clipboard history' in voice_data or 'show clipboard' in voice_data or 'clipboard list' in voice_data:
        from quantum.clipboard import get_history
        history = get_history()
        if not history:
            reply("Your clipboard history is empty. Copy something and I'll start tracking it.")
        else:
            lines = [f"{n}. {preview}" for n, preview in history]
            reply("Here's your clipboard history:<br>" + "<br>".join(lines) + "<br>Say 'paste item 2' to paste any entry.")

    elif 'clear clipboard' in voice_data:
        from quantum.clipboard import clear_history
        clear_history()
        reply("Clipboard history cleared.")

    elif any(kw in voice_data for kw in ('paste item', 'paste number', 'paste entry', 'paste the')):
        from quantum.clipboard import paste_item, get_history, ordinal
        import re as _re
        # Parse ordinals like "paste 2nd item", "paste item 3", "paste the third"
        ordinal_map = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
            'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
        }
        n = None
        for word, num in ordinal_map.items():
            if word in voice_data:
                n = num
                break
        if n is None:
            m = _re.search(r'\d+', voice_data)
            if m:
                n = int(m.group())
        if n is None:
            history = get_history()
            if history:
                reply("Which item? Say 'paste item 1' through 'paste item " + str(len(history)) + "'.")
            else:
                reply("Clipboard history is empty.")
        else:
            ok = paste_item(n)
            if ok:
                reply(f"Pasting {ordinal(n)} clipboard item.")
            else:
                from quantum.clipboard import get_history as _gh
                count = len(_gh())
                if count == 0:
                    reply("Clipboard history is empty.")
                else:
                    reply(f"I only have {count} item{'s' if count > 1 else ''} in clipboard history.")

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
            os.system("osascript -e 'tell application \"System Events\" to perform action \"AXZoom\" of (first window of (first process whose frontmost is true))'")
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
    # FILE SEARCH & OPEN BY VOICE
    # -----------------------------------------------------------------------
    elif any(kw in voice_data for kw in ('find file', 'search for file', 'find my', 'find folder', 'search file', 'locate file')):
        from quantum.file_search import search_files
        # Strip trigger phrases to get the query
        query = voice_data
        for kw in ('find file', 'search for file', 'find my', 'find folder', 'search file', 'locate file'):
            query = query.replace(kw, '')
        query = query.strip()
        if not query:
            reply("What file are you looking for?")
        else:
            reply(f"Searching for '{query}'…")
            results = search_files(query)
            state.file_search_results = results
            if not results:
                reply(f"No files found matching '{query}'.")
            else:
                lines = []
                for i, (score, path, is_dir) in enumerate(results, 1):
                    kind = 'Folder' if is_dir else 'File'
                    name = os.path.basename(path)
                    lines.append(f"{i}. {kind}: {name}")
                reply("Found these matches:<br>" + "<br>".join(lines) + "<br>Say 'open file 1' (or whichever number) to open.")

    elif 'open file' in voice_data or 'open result' in voice_data:
        from quantum.file_search import search_files, open_path
        # Try to parse a number (e.g. "open file 2")
        import re as _re
        m = _re.search(r'\d+', voice_data)
        if m and state.file_search_results:
            idx = int(m.group()) - 1
            if 0 <= idx < len(state.file_search_results):
                _, path, _ = state.file_search_results[idx]
                reply(f"Opening {os.path.basename(path)}")
                open_path(path)
            else:
                reply(f"I only have {len(state.file_search_results)} results. Please say a valid number.")
        else:
            # No previous results or no number — treat remainder as a fresh query and open best match
            query = voice_data.replace('open file', '').replace('open result', '').strip()
            if not query:
                reply("What file should I open?")
            else:
                results = search_files(query)
                if results:
                    _, path, _ = results[0]
                    reply(f"Opening {os.path.basename(path)}")
                    open_path(path)
                else:
                    reply(f"Could not find a file matching '{query}'.")

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
        if 'tab' in voice_data:
            _focus_browser()
            pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'w')
            reply("Closing tab")
        elif 'window' in voice_data:
            _focus_browser()
            if IS_MAC:
                pyautogui.hotkey('command', 'shift', 'w')
            else:
                pyautogui.hotkey('alt', 'f4')
            reply("Closing window")
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
        def _format_weather(raw):
            icon_map = {
                '\u2600\ufe0f': 'sunny', '\u2600': 'sunny',
                '\U0001f324': 'mostly sunny', '\U0001f325': 'partly cloudy',
                '\u26c5': 'partly cloudy', '\U0001f326': 'light rain',
                '\U0001f327': 'rainy', '\u26c8': 'thunderstorm',
                '\U0001f329': 'thunderstorm', '\U0001f328': 'snowy',
                '\u2744\ufe0f': 'snowing', '\u2744': 'snowing',
                '\U0001f32b': 'foggy', '\U0001f32c': 'windy',
                '\U0001f32a': 'stormy', '\U0001f321': '',
                '\U0001f302': 'rainy',
            }
            text = raw.strip()
            for icon, word in icon_map.items():
                text = text.replace(icon, f' {word} ' if word else ' ')
            import re as _re
            text = _re.sub(r'[^\x00-\x7F\s\u00b0+\-\d:,./()a-zA-Z]', '', text)
            text = text.replace('+', 'positive ').replace('-', 'negative ')
            text = _re.sub(r'\u00b0[Cc]', ' degrees celsius', text)
            text = _re.sub(r'\u00b0[Ff]', ' degrees fahrenheit', text)
            text = _re.sub(r'\s+', ' ', text).strip()
            return text

        try:
            import urllib.request
            location = voice_data.replace('weather', '').strip() or 'auto'
            url = f"http://wttr.in/{location}?format=3"
            with urllib.request.urlopen(url, timeout=5) as response:
                weather = response.read().decode('utf-8')
            reply(f"Current weather: {_format_weather(weather)}")
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
    # BROWSER CONTROLS  (focus browser first, then send shortcut)
    # -----------------------------------------------------------------------
    elif 'new tab' in voice_data:
        _focus_browser()
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 't')
        reply("Opening new tab")

    elif 'close tab' in voice_data:
        _focus_browser()
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'w')
        reply("Closing tab")

    elif 'close window' in voice_data:
        _focus_browser()
        if IS_MAC:
            pyautogui.hotkey('command', 'shift', 'w')
        else:
            pyautogui.hotkey('alt', 'f4')
        reply("Closing window")

    elif 'incognito' in voice_data or 'private' in voice_data:
        _focus_browser()
        pyautogui.hotkey('command' if IS_MAC else 'ctrl', 'shift', 'n')
        reply("Opening incognito window")

    elif 'refresh' in voice_data or 'reload' in voice_data:
        _focus_browser()
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
            preview = ',<br> '.join(apps[:12])
            extra = len(apps) - 12
            if extra > 0:
                reply(f"Found {len(apps)} startup app entries. First entries: {preview} ... and {extra} more.")
            else:
                reply(f"Found {len(apps)} startup app entries: <br>{preview}<br>")
        else:
            reply('No startup app entries found.')

    elif 'network speed test' in voice_data or 'speed test' in voice_data:
        try:
            reply('Running network speed test. This may take few seconds...')
            app.eel.showThinkingBubble()()  # re-show thinking while test runs
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
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
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
                    reply(f"No dictionary entry found for '{word}'. It may be a proper noun, brand name, or abbreviation.")
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
            # Replace word operators and common voice alternatives
            import re as _re
            expression = (expression
                .replace('multiplied by', '*').replace('times', '*')
                .replace('divided by', '/').replace('over', '/')
                .replace('plus', '+').replace('minus', '-').replace('subtract', '-')
                .replace('power', '**').replace('squared', '**2').replace('cubed', '**3')
                .replace('mod ', '%').replace('modulo', '%')
            )
            # Replace 'x' used as multiplication (with or without spaces)
            expression = _re.sub(r'(?<=\d)\s*x\s*(?=\d)', '*', expression)
            allowed_chars = set('0123456789+-**/()., %')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                # Show as int if whole number
                result_str = str(int(result)) if isinstance(result, float) and result.is_integer() else str(result)
                reply(f"The answer is: {result_str}")
            else:
                reply("Sorry, I can only calculate basic math. Try: calculate 25 times 48")
        except Exception:
            reply("I couldn't calculate that. Try: calculate 25 times 48")

    elif 'convert' in voice_data:
        def _fmt(n, decimals=2):
            formatted = f"{abs(n):.{decimals}f}"
            return f"negative {formatted}" if n < 0 else formatted

        try:
            vd = voice_data
            # Normalise abbreviations/alternate spellings so the checks below fire reliably
            import re as _re
            vd = _re.sub(r'\bmb\b', 'megabyte', vd)
            vd = _re.sub(r'\bgb\b', 'gigabyte', vd)
            vd = _re.sub(r'\btb\b', 'terabyte', vd)
            vd = vd.replace('litre', 'liter')
            # Normalise full currency names to ISO codes
            _cnames = {
                'us dollar': 'usd', 'us dollars': 'usd', 'united states dollar': 'usd', 'american dollar': 'usd',
                'euro': 'eur', 'euros': 'eur',
                'british pound': 'gbp', 'pound sterling': 'gbp', 'pounds': 'gbp', 'pound': 'gbp',
                'indian rupee': 'inr', 'indian rupees': 'inr', 'rupee': 'inr', 'rupees': 'inr',
                'japanese yen': 'jpy', 'yen': 'jpy',
                'canadian dollar': 'cad', 'canadian dollars': 'cad',
                'australian dollar': 'aud', 'australian dollars': 'aud',
                'swiss franc': 'chf', 'franc': 'chf', 'francs': 'chf',
                'emirati dirham': 'aed', 'dirham': 'aed', 'dirhams': 'aed',
                'chinese yuan': 'cny', 'yuan': 'cny', 'renminbi': 'cny',
                'singapore dollar': 'sgd', 'singapore dollars': 'sgd',
                'mexican peso': 'mxn', 'peso': 'mxn', 'pesos': 'mxn',
            }
            for _cname, _code in sorted(_cnames.items(), key=lambda x: -len(x[0])):
                if _cname in vd:
                    vd = vd.replace(_cname, _code)
            # Normalise currency symbols to codes (e.g. €50 → eur 50)
            _csymbols = {'$': 'usd', '€': 'eur', '£': 'gbp', '¥': 'jpy', '₹': 'inr', '₩': 'krw', '₣': 'chf'}
            for _sym, _code in _csymbols.items():
                vd = _re.sub(r'\{}(\d)'.format(_re.escape(_sym)), r'{} \1'.format(_code), vd)
                vd = vd.replace(_sym, _code + ' ')
            num = None
            for word in vd.split():
                try:
                    num = float(word)
                    break
                except ValueError:
                    continue

            if num is None:
                reply("Please say a number to convert. Example: convert 5 km to miles")
            # ── Distance ──────────────────────────────────────────────────────
            elif 'km' in vd and 'mile' in vd:
                if 'km' in vd.split('to')[0]:
                    reply(f"{num} kilometers equals {_fmt(num * 0.621371)} miles")
                else:
                    reply(f"{num} miles equals {_fmt(num * 1.60934)} kilometers")
            elif ('meter' in vd or 'metre' in vd) and ('feet' in vd or 'foot' in vd):
                if 'meter' in vd.split('to')[0] or 'metre' in vd.split('to')[0]:
                    reply(f"{num} meters equals {_fmt(num * 3.28084)} feet")
                else:
                    reply(f"{num} feet equals {_fmt(num / 3.28084)} meters")
            elif ('meter' in vd or 'metre' in vd) and 'inch' in vd:
                if 'meter' in vd.split('to')[0] or 'metre' in vd.split('to')[0]:
                    reply(f"{num} meters equals {_fmt(num * 39.3701)} inches")
                else:
                    reply(f"{num} inches equals {_fmt(num / 39.3701, 4)} meters")
            elif ('centimeter' in vd or ' cm ' in vd) and 'inch' in vd:
                if 'centimeter' in vd.split('to')[0] or ' cm ' in vd.split('to')[0]:
                    reply(f"{num} centimeters equals {_fmt(num / 2.54)} inches")
                else:
                    reply(f"{num} inches equals {_fmt(num * 2.54)} centimeters")
            # ── Temperature ───────────────────────────────────────────────────
            elif 'celsius' in vd or 'fahrenheit' in vd:
                if 'celsius' in vd.split('to')[0]:
                    reply(f"{num} degrees celsius equals {_fmt((num * 9/5) + 32)} degrees fahrenheit")
                else:
                    reply(f"{num} degrees fahrenheit equals {_fmt((num - 32) * 5/9)} degrees celsius")
            # ── Weight ────────────────────────────────────────────────────────
            elif ('kg' in vd or 'kilogram' in vd) and ('pound' in vd or ' lb' in vd or 'lbs' in vd):
                if 'kg' in vd.split('to')[0] or 'kilogram' in vd.split('to')[0]:
                    reply(f"{num} kilograms equals {_fmt(num * 2.20462)} pounds")
                else:
                    reply(f"{num} pounds equals {_fmt(num / 2.20462)} kilograms")
            elif 'gram' in vd and 'ounce' in vd:
                if 'gram' in vd.split('to')[0]:
                    reply(f"{num} grams equals {_fmt(num / 28.3495)} ounces")
                else:
                    reply(f"{num} ounces equals {_fmt(num * 28.3495)} grams")
            # ── Volume ────────────────────────────────────────────────────────
            elif 'liter' in vd and 'gallon' in vd:
                if 'liter' in vd.split('to')[0]:
                    reply(f"{num} liters equals {_fmt(num * 0.264172)} gallons")
                else:
                    reply(f"{num} gallons equals {_fmt(num / 0.264172)} liters")
            elif ('milliliter' in vd or ' ml ' in vd) and ('fluid ounce' in vd or 'fl oz' in vd):
                if 'milliliter' in vd.split('to')[0] or ' ml ' in vd.split('to')[0]:
                    reply(f"{num} milliliters equals {_fmt(num / 29.5735)} fluid ounces")
                else:
                    reply(f"{num} fluid ounces equals {_fmt(num * 29.5735)} milliliters")
            # ── Speed ─────────────────────────────────────────────────────────
            elif ('kmh' in vd or 'kph' in vd or 'km per hour' in vd or 'kilometer per hour' in vd) and 'mph' in vd:
                if any(x in vd.split('to')[0] for x in ['kmh', 'kph', 'km per hour', 'kilometer per hour']):
                    reply(f"{num} km/h equals {_fmt(num * 0.621371)} mph")
                else:
                    reply(f"{num} mph equals {_fmt(num / 0.621371)} km/h")
            # ── Data ──────────────────────────────────────────────────────────
            elif 'megabyte' in vd and 'gigabyte' in vd:
                if 'megabyte' in vd.split('to')[0]:
                    reply(f"{num} megabytes equals {_fmt(num / 1024, 4)} gigabytes")
                else:
                    reply(f"{num} gigabytes equals {_fmt(num * 1024, 0)} megabytes")
            elif 'gigabyte' in vd and 'terabyte' in vd:
                if 'gigabyte' in vd.split('to')[0]:
                    reply(f"{num} gigabytes equals {_fmt(num / 1024, 4)} terabytes")
                else:
                    reply(f"{num} terabytes equals {_fmt(num * 1024, 0)} gigabytes")
            elif 'megabyte' in vd and 'terabyte' in vd:
                if 'megabyte' in vd.split('to')[0]:
                    reply(f"{num} megabytes equals {_fmt(num / (1024 * 1024), 8)} terabytes")
                else:
                    reply(f"{num} terabytes equals {_fmt(num * 1024 * 1024, 0)} megabytes")
            # ── Time ──────────────────────────────────────────────────────────
            elif 'hour' in vd and 'minute' in vd:
                if 'hour' in vd.split('to')[0]:
                    reply(f"{num} hours equals {_fmt(num * 60, 0)} minutes")
                else:
                    reply(f"{num} minutes equals {_fmt(num / 60, 4)} hours")
            elif 'hour' in vd and 'second' in vd:
                if 'hour' in vd.split('to')[0]:
                    reply(f"{num} hours equals {_fmt(num * 3600, 0)} seconds")
                else:
                    reply(f"{num} seconds equals {_fmt(num / 3600, 4)} hours")
            elif 'minute' in vd and 'second' in vd:
                if 'minute' in vd.split('to')[0]:
                    reply(f"{num} minutes equals {_fmt(num * 60, 0)} seconds")
                else:
                    reply(f"{num} seconds equals {_fmt(num / 60, 4)} minutes")
            # ── Currency (open.er-api.com — free, no key) ─────────────────────
            elif any(c in vd for c in ['usd', 'eur', 'gbp', 'inr', 'jpy', 'cad', 'aud', 'chf', 'aed', 'cny', 'sgd', 'mxn']):
                try:
                    import urllib.request, json as _json, ssl as _ssl
                    currencies = ['usd', 'eur', 'gbp', 'inr', 'jpy', 'cad', 'aud', 'chf', 'aed', 'cny', 'sgd', 'mxn']
                    parts = vd.split('to')
                    from_cur, to_cur = None, None
                    if len(parts) >= 2:
                        for c in currencies:
                            if c in parts[0]:
                                from_cur = c.upper()
                            if c in parts[1]:
                                to_cur = c.upper()
                    if from_cur and to_cur:
                        ssl_ctx = _ssl.create_default_context()
                        ssl_ctx.check_hostname = False
                        ssl_ctx.verify_mode = _ssl.CERT_NONE
                        api_url = f"https://open.er-api.com/v6/latest/{from_cur}"
                        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                            data = _json.loads(resp.read().decode())
                        rate = data['rates'][to_cur]
                        reply(f"{num} {from_cur} equals {num * rate:.2f} {to_cur}")
                    else:
                        reply("Please specify both currencies. Example: convert 100 usd to inr")
                except Exception as _e:
                    reply(f"Currency conversion failed. ({_e})")
            else:
                reply(
                    "I can convert only in below units:<br>km/miles, meters/feet/inches, cm/inches, "
                    "celsius/fahrenheit, kg/pounds, grams/ounces, liters/gallons, "
                    "ml/fluid ounces, km per hour/mph, megabytes/gigabytes/terabytes, "
                    "hours/minutes/seconds, and currencies like USD, EUR, GBP, INR, JPY, CAD, AUD"
                )
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
    # COMMAND HISTORY
    # -----------------------------------------------------------------------
    elif 'history search' in voice_data or 'search history' in voice_data:
        try:
            from quantum import stats as _stats
            import re as _re
            query = voice_data.replace('history search', '').replace('search history', '').strip()
            hist = list(reversed(_stats._command_history))   # newest first
            if not hist:
                reply("No command history yet this session.")
            elif not query:
                # Show most recent 10 without filtering
                lines = [f"{i+1}. [{h['time']}] {h['cmd']}" for i, h in enumerate(hist[:10])]
                reply("Recent commands:<br>" + "<br>".join(lines) + "<br>Say 'run history 2' to re-run any entry.")
                state.file_search_results = [(1.0, h['cmd'], False) for h in hist[:10]]
            else:
                matches = [(i, h) for i, h in enumerate(hist) if query in h['cmd'].lower()]
                if not matches:
                    reply(f"No history entries match '{query}'.")
                else:
                    lines = [f"{n+1}. [{h['time']}] {h['cmd']}" for n, (_, h) in enumerate(matches[:10])]
                    reply("Matching history entries:\n" + "\n".join(lines) + "\nSay 'run history 1' to re-run.")
                    # Reuse file_search_results slot to store matched commands
                    state.file_search_results = [(1.0, h['cmd'], False) for _, h in matches[:10]]
        except Exception as _e:
            reply(f"Could not search history: {_e}")

    elif any(kw in voice_data for kw in ('run last command', 'repeat last', 'run again', 'redo last', 'repeat command')):
        try:
            from quantum import stats as _stats
            _META = ('run last command', 'repeat last', 'run again', 'redo last', 'repeat command',
                     'run history', 'history search', 'search history', 'run command number', 'rerun')
            # Walk backwards to find the most recent non-meta command
            last_cmd = None
            for entry in reversed(_stats._command_history):
                cmd = entry['cmd']
                if not any(m in cmd for m in _META):
                    last_cmd = cmd
                    break
            if last_cmd:
                reply(f"Running again: {last_cmd}")
                respond(last_cmd)
            else:
                reply("No previous command to repeat.")
        except Exception as _e:
            reply(f"Could not repeat command: {_e}")

    elif 'run history' in voice_data or 'run command number' in voice_data or 'rerun' in voice_data:
        import re as _re
        _META = ('run last command', 'repeat last', 'run again', 'redo last', 'repeat command',
                 'run history', 'history search', 'search history', 'run command number', 'rerun')
        m = _re.search(r'\d+', voice_data)
        if m:
            n = int(m.group()) - 1
            # file_search_results holds the last history search results
            if state.file_search_results and 0 <= n < len(state.file_search_results):
                _, cmd, _ = state.file_search_results[n]
                if any(kw in cmd for kw in _META):
                    reply("That entry is a history command itself — I can't re-run it.")
                else:
                    reply(f"Re-running: {cmd}")
                    respond(cmd)
            else:
                # Fall back to raw stats history
                try:
                    from quantum import stats as _stats
                    hist = list(reversed(_stats._command_history))
                    if 0 <= n < len(hist):
                        cmd = hist[n]['cmd']
                        if any(kw in cmd for kw in _META):
                            reply("That entry is a history command itself — I can't re-run it.")
                        else:
                            reply(f"Re-running: {cmd}")
                            respond(cmd)
                    else:
                        reply(f"History only has {len(hist)} entries.")
                except Exception:
                    reply("Could not find that history entry.")
        else:
            reply("Please say a number, like 'run history 2'.")

    # -----------------------------------------------------------------------
    # HELP
    # -----------------------------------------------------------------------
    elif voice_data == 'help' or voice_data == 'commands' or voice_data == 'what can you do':
        help_text = "Available commands: <br>"
        help_text += "• Basic: hello, time, date, weather, location, what is your name <br>"
        help_text += "• Clipboard: copy, paste, type [text] <br>"
        help_text += "• Window: minimize, maximize, scroll up, scroll down <br>"
        help_text += "• System: volume up/down, mute/unmute, brightness up/down, screenshot, lock screen <br>"
        help_text += "• Browser: new tab, close tab, incognito, refresh <br>"
        help_text += "• Music: play music, pause music, next song, previous song <br>"
        help_text += "• Apps: open app [name], close app [name] <br>"
        help_text += "• Gesture: launch gesture recognition, stop gesture recognition <br>"
        help_text += "• Search: search [query], youtube search [query], github search [query], stackoverflow [query] <br>"
        help_text += "• Tools: calculate [expr], convert [unit], translate [text], define [word], wikipedia [topic], set timer [duration] <br>"
        help_text += "• Files: list (browse root directory) <br>"
        help_text += "• Info: battery, cpu, system info, ip address, wifi name <br>"
        help_text += "• Power: cleanup desktop, empty recycle bin, startup apps status, network speed test <br>"
        help_text += "• Fun: joke, flip coin, roll dice, magic 8 ball, motivational quote, random fact, compliment me, roast me, sing, dance <br>"
        help_text += "• About: tell me about yourself, are you alive, thoughts on ai, change name to [name] <br>"
        help_text += "• Easter eggs: good job quantum, well done quantum, thank you quantum <br>"
        help_text += "Say 'quantum' before each command!"
        reply(help_text)

    # -----------------------------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------------------------
    elif 'show dashboard' in voice_data or 'open dashboard' in voice_data or voice_data == 'dashboard':
        webbrowser.get().open('http://localhost:27005/dashboard.html')
        reply("Opening Quantum Dashboard in your browser")

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
        import random as _random
        _unknown_responses = [
            "Hmm, that's beyond my current abilities. Try asking something else!",
            "I'm not sure how to help with that one. Got another command?",
            "That's outside my skill set for now. Maybe I'll learn it someday!",
            "I didn't quite get that. Could you try rephrasing?",
            "Not in my command book yet! Try 'help' to see what I can do.",
            "That one stumped me. I'm good, but not that good... yet.",
            "I wish I could help with that, but it's not something I support.",
            "Interesting request, but that's a no from me. Try something else!",
            "I'm drawing a blank on that. Ask me something different?",
            "That command doesn't ring a bell. Type 'help' for a full list.",
            "Oops, I don't know how to do that. But I'm always learning!",
            "I heard you, but I don't know what to do with that. Try 'help'.",
            "That's a new one for me! Unfortunately, I can't handle it right now.",
            "Not quite in my repertoire. What else can I do for you?",
            "I'm Quantum, not magic — that one's out of my range!",
            "My circuits are drawing a blank on that one.",
            "Even I have limits — and that's one of them. For now!",
            "I processed that and came up with... nothing. Sorry!",
            "That's above my pay grade. Try a different command?",
            "Unknown territory! I'd explore it, but I don't have a map.",
            "I'm still growing — that feature hasn't been added to me yet.",
            "Did you mean something else? I couldn't match that to any command.",
            "Request received, capability not found. Try 'help' for ideas.",
            "I'm confident I can do a lot — just not that. Not yet, anyway.",
            "That sailed right over my head. What else can I do for you?",
            "Scanning knowledge base... command not found. Try rephrasing?",
            "I'd love to help, but that one's not in my arsenal.",
            "Interesting! But I have no idea how to do that. Ask me something else.",
            "My best guess is that you want something I don't support — yet.",
            "That's a mystery to me. Type 'help' and let's find something I can do!",
        ]
        reply(_random.choice(_unknown_responses))
