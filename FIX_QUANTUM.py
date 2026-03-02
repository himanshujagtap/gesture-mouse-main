"""
COMPREHENSIVE FIXES FOR QUANTUM.PY
Apply these changes to fix all reported issues
"""

# ====================
# FIX 1: Add typing mode state variable
# Add after line 69 (after blank_response_index = 0)
# ====================
typing_mode = False  # Typing mode state

# ====================
# FIX 2: Fix screenshot command
# Replace the existing screenshot command with this:
# ====================
"""
elif 'screenshot' in voice_data or 'take screenshot' in voice_data or 'screen shot' in voice_data:
    try:
        import time as time_module
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')

        # Ensure Desktop exists
        if not os.path.exists(desktop_path):
            os.makedirs(desktop_path)

        screenshot_path = os.path.join(desktop_path, filename)

        # Take screenshot
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        reply(f"Screenshot saved to Desktop as {filename}")
    except Exception as e:
        reply(f"Failed to take screenshot. Error: {str(e)}")
        print(f"Screenshot error: {e}")
"""

# ====================
# FIX 3: Fix time format
# Replace the existing time command with this:
# ====================
"""
elif 'time' in voice_data or 'what time' in voice_data:
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    reply(f"{hour} hours {minute} minutes and {second} seconds")
"""

# ====================
# FIX 4: Add separate unmute command
# Add after the mute command:
# ====================
"""
elif 'unmute' in voice_data and 'mute' not in voice_data.replace('unmute', ''):
    if IS_MAC:
        os.system("osascript -e 'set volume output muted false'")
    else:
        # Windows doesn't have separate unmute, use toggle
        pyautogui.press('volumemute')
    reply("Unmuted")

elif 'mute' in voice_data and 'unmute' not in voice_data:
    if IS_MAC:
        os.system("osascript -e 'set volume output muted true'")
    else:
        pyautogui.press('volumemute')
    reply("Muted")
"""

# ====================
# FIX 5: Fix close app with better error handling
# Replace the close app section with:
# ====================
"""
elif 'close' in voice_data and 'tab' not in voice_data and 'window' not in voice_data:
    app_name = voice_data.replace('close', '').strip()
    if app_name:
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
                    'calendar': 'Calendar',
                    'music': 'Music',
                    'photos': 'Photos',
                    'messages': 'Messages',
                    'terminal': 'Terminal',
                    'preview': 'Preview',
                    'xcode': 'Xcode',
                    'vscode': 'Visual Studio Code',
                    'code': 'Visual Studio Code',
                    'slack': 'Slack',
                    'spotify': 'Spotify',
                    'discord': 'Discord',
                    'whatsapp': 'WhatsApp',
                    'zoom': 'zoom.us',
                    'teams': 'Microsoft Teams'
                }
                app_to_close = mac_apps.get(app_name.lower(), app_name.title())
                result = os.system(f'osascript -e \'quit app "{app_to_close}"\' 2>/dev/null')
                if result == 0:
                    reply(f"Closed {app_to_close}")
                else:
                    reply(f"Couldn't close {app_name}. Make sure it's running.")
            else:
                os.system(f'taskkill /f /im {app_name}.exe 2>nul')
                reply(f"Closing {app_name}")
        except Exception as e:
            reply(f"Couldn't close {app_name}")
    else:
        # Close current window
        if IS_MAC:
            pyautogui.hotkey('command', 'w')
        else:
            pyautogui.hotkey('alt', 'f4')
        reply("Closing current window")
"""

# ====================
# FIX 6: Enhanced open app with better error messages
# Replace the open app section with:
# ====================
"""
elif 'open' in voice_data:
    app_name = voice_data.replace('open', '').strip()
    if app_name:
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
                    'calendar': 'Calendar',
                    'music': 'Music',
                    'photos': 'Photos',
                    'messages': 'Messages',
                    'terminal': 'Terminal',
                    'settings': 'System Settings',
                    'app store': 'App Store',
                    'facetime': 'FaceTime',
                    'preview': 'Preview',
                    'xcode': 'Xcode',
                    'vscode': 'Visual Studio Code',
                    'code': 'Visual Studio Code',
                    'slack': 'Slack',
                    'spotify': 'Spotify',
                    'discord': 'Discord',
                    'whatsapp': 'WhatsApp',
                    'zoom': 'zoom.us',
                    'teams': 'Microsoft Teams',
                    'word': 'Microsoft Word',
                    'excel': 'Microsoft Excel',
                    'powerpoint': 'Microsoft PowerPoint'
                }
                app_to_open = mac_apps.get(app_name.lower(), app_name.title())

                # Try to open the app
                result = os.system(f'open -a "{app_to_open}" 2>/dev/null')

                if result == 0:
                    reply(f"Opening {app_to_open}")
                else:
                    # App not found
                    reply(f"Sorry, I don't have {app_name} installed on this Mac. Please install it first from the App Store or download it.")
            else:
                win_apps = {
                    'notepad': 'notepad.exe',
                    'calculator': 'calc.exe',
                    'paint': 'mspaint.exe',
                    'wordpad': 'write.exe',
                    'explorer': 'explorer.exe',
                    'cmd': 'cmd.exe',
                    'command prompt': 'cmd.exe'
                }
                app_to_open = win_apps.get(app_name.lower(), app_name + '.exe')
                try:
                    os.startfile(app_to_open)
                    reply(f"Opening {app_name}")
                except:
                    reply(f"Sorry, I couldn't find {app_name}. Make sure it's installed.")
        except Exception as e:
            reply(f"Sorry, I don't have {app_name} installed.")
    else:
        reply("Which application should I open?")
"""

# ====================
# FIX 7: Add Typing Mode
# Add this new command section:
# ====================
"""
# TYPING MODE
elif 'typing mode' in voice_data or 'open typing mode' in voice_data:
    global typing_mode
    typing_mode = True
    reply("Typing mode activated. I will type everything you say. Say 'close typing mode' to exit.")

elif typing_mode and ('close typing mode' in voice_data or 'quit typing mode' in voice_data or 'exit typing mode' in voice_data):
    typing_mode = False
    reply("Typing mode closed")

elif typing_mode:
    # In typing mode, type everything said
    text_to_type = voice_data.strip()
    if text_to_type:
        try:
            pyautogui.typewrite(text_to_type, interval=0.05)
            # Don't reply in typing mode to avoid interruption
        except:
            # If typewrite fails, try write (for non-ASCII)
            pyautogui.write(text_to_type, interval=0.05)
"""

# ====================
# FIX 8: Use Joke API
# Replace the joke command with:
# ====================
"""
elif 'joke' in voice_data or 'tell me a joke' in voice_data:
    try:
        import urllib.request
        import json

        req = urllib.request.Request(
            'https://icanhazdadjoke.com/',
            headers={'Accept': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            joke = data.get('joke', 'I forgot the joke!')
            reply(joke)
    except Exception as e:
        # Fallback jokes if API fails
        import random
        fallback_jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the programmer quit his job? He didn't get arrays!",
            "How does a computer get drunk? It takes screenshots!"
        ]
        reply(random.choice(fallback_jokes))
"""

# ====================
# FIX 9: Fix name change to work properly
# The issue is that assistant_name needs to be declared global in respond()
# Make sure this line is at the top of respond() function:
# ====================
"""
def respond(voice_data):
    global file_exp_status, files, is_awake, path, assistant_name, blank_response_index, typing_mode
"""

print("""
All fixes documented in this file.
Apply these changes to Quantum.py to fix all reported issues.

Key changes:
1. Added typing mode state
2. Fixed screenshot with better error handling
3. Fixed time format
4. Separated mute/unmute commands
5. Fixed close app with error checking
6. Enhanced open app with custom "not installed" messages
7. Added typing mode functionality
8. Using joke API instead of hardcoded jokes
9. Fixed name change by adding global variable
""")
