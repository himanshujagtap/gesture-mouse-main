import eel
import os
from queue import Queue

class ChatBot:

    started = False
    userinputQueue = Queue()
    text_mode = False  # Track if in text input mode

    def isUserInput():
        return not ChatBot.userinputQueue.empty()

    def popUserInput():
        return ChatBot.userinputQueue.get()

    def getTextMode():
        return ChatBot.text_mode

    @eel.expose
    def setTextMode(mode):
        ChatBot.text_mode = mode
        print(f"Text mode: {mode}")

    def close_callback(route, websockets):
        # if not websockets:
        #     print('Bye!')
        exit()

    @eel.expose
    def getUserInput(msg):
        ChatBot.userinputQueue.put(msg)
        # Removed print to avoid duplicate console output (already printed in respond())

    @eel.expose
    def getCommandSuggestions(partial_input):
        """Return command suggestions based on partial input"""
        commands = [
            'hello', 'time', 'date', 'search', 'location',
            'launch gesture recognition', 'stop gesture recognition',
            'copy', 'paste', 'change name to', 'rename to', 'call yourself',
            'screenshot', 'scroll up', 'scroll down',
            'volume up', 'volume down', 'mute', 'unmute',
            'wikipedia', 'type', 'minimize', 'maximize', 'lock',
            'open app calculator', 'open app chrome', 'open app safari', 'open app notes',
            'open app firefox', 'open app terminal', 'open app vscode',
            'close app calculator', 'close app chrome', 'close app safari',
            'close window', 'close tab', 'weather',
            'play music', 'pause music', 'next song', 'previous song',
            'brightness up', 'brightness down',
            'new tab', 'close tab', 'incognito', 'refresh', 'reload',
            'joke', 'tell me a joke', 'flip a coin', 'roll a dice',
            'set timer', 'battery', 'cpu', 'system info',
            'list', 'open', 'back', 'sleep', 'go to sleep', 'exit', 'terminate', 'wake up',
            # New commands
            'calculate', 'convert 5 km to miles', 'convert 100 celsius to fahrenheit',
            'youtube search', 'youtube', 'github search', 'github', 'stackoverflow',
            'translate hello to spanish', 'define', 'ip address', 'show ip', 'wifi name',
            'motivational quote', 'motivate me', 'inspire me', 'random fact', 'fun fact', 'tell me a fact',
            'magic 8 ball', 'compliment me', 'say something nice', 'insult me', 'roast me',
            'help', 'commands', 'what can you do',
            'sing', 'dance', 'tell me about yourself', 'about yourself',
            'good job', 'well done', 'great job', 'thank you',
            'are you alive', 'are you real', 'what do you think about ai',
            'cleanup desktop', 'empty recycle bin', 'startup apps status', 'network speed test',
            'confirm', 'cancel'
        ]

        partial_lower = partial_input.lower().strip()
        if not partial_lower:
            return []

        # Find commands that start with the partial input
        suggestions = [cmd for cmd in commands if cmd.startswith(partial_lower)]

        # If no exact prefix matches, try fuzzy matching
        if not suggestions:
            from difflib import get_close_matches
            suggestions = get_close_matches(partial_lower, commands, n=5, cutoff=0.6)

        return suggestions[:5]  # Return max 5 suggestions
    
    def close():
        ChatBot.started = False
    
    def addUserMsg(msg):
        eel.addUserMsg(msg)()
    
    def addAppMsg(msg):
        eel.addAppMsg(msg)()

    def start():
        path = os.path.dirname(os.path.abspath(__file__))
        # Use os.path.join for cross-platform compatibility
        web_path = os.path.join(path, 'web')
        eel.init(web_path, allowed_extensions=['.js', '.html'])
        try:
            eel.start('index.html', mode='brave',
                                    host='localhost',
                                    port=27005,
                                    block=False,
                                    size=(350, 480),
                                    position=(10,100),
                                    disable_cache=True,
                                    close_callback=ChatBot.close_callback)
            ChatBot.started = True
            while ChatBot.started:
                try:
                    eel.sleep(10.0)
                except:
                    #main thread exited
                    break
        
        except:
            pass