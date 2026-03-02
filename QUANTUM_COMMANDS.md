# 🎯 Quantum Voice Commands - Complete Reference

> **Note:** After changing Quantum's name, use the new name for all commands!
> Example: `quantum change name to jarvis` → Now use `jarvis [command]`

---

## 🔧 Basic Commands

| Command | What it does |
|---------|--------------|
| **quantum hello** | Greet Quantum |
| **quantum what is your name** | Quantum tells you its name |
| **quantum who are you** | Same as above |
| **quantum time** | Get current time (format: "13 hours 23 minutes and 23 seconds") |
| **quantum date** | Get today's date |
| **quantum search [query]** | Google search |

---

## 🎭 Name Change

| Command | Examples |
|---------|----------|
| **quantum change name to [name]** | `change name to jarvis` |
| **quantum rename to [name]** | `rename to friday` |
| **quantum call yourself [name]** | `call yourself cortana` |

**After renaming:**
- UI title updates automatically ✨
- All future commands use the new name
- Example: `jarvis hello`, `friday time`, etc.

---

## 🖥️ System Controls

### Window Management
| Command | What it does |
|---------|--------------|
| **quantum minimize** | Minimize window (⌘M on Mac / Win+D on Windows) |
| **quantum maximize** | Maximize window |
| **quantum close window** | Close current window (⌘W / Alt+F4) |
| **quantum lock** | Lock screen |

### Screenshot & Display
| Command | What it does |
|---------|--------------|
<!-- | **quantum screenshot** | Take screenshot (saved to Desktop with timestamp) | -->
| **quantum scroll up** | Smooth scroll up |
| **quantum scroll down** | Smooth scroll down |
| **quantum brightness up** | Increase screen brightness |
| **quantum brightness down** | Decrease screen brightness |

### Audio Controls
| Command | What it does |
|---------|--------------|
| **quantum volume up** | Increase volume |
| **quantum volume down** | Decrease volume |
| **quantum mute** | Toggle mute/unmute |

---

## 📱 Application Control

### Open Applications
| Command | What it does |
|---------|--------------|
| **quantum open calculator** | Open Calculator |
| **quantum open notes** | Open Notes (Mac) / Notepad (Windows) |
| **quantum open safari** | Open Safari (Mac) |
| **quantum open chrome** | Open Chrome |
| **quantum open firefox** | Open Firefox |
| **quantum open mail** | Open Mail app |
| **quantum open finder** | Open Finder (Mac) |
| **quantum open terminal** | Open Terminal (Mac) |
| **quantum open settings** | Open System Settings |
| **quantum open vscode** | Open Visual Studio Code |
| **quantum open slack** | Open Slack |
| **quantum open spotify** | Open Spotify |
| **quantum open discord** | Open Discord |
| **quantum open zoom** | Open Zoom |
| **quantum open [any app]** | Try to open any installed app |

### Close Applications
| Command | What it does |
|---------|--------------|
| **quantum close calculator** | Close specific app |
| **quantum close chrome** | Close Chrome |
| **quantum close [app name]** | Close any running app |
| **quantum close window** | Close current window |

*If app name not found, shows error message*

---

## 🌐 Browser Controls

| Command | What it does |
|---------|--------------|
| **quantum new tab** | Open new browser tab (⌘T / Ctrl+T) |
| **quantum close tab** | Close current tab (⌘W / Ctrl+W) |
| **quantum incognito** | Open incognito/private window (⌘⇧N / Ctrl+Shift+N) |
| **quantum refresh** | Refresh current page (⌘R / Ctrl+R) |
| **quantum reload** | Same as refresh |

---

## 📝 Text & Input

| Command | What it does |
|---------|--------------|
| **quantum type hello world** | Type text (waits 2s for focus) |
| **quantum copy** | Copy selection (⌘C / Ctrl+C) |
| **quantum paste** | Paste (⌘V / Ctrl+V) |

---

## 📚 Information & Search

| Command | What it does |
|---------|--------------|
| **quantum wikipedia python** | Search Wikipedia for "python" (2 sentence summary) |
| **quantum wikipedia [topic]** | Get Wikipedia summary of any topic |
| **quantum weather** | Get current weather for your location |
| **quantum weather [city]** | Get weather for specific city |

---

## 🎵 Music Controls

| Command | What it does |
|---------|--------------|
| **quantum play music** | Play/pause music |
| **quantum pause music** | Toggle play/pause |
| **quantum next song** | Skip to next track |
| **quantum next track** | Same as above |
| **quantum previous song** | Go to previous track |
| **quantum previous track** | Same as above |

---

## 👆 Gesture Recognition

| Command | What it does |
|---------|--------------|
| **quantum launch gesture recognition** | Start hand gesture control |
| **quantum stop gesture recognition** | Stop gesture control |

### Gesture Controls (once launched):
- ✌️ **V gesture (peace sign)** - Move cursor
- ✊ **Fist** - Click and drag
- 🤏 **Pinch (minor hand)** - Scroll
- 🖕 **Middle finger up** - Left click
- ☝️ **Index finger up** - Right click
- 🤞 **Two fingers closed** - Double click

---

## 🎮 Fun & Utility

| Command | What it does |
|---------|--------------|
| **quantum joke** | Tell a random joke |
| **quantum tell me a joke** | Same as above |
| **quantum flip a coin** | Flip a coin (Heads or Tails) |
| **quantum roll a dice** | Roll a dice (1-6) |
| **quantum timer [minutes]** | Set a timer (e.g., "timer 5") |
| **quantum set timer 10** | Set 10 minute timer |

---

## 🔋 System Information

| Command | What it does |
|---------|--------------|
| **quantum battery** | Check battery percentage and charging status |
| **quantum cpu** | Check CPU and memory usage |
| **quantum system info** | Same as CPU command |

*Requires psutil: `pip install psutil`*

---

## 💤 Sleep/Wake/Exit

| Command | What it does |
|---------|--------------|
| **quantum sleep** | Put Quantum to sleep mode |
| **quantum go to sleep** | Same as above |
| **quantum wake up** | Wake Quantum from sleep |
| **quantum wake** | Same as wake up |
| **quantum exit** | Close Quantum completely |
| **quantum quit** | Same as exit |
| **quantum terminate** | Same as exit |o

*Note: "bye" changed to "sleep" for better voice recognition*

---

## 📂 File Navigation

| Command | What it does |
|---------|--------------|
| **quantum list** | List files in home directory (Mac) / C:// (Windows) |
| **quantum open [number]** | Open file by number from list |
| **quantum back** | Go back to parent directory |


## 📋 Updated Command Syntax

### App Management
```bash
# Opening apps
open app calculator    # Opens calculator
open app chrome       # Opens Chrome (shows error if not installed)
open app safari       # Opens Safari
open app terminal     # Opens Terminal

# Closing apps
close app calculator  # Closes calculator
close app chrome      # Closes Chrome
close app safari      # Closes Safari
```

### File Navigation
```bash
list                  # Show files in home directory
open 25              # Open folder #25 from list
back                 # Go back to parent directory
```

### Timer vs Time
```bash
time                 # Shows current time
set timer 5          # Sets 5 minute timer
timer 10             # Sets 10 minute timer
```

### System Info
```bash
cpu                  # Simple: CPU and memory usage
system info          # Detailed: CPU, memory, disk, uptime
battery              # Battery percentage and status
```

### Sleep/Wake
```bash
sleep                # Put Quantum to sleep
go to sleep          # Same as above
wake up              # Wake Quantum from sleep
```

# 🎉 New Commands Added to Quantum!

## 📊 Quick Calculations & Conversions

### Calculate
```bash
calculate 25 * 48          # Math: 1200
calculate 100 / 5          # Division: 20
calculate 15 + 30          # Addition: 45
math 50 - 12              # Subtraction: 38
```

### Unit Conversions
```bash
convert 5 km to miles      # 5 km = 3.11 miles
convert 10 miles to km     # 10 miles = 16.09 km
convert 25 celsius to fahrenheit    # 25°C = 77°F
convert 98 fahrenheit to celsius    # 98°F = 36.67°C
```

---

## 🌐 Enhanced Web Searches

### YouTube Search
```bash
youtube search python tutorials
youtube search funny cats
youtube how to cook pasta
```

### GitHub Search
```bash
github search react hooks
github search machine learning
github python projects
```

### Stack Overflow
```bash
stackoverflow python list comprehension
stackoverflow javascript promises
stackoverflow how to reverse a string
```

### Translation
```bash
translate hello to spanish    # Opens Google Translate
translate good morning to french
translate thank you to japanese
```
**Supported languages:** Spanish, French, German, Italian, Portuguese, Russian, Japanese, Chinese, Hindi, Arabic, Korean

### Dictionary
```bash
define quantum               # Opens Google definition
define serendipity
define ephemeral
```

---

## 🔍 System Information

### Network Info
```bash
ip address                   # Shows your local IP
show ip                      # Same as above
wifi name                    # Shows connected WiFi network
```

---

## 🎮 Fun & Entertainment

### Motivational Quotes
```bash
motivational quote
inspire me
motivate me
```
**Sample quotes:**
- "The only way to do great work is to love what you do. - Steve Jobs"
- "Believe you can and you're halfway there. - Theodore Roosevelt"
- 10 rotating quotes!

### Random Facts
```bash
random fact
tell me a fact
fun fact
```
**Sample facts:**
- "Honey never spoils. Archaeologists have found 3000-year-old honey!"
- "Octopuses have three hearts and blue blood!"
- 10 interesting facts!

### Magic 8 Ball
```bash
magic 8 ball will I succeed?
magic 8 ball should I do it?
magic eight ball am I awesome?
```
**Responses:** 20 classic Magic 8-Ball answers!

### Compliments & Roasts
```bash
compliment me               # Get a nice compliment
say something nice          # Random compliment
insult me                   # Playful roast (not mean!)
roast me                    # Funny insult
```

---

## ❓ Help Command

```bash
help                        # Shows all available commands
commands                    # Same as above
what can you do             # Lists capabilities
```

**Output includes:**
- Basic commands
- App management
- System controls
- Search tools
- Fun commands
- Easter eggs

---

## 🎭 Easter Eggs & Personality

### Quantum's Personality
```bash
quantum sing                # Quantum sings a song! 🎵
quantum dance               # Robot dance! 💃🕺
quantum tell me about yourself    # Quantum's backstory
quantum what do you think about ai    # Quantum's thoughts on AI
quantum are you alive       # Philosophical response
quantum are you real
quantum are you conscious
```

### Appreciation
```bash
good job quantum           # Quantum thanks you
great job                  # Random thank you response
well done                  # Appreciation
thank you                  # You're welcome!
```

**5 rotating thank you responses!**

---

## 📋 Complete Command List

### Quick Reference

| Category | Commands |
|----------|----------|
| **Math** | calculate, math |
| **Conversion** | convert [value] [unit] to [unit] |
| **Search** | youtube search, github search, stackoverflow |
| **Translation** | translate [text] to [language] |
| **Dictionary** | define [word] |
| **Network** | ip address, show ip, wifi name |
| **Fun** | motivational quote, random fact, magic 8 ball |
| **Social** | compliment me, insult me |
| **Help** | help, commands, what can you do |
| **Easter Eggs** | sing, dance, tell me about yourself, good job |

---

## 🎯 Usage Examples

### Productivity
```bash
# Quick calculations while working
calculate 1500 * 0.15
convert 5 km to miles
translate hello to spanish
define algorithm
```

### Development
```bash
# Search for solutions
stackoverflow react hooks
github search machine learning
youtube search python tutorial
```

### Fun Break
```bash
# Take a quick break
motivational quote
random fact
magic 8 ball should I take a break?
compliment me
joke
```

### Information
```bash
# Quick info
ip address
wifi name
weather
battery
cpu
```



Enjoy your enhanced AI assistant! 🚀