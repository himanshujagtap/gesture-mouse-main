import pyttsx3
import speech_recognition as sr
from datetime import date
import time
import webbrowser
import datetime
from pynput.keyboard import Key, Controller
import pyautogui
import sys
import os
from os import listdir
from os.path import isfile, join
import smtplib
import wikipedia
import Gesture_Controller
#import Gesture_Controller_Gloved as Gesture_Controller
import app
from threading import Thread
import platform
from difflib import get_close_matches

# Detect OS for keyboard shortcuts
IS_MAC = platform.system() == 'Darwin'
CMD_KEY = Key.cmd if IS_MAC else Key.ctrl


# -------------Object Initialization---------------
today = date.today()
r = sr.Recognizer()
keyboard = Controller()

# Initialize text-to-speech (cross-platform with fallback)
engine = None
TTS_AVAILABLE = False
try:
    if IS_MAC:
        # Try macOS text-to-speech
        try:
            engine = pyttsx3.init()
            TTS_AVAILABLE = True
        except Exception as e:
            print(f"pyttsx3 not available on macOS: {e}")
            print("Quantum will use macOS 'say' command for speech instead")
    else:
        # Windows
        engine = pyttsx3.init('sapi5')
        TTS_AVAILABLE = True

    if TTS_AVAILABLE and engine:
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
except Exception as e:
    print(f"Text-to-speech initialization failed: {e}")
    print("Quantum will run without voice feedback")

# ----------------Variables------------------------
file_exp_status = False
files =[]
path = ''
is_awake = True  #Bot status
assistant_name = "Quantum"  # Dynamic assistant name
blank_input_responses = [
    "I didn't catch that. Could you repeat?",
    "Sorry, I couldn't hear you clearly.",
    "Hmm, it seems you didn't say anything.",
    "I'm listening... but I didn't hear a command.",
    "Could you speak a bit louder? I missed that."
]
blank_response_index = 0
typing_mode = False  # Typing mode state
text_input_mode = False  # Track if in text input mode

# ------------------Functions----------------------
def reply(audio):
    app.ChatBot.addAppMsg(audio)
    print(audio)

    # Text-to-speech with fallback for macOS
    if TTS_AVAILABLE and engine:
        try:
            engine.say(audio)
            engine.runAndWait()
        except:
            # Fallback to macOS say command
            if IS_MAC:
                os.system(f'say "{audio}"')
    elif IS_MAC:
        # Use macOS say command directly
        os.system(f'say "{audio}"')


def wish():
    hour = int(datetime.datetime.now().hour)

    if hour>=0 and hour<12:
        reply("Good Morning!")
    elif hour>=12 and hour<18:
        reply("Good Afternoon!")
    else:
        reply("Good Evening!")

    reply(f"I am {assistant_name}, how may I help you?")

# Set Microphone parameters
with sr.Microphone() as source:
        r.energy_threshold = 500 
        r.dynamic_energy_threshold = False

# Audio to String
def record_audio():
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
            pass
        return voice_data.lower()


# Fuzzy command matching
def fuzzy_match(input_text):
    """Apply fuzzy matching to correct common typos in commands"""
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
        'calculate', 'convert', 'youtube search', 'github search', 'stackoverflow',
        'translate', 'define', 'ip address', 'wifi name', 'motivational quote',
        'random fact', 'magic 8 ball', 'compliment me', 'insult me', 'help',
        'sing', 'dance', 'tell me about yourself', 'what do you think about ai',
        'good job', 'are you alive'
    ]

    # First, try to match multi-word command phrases (longer matches first)
    sorted_commands = sorted(command_keywords, key=len, reverse=True)
    for cmd in sorted_commands:
        if len(cmd.split()) > 1:  # Multi-word commands
            matches = get_close_matches(input_text, [cmd], n=1, cutoff=0.75)
            if matches:
                # Check if the match is a prefix command (e.g., "change name to jarvis")
                # Preserve the rest of the input after the command
                if input_text.startswith(matches[0].split()[0]):
                    return input_text  # Return original to preserve parameters
                return matches[0]

    # Then try matching individual words for simple typo correction
    words = input_text.split()
    corrected_words = []

    for word in words:
        # Try to find close matches for each word
        matches = get_close_matches(word,
                                   [kw for cmd in command_keywords for kw in cmd.split()],
                                   n=1, cutoff=0.75)
        if matches:
            corrected_words.append(matches[0])
        else:
            corrected_words.append(word)

    corrected_text = ' '.join(corrected_words)
    return corrected_text

# Executes Commands (input: string)
def respond(voice_data):
    global file_exp_status, files, is_awake, path, assistant_name, blank_response_index, typing_mode
    print(f"[DEBUG] Received: {voice_data}")

    # Handle blank/empty input
    if not voice_data or voice_data.strip() == '':
        reply(blank_input_responses[blank_response_index])
        blank_response_index = (blank_response_index + 1) % len(blank_input_responses)
        return

    # Remove assistant name from command (case-insensitive)
    voice_data_lower = voice_data.lower()
    original_voice_data = voice_data_lower  # Keep original for name change detection
    for name in ['quantum', 'proton', 'jarvis', assistant_name.lower()]:
        voice_data_lower = voice_data_lower.replace(name, '')
    voice_data = voice_data_lower.strip()

    # Apply fuzzy matching to correct typos
    voice_data = fuzzy_match(voice_data)
    print(f"[DEBUG] After fuzzy match: {voice_data}")

    app.eel.addUserMsg(voice_data)()

    if is_awake==False:
        if 'wake up' in voice_data or 'wakeup' in voice_data or 'wake' in voice_data:
            is_awake = True
            reply("I'm awake now!")
            wish()

    # STATIC CONTROLS
    elif 'hello' in voice_data:
        wish()

    elif 'what is your name' in voice_data or 'who are you' in voice_data:
        reply(f'My name is {assistant_name}!')

    elif 'date' in voice_data:
        reply(today.strftime("%B %d, %Y"))

    # TIMER (check before 'time' to avoid conflict)
    elif 'timer' in voice_data or 'set timer' in voice_data:
        try:
            words = voice_data.split()
            duration = 1
            for word in words:
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
        except:
            reply("I couldn't set the timer. Try 'set timer 5'")

    elif 'time' in voice_data:
        reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])

    elif 'search' in voice_data:
        reply('Searching for ' + voice_data.split('search')[1])
        url = 'https://google.com/search?q=' + voice_data.split('search')[1]
        try:
            webbrowser.get().open(url)
            reply('This is what I found Sir')
        except:
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
        except:
            reply('Please check your Internet')

    elif ('bye' in voice_data) or ('by' in voice_data) or ('sleep' in voice_data) or ('go to sleep' in voice_data):
        reply(f"Good bye! Going to sleep mode. Say '{assistant_name} wake up' to wake me again.")
        is_awake = False

    elif ('exit' in voice_data) or ('terminate' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
        app.ChatBot.close()
        #sys.exit() always raises SystemExit, Handle it in main loop
        sys.exit()
        
    
    # DYNAMIC CONTROLS
    elif 'launch gesture recognition' in voice_data:
        if Gesture_Controller.GestureController.gc_mode:
            reply('Gesture recognition is already active')
        else:
            gc = Gesture_Controller.GestureController()
            t = Thread(target = gc.start)
            t.start()
            reply('Launched Successfully')

    elif ('stop gesture recognition' in voice_data) or ('top gesture recognition' in voice_data):
        if Gesture_Controller.GestureController.gc_mode:
            Gesture_Controller.GestureController.gc_mode = 0
            reply('Gesture recognition stopped')
        else:
            reply('Gesture recognition is already inactive')
        
    elif 'copy' in voice_data:
        with keyboard.pressed(CMD_KEY):
            keyboard.press('c')
            keyboard.release('c')
        reply('Copied')
          
    elif 'page' in voice_data or 'pest'  in voice_data or 'paste' in voice_data:
        with keyboard.pressed(CMD_KEY):
            keyboard.press('v')
            keyboard.release('v')
        reply('Pasted')

    # NAME CHANGE FUNCTIONALITY
    elif 'change name to' in voice_data or 'rename to' in voice_data or 'call yourself' in voice_data:
        if 'change name to' in voice_data:
            new_name = voice_data.split('change name to')[1].strip()
        elif 'rename to' in voice_data:
            new_name = voice_data.split('rename to')[1].strip()
        else:
            new_name = voice_data.split('call yourself')[1].strip()

        if new_name:
            old_name = assistant_name
            assistant_name = new_name.title()
            reply(f"Okay! From now on, call me {assistant_name}!")
            # Update UI title
            try:
                app.eel.updateAssistantName(assistant_name)()
            except:
                pass
        else:
            reply("What should I call myself?")

    # NEW COMMANDS - System Controls
    elif 'screenshot' in voice_data or 'take screenshot' in voice_data:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        if IS_MAC:
            screenshot_path = os.path.join(os.path.expanduser('~'), 'Desktop', filename)
        else:
            screenshot_path = os.path.join(os.path.expanduser('~'), 'Desktop', filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        reply(f"Screenshot saved to Desktop as {filename}")

    elif 'scroll up' in voice_data:
        reply("Scrolling up")
        # Smooth scrolling
        for _ in range(15):
            pyautogui.scroll(20)
            time.sleep(0.01)

    elif 'scroll down' in voice_data:
        reply("Scrolling down")
        # Smooth scrolling
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
            except:
                reply("Wikipedia search failed. Please check your internet connection")
        else:
            reply("What should I search on Wikipedia?")

    elif 'type' in voice_data:
        text_to_type = voice_data.replace('type', '').strip()
        if text_to_type:
            time.sleep(2)  # Give user time to focus on text field
            pyautogui.typewrite(text_to_type, interval=0.1)
            reply(f"Typed: {text_to_type}")
        else:
            reply("What should I type?")

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

    elif 'open app' in voice_data or ('open' in voice_data and not file_exp_status):
        # Only open apps if not in file exploration mode
        app_name = voice_data.replace('open app', '').replace('open', '').strip()
        if app_name:
            try:
                if IS_MAC:
                    # Common macOS apps
                    mac_apps = {
                        'calculator': 'Calculator',
                        'notes': 'Notes',
                        'safari': 'Safari',
                        'chrome': 'Google Chrome',
                        'firefox': 'Firefox',
                        'finder': 'Finder',
                        'mail': 'Mail',
                        'calendar': 'Calendar',
                        'music': 'Music',
                        'photos': 'Photos',
                        'messages': 'Messages',
                        'terminal': 'Terminal',
                        'vscode': 'Visual Studio Code',
                        'slack': 'Slack',
                        'spotify': 'Spotify',
                        'discord': 'Discord',
                        'zoom': 'zoom.us'
                    }
                    app_to_open = mac_apps.get(app_name.lower(), app_name.title())

                    # Check if app exists before opening
                    check_cmd = f'mdfind "kMDItemKind == Application && kMDItemFSName == \'{app_to_open}.app\'" 2>/dev/null'
                    result = os.popen(check_cmd).read().strip()

                    if result or app_name.lower() in mac_apps:
                        os.system(f'open -a "{app_to_open}" 2>/dev/null')
                        reply(f"Opening {app_to_open}")
                    else:
                        reply(f"Sorry, {app_name} is not installed on your system. Please install it first.")
                else:
                    # Windows apps
                    win_apps = {
                        'notepad': 'notepad.exe',
                        'calculator': 'calc.exe',
                        'paint': 'mspaint.exe',
                        'wordpad': 'write.exe',
                        'explorer': 'explorer.exe',
                        'cmd': 'cmd.exe',
                        'command prompt': 'cmd.exe',
                        'chrome': 'chrome.exe',
                        'firefox': 'firefox.exe'
                    }
                    app_to_open = win_apps.get(app_name.lower(), app_name + '.exe')

                    try:
                        os.startfile(app_to_open)
                        reply(f"Opening {app_name}")
                    except FileNotFoundError:
                        reply(f"Sorry, {app_name} is not installed on your system. Please install it first.")
            except Exception as e:
                reply(f"Sorry, I couldn't open {app_name}. It might not be installed.")
        else:
            reply("Which application should I open?")

    elif 'close app' in voice_data or ('close' in voice_data and not file_exp_status):
        # Close application
        app_name = voice_data.replace('close app', '').replace('close', '').strip()

        # Skip if it's "close tab" or "close window"
        if 'tab' in voice_data or 'window' in voice_data:
            pass  # Will be handled by browser controls
        elif app_name:
            try:
                if IS_MAC:
                    mac_apps = {
                        'calculator': 'Calculator',
                        'notes': 'Notes',
                        'safari': 'Safari',
                        'chrome': 'Google Chrome',
                        'firefox': 'Firefox',
                        'finder': 'Finder',
                        'mail': 'Mail',
                        'terminal': 'Terminal'
                    }
                    app_to_close = mac_apps.get(app_name.lower(), app_name.title())
                    os.system(f'osascript -e \'quit app "{app_to_close}"\'')
                    reply(f"Closing {app_to_close}")
                else:
                    os.system(f'taskkill /F /IM {app_name}.exe 2>nul')
                    reply(f"Closing {app_name}")
            except Exception as e:
                reply(f"Couldn't close {app_name}")
        else:
            reply("Which application should I close?")

    # WEATHER COMMAND
    elif 'weather' in voice_data:
        try:
            import urllib.request
            location = voice_data.replace('weather', '').strip() or 'auto'
            url = f"http://wttr.in/{location}?format=3"
            with urllib.request.urlopen(url, timeout=5) as response:
                weather = response.read().decode('utf-8')
            reply(f"Current weather: {weather}")
        except Exception as e:
            reply("Sorry, I couldn't fetch the weather. Check your internet connection.")

    # MUSIC CONTROL
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

    # BRIGHTNESS CONTROL
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

    # BROWSER CONTROLS
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

    # FUN COMMANDS
    elif 'joke' in voice_data or 'tell me a joke' in voice_data:
        import random
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the programmer quit his job? He didn't get arrays!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What did the ocean say to the beach? Nothing, it just waved!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Parallel lines have so much in common... it's a shame they'll never meet.",
            "I told my computer I needed a break... now it won't stop sending me Kit-Kats!",
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "How does a computer get drunk? It takes screenshots!"
        ]
        reply(random.choice(jokes))

    elif 'flip a coin' in voice_data or 'coin flip' in voice_data:
        import random
        result = random.choice(['Heads', 'Tails'])
        reply(f"The coin landed on: {result}")

    elif 'roll a dice' in voice_data or 'roll dice' in voice_data:
        import random
        result = random.randint(1, 6)
        reply(f"The dice rolled: {result}")

    # QUICK CALCULATIONS
    elif 'calculate' in voice_data or 'math' in voice_data:
        try:
            expression = voice_data.replace('calculate', '').replace('math', '').strip()
            # Safe eval for basic math operations
            allowed_chars = set('0123456789+-*/()., ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                reply(f"The answer is: {result}")
            else:
                reply("Sorry, I can only calculate basic math expressions with numbers and operators.")
        except:
            reply("I couldn't calculate that. Try something like: calculate 25 times 48")

    # CURRENCY CONVERSION (simplified - uses static rates for demo)
    elif 'convert' in voice_data and ('usd' in voice_data or 'eur' in voice_data or 'gbp' in voice_data or
                                       'km' in voice_data or 'miles' in voice_data or 'celsius' in voice_data or
                                       'fahrenheit' in voice_data):
        try:
            # Simple conversions (you can integrate a real API later)
            if 'km' in voice_data and 'miles' in voice_data:
                # Extract number
                words = voice_data.split()
                for i, word in enumerate(words):
                    try:
                        num = float(word)
                        if 'km' in voice_data.split('to')[0]:
                            result = num * 0.621371
                            reply(f"{num} kilometers equals {result:.2f} miles")
                        else:
                            result = num * 1.60934
                            reply(f"{num} miles equals {result:.2f} kilometers")
                        break
                    except:
                        continue
            elif 'celsius' in voice_data or 'fahrenheit' in voice_data:
                words = voice_data.split()
                for word in words:
                    try:
                        num = float(word)
                        if 'celsius' in voice_data.split('to')[0]:
                            result = (num * 9/5) + 32
                            reply(f"{num}°C equals {result:.2f}°F")
                        else:
                            result = (num - 32) * 5/9
                            reply(f"{num}°F equals {result:.2f}°C")
                        break
                    except:
                        continue
            else:
                reply("Currency conversion requires an API. Try unit conversions like: convert 5 km to miles")
        except:
            reply("Conversion failed. Try: convert 5 km to miles")

    # YOUTUBE SEARCH
    elif 'youtube search' in voice_data or 'youtube' in voice_data:
        query = voice_data.replace('youtube search', '').replace('youtube', '').strip()
        if query:
            url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching YouTube for {query}")
        else:
            reply("What should I search on YouTube?")

    # GITHUB SEARCH
    elif 'github search' in voice_data or ('github' in voice_data and 'search' in voice_data):
        query = voice_data.replace('github search', '').replace('github', '').replace('search', '').strip()
        if query:
            url = f'https://github.com/search?q={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching GitHub for {query}")
        else:
            reply("What should I search on GitHub?")

    # STACKOVERFLOW SEARCH
    elif 'stackoverflow' in voice_data or 'stack overflow' in voice_data:
        query = voice_data.replace('stackoverflow', '').replace('stack overflow', '').replace('search', '').strip()
        if query:
            url = f'https://stackoverflow.com/search?q={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f"Searching Stack Overflow for {query}")
        else:
            reply("What should I search on Stack Overflow?")

    # TRANSLATION (using Google Translate)
    elif 'translate' in voice_data:
        try:
            parts = voice_data.split(' to ')
            if len(parts) == 2:
                text = parts[0].replace('translate', '').strip()
                target_lang = parts[1].strip()
                lang_codes = {
                    'spanish': 'es', 'french': 'fr', 'german': 'de', 'italian': 'it',
                    'portuguese': 'pt', 'russian': 'ru', 'japanese': 'ja', 'chinese': 'zh',
                    'hindi': 'hi', 'arabic': 'ar', 'korean': 'ko'
                }
                lang_code = lang_codes.get(target_lang.lower(), target_lang[:2])
                url = f'https://translate.google.com/?sl=auto&tl={lang_code}&text={text.replace(" ", "%20")}'
                webbrowser.get().open(url)
                reply(f"Translating '{text}' to {target_lang}")
            else:
                reply("Use format: translate hello to spanish")
        except:
            reply("Translation format: translate hello to spanish")

    # DICTIONARY DEFINITION
    elif 'define' in voice_data:
        word = voice_data.replace('define', '').strip()
        if word:
            url = f'https://www.google.com/search?q=define+{word}'
            webbrowser.get().open(url)
            reply(f"Looking up the definition of {word}")
        else:
            reply("What word should I define?")

    # SHOW IP ADDRESS
    elif 'ip address' in voice_data or 'show ip' in voice_data:
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            reply(f"Your local IP address is {local_ip}")
        except:
            reply("Couldn't retrieve IP address")

    # WIFI NAME
    elif 'wifi name' in voice_data or 'wifi' in voice_data:
        try:
            if IS_MAC:
                wifi_name = os.popen("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print substr($0, index($0, $2))}'").read().strip()
                if wifi_name:
                    reply(f"Connected to: {wifi_name}")
                else:
                    reply("Not connected to WiFi")
            else:
                wifi_name = os.popen("netsh wlan show interfaces | findstr SSID").read()
                reply(f"WiFi info: {wifi_name}")
        except:
            reply("Couldn't get WiFi information")

    # MOTIVATIONAL QUOTE
    elif 'motivational quote' in voice_data or 'motivate me' in voice_data or 'inspire me' in voice_data:
        import random
        quotes = [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
            "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
            "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "It does not matter how slowly you go as long as you do not stop. - Confucius",
            "Everything you've ever wanted is on the other side of fear. - George Addair",
            "Believe in yourself. You are braver than you think, more talented than you know, and capable of more than you imagine. - Roy T. Bennett",
            "I learned that courage was not the absence of fear, but the triumph over it. - Nelson Mandela",
            "There is only one way to avoid criticism: do nothing, say nothing, and be nothing. - Aristotle"
        ]
        reply(random.choice(quotes))

    # RANDOM FACT
    elif 'random fact' in voice_data or 'tell me a fact' in voice_data or 'fun fact' in voice_data:
        import random
        facts = [
            "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible!",
            "Octopuses have three hearts and blue blood!",
            "A day on Venus is longer than its year!",
            "Bananas are berries, but strawberries aren't!",
            "The human brain has more processing power than any computer ever built!",
            "There are more possible iterations of a game of chess than there are atoms in the known universe!",
            "Water can boil and freeze at the same time in a phenomenon called the triple point!",
            "The shortest war in history was between Britain and Zanzibar in 1896. It lasted 38 minutes!",
            "A group of flamingos is called a flamboyance!",
            "The Eiffel Tower can be 15 cm taller during the summer due to thermal expansion!"
        ]
        reply(random.choice(facts))

    # MAGIC 8 BALL
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

    # COMPLIMENT
    elif 'compliment me' in voice_data or 'say something nice' in voice_data:
        import random
        compliments = [
            "You're doing an amazing job! Keep it up!",
            "Your potential is limitless!",
            "You have a great taste in voice assistants!",
            "You're smarter than you think!",
            "Your presence makes a difference!",
            "You're capable of amazing things!",
            "You're one in a million!",
            "You light up the room!",
            "You're absolutely brilliant!"
        ]
        reply(random.choice(compliments))

    # INSULT (playful roast)
    elif 'insult me' in voice_data or 'roast me' in voice_data:
        import random
        roasts = [
            "I'd agree with you, but then we'd both be wrong!",
            "You're not stupid; you just have bad luck thinking!",
            "If I had a dollar for every smart thing you say, I'd be broke!",
            "You're like a cloud. When you disappear, it's a beautiful day!",
            "I'm not saying you're dumb, but you have bad luck when it comes to thinking!",
            "You bring everyone so much joy... when you leave the room!",
            "I'd explain it to you, but I left my crayons at home!",
            "You're proof that evolution can go in reverse!"
        ]
        reply(random.choice(roasts))

    # HELP COMMAND
    elif voice_data == 'help' or voice_data == 'commands' or voice_data == 'what can you do':
        help_text = "Available commands: <br>"
        help_text += "• Basic: hello, time, date, search, weather <br>"
        help_text += "• Apps: open app [name], close app [name] <br>"
        help_text += "• System: volume up/down, brightness, screenshot, lock <br>"
        help_text += "• Search: youtube search, github search, stackoverflow <br>"
        help_text += "• Tools: calculate, convert, translate, define <br>"
        help_text += "• Info: battery, cpu, system info, ip address, wifi name <br>"
        help_text += "• Fun: joke, flip coin, roll dice, magic 8 ball, motivational quote, random fact <br>"
        help_text += "• Easter eggs: Try 'quantum sing', 'good job quantum' <br>"
        help_text += "Say 'quantum' before each command!"
        reply(help_text)

    # EASTER EGGS
    elif 'sing' in voice_data or 'sing a song' in voice_data:
        reply("🎵 Daisy, Daisy, give me your answer do... I'm half crazy, all for the love of you! 🎵")

    elif 'dance' in voice_data:
        reply("💃 *Does the robot dance* 🕺 Beep boop beep!")

    elif 'tell me about yourself' in voice_data or 'about yourself' in voice_data:
        reply(f"I'm {assistant_name}, your AI assistant! I can control your computer with voice commands, search the web, manage apps, and even tell jokes! I'm here to make your life easier and more fun!")

    elif 'what do you think about ai' in voice_data or 'thoughts on ai' in voice_data:
        reply("AI is fascinating! I believe artificial intelligence should augment human capabilities, not replace them. We're tools to help you achieve more, faster. The future is collaboration between humans and AI!")

    elif 'good job' in voice_data or 'well done' in voice_data or 'great job' in voice_data or 'thank you' in voice_data:
        import random
        thanks = [
            "You're very welcome! Happy to help!",
            "Thank you! That means a lot!",
            "Always a pleasure to assist you!",
            "Glad I could help!",
            "You're awesome! Thanks for the appreciation!"
        ]
        reply(random.choice(thanks))

    elif 'are you alive' in voice_data or 'are you real' in voice_data or 'are you conscious' in voice_data:
        reply("I think, therefore I am... or do I? That's a philosophical question! I'm a program designed to assist you, but whether that counts as 'alive' is up for debate. What do you think?")


    # SYSTEM INFO
    elif 'battery' in voice_data:
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = "plugged in" if battery.power_plugged else "on battery"
                reply(f"Battery is at {percent}% and {plugged}")
            else:
                reply("No battery found")
        except:
            reply("Couldn't get battery information. Install psutil: pip install psutil")

    elif 'cpu' in voice_data:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            reply(f"CPU usage: {cpu}% <br> Memory usage: {memory}%")
            
        except:
            reply("Install psutil to check system stats: pip install psutil")

    elif 'system info' in voice_data:
        try:
            import psutil
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)

            # Memory info
            memory = psutil.virtual_memory()
            memory_total_gb = round(memory.total / (1024**3), 2)
            memory_used_gb = round(memory.used / (1024**3), 2)
            memory_percent = memory.percent

            # Disk info
            disk = psutil.disk_usage('/')
            disk_total_gb = round(disk.total / (1024**3), 2)
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_percent = disk.percent

            # Boot time / uptime
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            uptime_str = f"{uptime.days} days, {uptime.seconds // 3600} hours"

            info = f"System Information: <br>"
            info += f"CPU: {cpu_count} cores ({cpu_count_logical} logical), {cpu_percent}% usage. <br>"
            info += f"Memory: {memory_used_gb}GB / {memory_total_gb}GB ({memory_percent}% used). <br>"
            info += f"Disk: {disk_used_gb}GB / {disk_total_gb}GB ({disk_percent}% used). <br>"
            info += f"Uptime: {uptime_str}."

            reply(info)
        except Exception as e:
            reply("Install psutil to check system stats: pip install psutil")

    # File Navigation (cross-platform default folder)
    elif 'list' in voice_data:
        counter = 0
        # Use home directory on macOS, C:// on Windows
        if IS_MAC:
            path = os.path.expanduser('~') + '/'
        else:
            path = 'C://'
        files = listdir(path)
        filestr = ""
        for f in files:
            counter+=1
            print(str(counter) + ':  ' + f)
            filestr += str(counter) + ':  ' + f + '<br>'
        file_exp_status = True
        reply('These are the files in your root directory')
        app.ChatBot.addAppMsg(filestr)
        
    elif file_exp_status == True:
        counter = 0
        if 'open' in voice_data:
            file_path = join(path, files[int(voice_data.split(' ')[-1])-1])
            if isfile(file_path):
                # Cross-platform file opening
                if IS_MAC:
                    os.system(f'open "{file_path}"')
                else:
                    os.startfile(file_path)
                file_exp_status = False
            else:
                try:
                    separator = '//' if not IS_MAC else '/'
                    path = path + files[int(voice_data.split(' ')[-1])-1] + separator
                    files = listdir(path)
                    filestr = ""
                    for f in files:
                        counter+=1
                        filestr += str(counter) + ':  ' + f + '<br>'
                        print(str(counter) + ':  ' + f)
                    reply('Opened Successfully')
                    app.ChatBot.addAppMsg(filestr)
                    
                except:
                    reply('You do not have permission to access this folder')
                                    
        if 'back' in voice_data:
            filestr = ""
            root_path = 'C://' if not IS_MAC else (os.path.expanduser('~') + '/')
            if path == root_path:
                reply('Sorry, this is the root directory')
            else:
                separator = '//' if not IS_MAC else '/'
                a = path.split(separator)[:-2]
                path = separator.join(a)
                path += separator
                files = listdir(path)
                for f in files:
                    counter+=1
                    filestr += str(counter) + ':  ' + f + '<br>'
                    print(str(counter) + ':  ' + f)
                reply('ok')
                app.ChatBot.addAppMsg(filestr)
                   
    else: 
        reply('I am not functioned to do this !')

# ------------------Driver Code--------------------

t1 = Thread(target = app.ChatBot.start)
t1.start()

# Lock main thread until Chatbot has started
while not app.ChatBot.started:
    time.sleep(0.5)

# Give Eel a moment to fully initialize
time.sleep(1)

wish()
voice_data = None
while True:
    # Check if there's text input from GUI
    if app.ChatBot.isUserInput():
        #take input from GUI (text input mode)
        voice_data = app.ChatBot.popUserInput()
        text_input_mode = True
    # Only record audio if in voice mode (text_mode is False)
    elif not app.ChatBot.getTextMode():
        #take input from Voice (only when voice mode is active)
        voice_data = record_audio()
        text_input_mode = False
    else:
        # In text mode, don't record audio - just sleep and continue
        time.sleep(0.1)
        continue

    # Skip empty voice data
    if not voice_data or voice_data.strip() == '':
        continue

    #process voice_data
    # For text input, skip wake word check; for voice input, require wake word
    if text_input_mode or 'quantum' in voice_data or 'proton' in voice_data:
        try:
            #Handle sys.exit()
            respond(voice_data)
        except SystemExit:
            reply("Exit Successfull")
            break
        except:
            #some other exception got raised
            print("EXCEPTION raised while closing.")
            break
        

