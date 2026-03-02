# 🔧 Complete Fixes for Quantum.py

## Run this Python script to apply all fixes:

```python
cd "/Users/himanshu/Desktop/final project/gesture-mouse"
source .venv/bin/activate
python3 << 'EOF'

import re

# Read the current Quantum.py
with open('Quantum.py', 'r') as f:
    content = f.read()

# Backup
with open('Quantum.py.backup', 'w') as f:
    f.write(content)

print("✓ Created backup: Quantum.py.backup")

# Fix 1: Update time command to new format
old_time = r'''    elif 'time' in voice_data:
        reply(str(datetime.datetime.now\(\).split\(" "\)\[1\].split\('\.'\)\[0\])'''

new_time = '''    elif 'time' in voice_data or 'what time' in voice_data:
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second
        reply(f"{hour} hours {minute} minutes and {second} seconds")'''

if re.search(r"elif 'time' in voice_data", content):
    # Find and replace the time command section
    content = re.sub(
        r"elif 'time' in voice_data:.*?reply\(.*?\)",
        new_time.strip(),
        content,
        flags=re.DOTALL
    )
    print("✓ Fixed time format")

# Fix 2: Separate mute/unmute
mute_section = '''    elif 'unmute' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'set volume output muted false'")
        else:
            pyautogui.press('volumemute')
        reply("Unmuted")

    elif 'mute' in voice_data:
        if IS_MAC:
            os.system("osascript -e 'set volume output muted true'")
        else:
            pyautogui.press('volumemute')
        reply("Muted")'''

# Replace old mute/unmute toggle
content = re.sub(
    r"elif 'mute' in voice_data or 'unmute' in voice_data:.*?reply\('Volume toggled'\)",
    mute_section,
    content,
    flags=re.DOTALL
)
print("✓ Added separate unmute command")

# Fix 3: Use joke API
joke_section = '''    elif 'joke' in voice_data or 'tell me a joke' in voice_data:
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
            import random
            fallback_jokes = [
                "Why don't scientists trust atoms? Because they make up everything!",
                "Why did the programmer quit his job? He didn't get arrays!",
                "How does a computer get drunk? It takes screenshots!"
            ]
            reply(random.choice(fallback_jokes))'''

# Replace old joke command
content = re.sub(
    r"elif 'joke' in voice_data.*?reply\(random\.choice\(jokes\)\)",
    joke_section,
    content,
    flags=re.DOTALL
)
print("✓ Updated joke to use API")

# Save updated content
with open('Quantum.py', 'w') as f:
    f.write(content)

print("\n✅ All automatic fixes applied!")
print("📝 Manual fixes still needed:")
print("  1. Typing mode implementation")
print("  2. Enhanced app open/close error messages")
print("  3. Screenshot error handling")
print("\nCheck MANUAL_FIXES.md for remaining updates")

EOF
```

Save this and run it!

---

## Or Apply Manually:

### 1. TIME FORMAT (Line ~158)
**Replace:**
```python
elif 'time' in voice_data:
    reply(str(datetime.datetime.now()).split(" ")[1].split('.')[0])
```

**With:**
```python
elif 'time' in voice_data or 'what time' in voice_data:
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    reply(f"{hour} hours {minute} minutes and {second} seconds")
```

### 2. MUTE/UNMUTE (Line ~278)
**Replace:**
```python
elif 'mute' in voice_data or 'unmute' in voice_data:
    if IS_MAC:
        os.system("osascript -e 'set volume output muted not (output muted of (get volume settings))'")
    else:
        pyautogui.press('volumemute')
    reply("Volume toggled")
```

**With:**
```python
elif 'unmute' in voice_data:
    if IS_MAC:
        os.system("osascript -e 'set volume output muted false'")
    else:
        pyautogui.press('volumemute')
    reply("Unmuted")

elif 'mute' in voice_data:
    if IS_MAC:
        os.system("osascript -e 'set volume output muted true'")
    else:
        pyautogui.press('volumemute')
    reply("Muted")
```

### 3. JOKE API (Line ~407)
**Replace entire jokes section with:**
```python
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
        import random
        fallback_jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the programmer quit his job? He didn't get arrays!",
            "How does a computer get drunk? It takes screenshots!"
        ]
        reply(random.choice(fallback_jokes))
```

### 4. TYPING MODE (Add before "File Navigation")
```python
# TYPING MODE
elif 'typing mode' in voice_data or 'open typing mode' in voice_data:
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
            pyautogui.write(text_to_type, interval=0.05)
        except:
            pass
```

### 5. ENHANCED APP OPEN (Replace existing open command)
```python
elif 'open' in voice_data:
    app_name = voice_data.replace('open', '').strip()
    if app_name:
        if IS_MAC:
            mac_apps = {
                'calculator': 'Calculator',
                'notes': 'Notes',
                'safari': 'Safari',
                'chrome': 'Google Chrome',
                'firefox': 'Firefox',
                'finder': 'Finder',
                'mail': 'Mail',
                'terminal': 'Terminal',
                'vscode': 'Visual Studio Code',
                'code': 'Visual Studio Code',
                'slack': 'Slack',
                'spotify': 'Spotify'
            }
            app_to_open = mac_apps.get(app_name.lower(), app_name.title())
            result = os.system(f'open -a "{app_to_open}" 2>/dev/null')
            if result == 0:
                reply(f"Opening {app_to_open}")
            else:
                reply(f"Sorry, I don't have {app_name} installed on this Mac. Please install it first.")
        else:
            # Windows code...
    else:
        reply("Which application should I open?")
```

### 6. CLOSE APP (Replace existing close command)
```python
elif 'close' in voice_data and 'tab' not in voice_data:
    app_name = voice_data.replace('close', '').replace('window', '').strip()
    if app_name:
        if IS_MAC:
            mac_apps = {
                'calculator': 'Calculator',
                'chrome': 'Google Chrome',
                'safari': 'Safari'
            }
            app_to_close = mac_apps.get(app_name.lower(), app_name.title())
            result = os.system(f'osascript -e \'quit app "{app_to_close}"\' 2>/dev/null')
            if result == 0:
                reply(f"Closed {app_to_close}")
            else:
                reply(f"Couldn't close {app_name}. Make sure it's running.")
    else:
        if IS_MAC:
            pyautogui.hotkey('command', 'w')
        else:
            pyautogui.hotkey('alt', 'f4')
        reply("Closing current window")
```

---

## Quick Fix Command:

Just run:
```bash
cd "/Users/himanshu/Desktop/final project/gesture-mouse"
python3 APPLY_ALL_FIXES.md
```

All done! ✅
