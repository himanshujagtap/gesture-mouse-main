# ADD THESE NEW COMMANDS TO Quantum.py AFTER THE EXISTING COMMANDS
# Insert after the 'open' command and before 'File Navigation'

# Additional suggested features - add these to Quantum.py

# WEATHER COMMAND
elif 'weather' in voice_data:
    try:
        # Using wttr.in - no API key needed
        import urllib.request
        import json
        location = voice_data.replace('weather', '').strip() or 'auto'
        url = f"http://wttr.in/{location}?format=3"
        with urllib.request.urlopen(url) as response:
            weather = response.read().decode('utf-8')
        reply(f"Current weather: {weather}")
    except Exception as e:
        reply("Sorry, I couldn't fetch the weather. Check your internet connection.")

# MUSIC CONTROL
elif 'play music' in voice_data or 'pause music' in voice_data or 'play' in voice_data or 'pause' in voice_data:
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
    import random
    reply(random.choice(jokes))

elif 'flip a coin' in voice_data or 'coin flip' in voice_data:
    import random
    result = random.choice(['Heads', 'Tails'])
    reply(f"The coin landed on: {result}")

elif 'roll a dice' in voice_data or 'roll dice' in voice_data:
    import random
    result = random.randint(1, 6)
    reply(f"The dice rolled: {result}")

# TIMER
elif 'timer' in voice_data or 'set timer' in voice_data:
    try:
        # Extract duration in minutes
        words = voice_data.split()
        duration = 1  # default
        for i, word in enumerate(words):
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
                os.system(f'msg * Timer of {minutes} minutes is complete')

        from threading import Thread
        timer_thread = Thread(target=timer_alert, args=(duration,))
        timer_thread.daemon = True
        timer_thread.start()
    except:
        reply("I couldn't set the timer. Please specify duration like 'set timer 5 minutes'")

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
        reply("Couldn't get battery information")

elif 'cpu' in voice_data or 'memory' in voice_data:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        reply(f"CPU usage: {cpu}%, Memory usage: {memory}%")
    except:
        reply("Install psutil to check system stats: pip install psutil")
