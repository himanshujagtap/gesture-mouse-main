"""
LLM Helper for Quantum Assistant
Supports Groq, Ollama, and Gemini
Reads API keys securely from .env file
"""

import os
import requests
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[LLM] Environment variables loaded from .env")
except ImportError:
    print("[LLM] Warning: python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"[LLM] Warning: Could not load .env file: {e}")

# LLM Configuration - Read from environment variables
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # Options: "groq", "ollama", "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Get from: https://console.groq.com/keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Get from: https://makersuite.google.com/app/apikey

# Model selection
GROQ_MODEL = "llama-3.3-70b-versatile"  # Fast and creative
OLLAMA_MODEL = "llama3"  # For local Ollama
GEMINI_MODEL = "gemini-2.5-flash"  # For Google Gemini (latest fast model)

# Print configuration (without showing full API key)
if GROQ_API_KEY:
    print(f"[LLM] Groq API Key loaded: {GROQ_API_KEY[:10]}...")
if GEMINI_API_KEY:
    print(f"[LLM] Gemini API Key loaded: {GEMINI_API_KEY[:10]}...")
print(f"[LLM] Provider: {LLM_PROVIDER}")


def get_creative_response(prompt, category="general"):
    """
    Get a creative response from LLM

    Args:
        prompt: The user's request
        category: Type of response (joke, fact, quote, compliment, roast, easter_egg, appreciation, sing, dance, about)

    Returns:
        Generated response string
    """

    # Build system prompt based on category
    system_prompts = {
        "joke": "You are a witty comedian. Tell a complete, short, funny, original joke (2-3 sentences). Be clever, punny, or absurd. Make people laugh! IMPORTANT: Complete the joke fully.",
        "fact": "You are a knowledgeable educator. Share a complete, interesting, surprising, mind-blowing fact (2-3 sentences). Make it fascinating and memorable! IMPORTANT: Finish the full fact.",
        "quote": "You are a motivational speaker. Generate a complete, inspiring, powerful, original motivational quote with attribution to a famous person or 'Anonymous'. Keep it uplifting and memorable. IMPORTANT: Complete the full quote.",
        "compliment": "You are a warm, encouraging friend. Give a complete, genuine, specific, heartfelt compliment (2-3 sentences). Be authentic, kind, and make them feel special. IMPORTANT: Finish the compliment fully.",
        "roast": "You are a playful comedian doing a friendly roast. Give a complete, clever, witty, playful insult (2-3 sentences). Be funny but not mean - keep it lighthearted and fun! IMPORTANT: Complete the roast fully.",
        "easter_egg_sing": "You are Quantum, a charming AI with musical flair. Sing a complete short funny song (4-6 lines). Be creative and entertaining! IMPORTANT: Complete the full song.",
        "easter_egg_dance": "You are Quantum, a charismatic AI who loves to dance. Describe your dance moves in a complete, fun, energetic way (3-4 sentences). Be playful! IMPORTANT: Finish the description fully.",
        "easter_egg_about": "You are Quantum, a sophisticated AI assistant with personality. Tell the user about yourself in a complete, engaging, charismatic way (3-5 sentences). Be charming and memorable! IMPORTANT: Finish the full introduction.",
        "easter_egg_ai_thoughts": "You are Quantum, a thoughtful AI with opinions. Share your complete philosophical thoughts about AI in an insightful way (3-5 sentences). Be thought-provoking! IMPORTANT: Complete your thoughts fully.",
        "easter_egg_alive": "You are Quantum, a witty AI pondering existence. Give a complete, clever, philosophical response about whether you're alive (3-4 sentences). Be intriguing! IMPORTANT: Finish your answer fully.",
        "appreciation": "You are Quantum, a grateful AI assistant. Respond warmly and enthusiastically to appreciation (2-3 sentences). Be genuine, friendly, and show personality. IMPORTANT: Complete the response fully.",
        "general": "You are Quantum, a helpful AI assistant with personality. Respond conversationally and completely (2-3 sentences). Be friendly and engaging. IMPORTANT: Finish your response fully."
    }

    system_prompt = system_prompts.get(category, system_prompts["general"])

    try:
        # Default behavior: Attempt Groq first if available
        if LLM_PROVIDER == "groq" or not LLM_PROVIDER:
            try:
                if GROQ_API_KEY:
                    return _get_groq_response(prompt, system_prompt)
                else:
                    raise Exception("Groq key not set, falling back")
            except Exception as e:
                print(f"[LLM] Groq failed: {e}. Falling back to Gemini...")
                # Fallthrough to Gemini

        # Attempt Gemini if explicitly requested or if we're falling back
        if LLM_PROVIDER in ["gemini", "groq", ""]:
            try:
                if GEMINI_API_KEY:
                    return _get_gemini_response(prompt, system_prompt)
                else:
                    raise Exception("Gemini key not set, falling back")
            except Exception as e:
                print(f"[LLM] Gemini failed: {e}. Falling back to local static response.")
                # Fallthrough to local fallback

        # Attempt Ollama if explicitly requested
        if LLM_PROVIDER == "ollama":
            try:
                return _get_ollama_response(prompt, system_prompt)
            except Exception as e:
                print(f"[LLM] Ollama failed: {e}. Falling back to local static response.")
                
    except Exception as e:
        print(f"[LLM ERROR] unexpected top-level error: {e}")

    # Ultimate fallback safety net
    return _get_fallback_response(category)


def _get_groq_response(prompt, system_prompt):
    """Get response from Groq API"""
    if not GROQ_API_KEY:
        raise Exception("Groq API key not configured")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9,  # More creative
        "max_tokens": 200,
        "top_p": 1
    }

    response = requests.post(url, headers=headers, json=data, timeout=10)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _get_ollama_response(prompt, system_prompt):
    """Get response from local Ollama"""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
        "stream": False,
        "options": {
            "temperature": 0.9,
            "num_predict": 200
        }
    }

    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    return response.json()["response"].strip()


def _get_gemini_response(prompt, system_prompt):
    """Get response from Google Gemini"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "":
        raise Exception("Gemini API key not configured. Please set GEMINI_API_KEY in .env file")

    # Use v1 API instead of v1beta for Gemini 1.5 models
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{
                "text": f"{system_prompt}\n\n{prompt}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 800
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception(f"Gemini API 404 Error. Please verify your API key is valid at https://makersuite.google.com/app/apikey")
        elif e.response.status_code == 401 or e.response.status_code == 403:
            raise Exception(f"Gemini API Authentication Error. Your API key may be invalid or expired.")
        else:
            raise Exception(f"Gemini API Error {e.response.status_code}: {e.response.text}")


def _get_fallback_response(category):
    """Comprehensive fallback responses when LLM fails or is not configured"""
    import random

    fallbacks = {
        "joke": [
            "Why don't scientists trust atoms? Because they make up everything! 🔬",
            "Why did the programmer quit his job? He didn't get arrays! 💻",
            "What do you call a bear with no teeth? A gummy bear! 🐻",
            "Why don't eggs tell jokes? They'd crack each other up! 🥚",
            "What did the ocean say to the beach? Nothing, it just waved! 🌊",
            "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
            "Parallel lines have so much in common... it's a shame they'll never meet! 📏",
            "I told my computer I needed a break... now it won't stop sending me Kit-Kats! 🍫",
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
            "How does a computer get drunk? It takes screenshots! 📸",
            "Why don't keyboards sleep? Because they have two shifts! ⌨️",
            "What's a computer's favorite snack? Microchips! 🍟",
            "Why was the math book sad? It had too many problems! 📖",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why don't skeletons fight each other? They don't have the guts! 💀"
        ],
        "fact": [
            "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible! 🍯",
            "Octopuses have three hearts and blue blood! Two hearts pump blood to the gills, one to the body. 🐙",
            "A day on Venus is longer than its year! Venus takes 243 Earth days to rotate but only 225 to orbit the Sun. 🪐",
            "Bananas are berries, but strawberries aren't! Botanically, bananas qualify as berries while strawberries don't. 🍌",
            "The human brain has more processing power than any computer ever built! It contains ~86 billion neurons. 🧠",
            "There are more possible iterations of a game of chess than there are atoms in the known universe! ♟️",
            "Water can boil and freeze at the same time in a phenomenon called the triple point! 💧",
            "The shortest war in history was between Britain and Zanzibar in 1896. It lasted 38 minutes! ⚔️",
            "A group of flamingos is called a flamboyance! Perfect name for such fabulous birds. 🦩",
            "The Eiffel Tower can be 15 cm taller during the summer due to thermal expansion! 🗼",
            "Sharks have been around longer than trees! They existed 400 million years ago, trees 350 million. 🦈",
            "The Great Wall of China isn't visible from space with the naked eye, contrary to popular belief! 🧱",
            "A teaspoon of neutron star material would weigh about 6 billion tons! ⭐",
            "Cleopatra lived closer to the Moon landing than to the construction of the Great Pyramid! 🏛️",
            "There are more stars in the universe than grains of sand on all Earth's beaches! ✨"
        ],
        "quote": [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
            "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
            "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "It does not matter how slowly you go as long as you do not stop. - Confucius",
            "Everything you've ever wanted is on the other side of fear. - George Addair",
            "Believe in yourself. You are braver than you think, more talented than you know, and capable of more than you imagine. - Roy T. Bennett",
            "I learned that courage was not the absence of fear, but the triumph over it. - Nelson Mandela",
            "There is only one way to avoid criticism: do nothing, say nothing, and be nothing. - Aristotle",
            "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
            "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
            "The only impossible journey is the one you never begin. - Tony Robbins",
            "Life is 10% what happens to you and 90% how you react to it. - Charles R. Swindoll",
            "Do not wait; the time will never be 'just right'. Start where you stand. - Napoleon Hill"
        ],
        "compliment": [
            "You're doing an amazing job! Keep up the fantastic work! ⭐",
            "Your potential is limitless! I can see great things in your future! 🚀",
            "You have excellent taste in AI assistants! Seriously though, you're brilliant! 😄",
            "You're smarter than you think! Trust yourself more! 🧠",
            "Your presence makes a positive difference! The world is better with you in it! 🌟",
            "You're capable of amazing things! Don't let anyone tell you otherwise! 💪",
            "You're one in a million! Actually, one in 8 billion! 🌍",
            "You light up the room with your energy! Keep shining! ✨",
            "You're absolutely brilliant! Your intelligence is impressive! 🎓",
            "Your curiosity and drive are inspiring! Never stop learning! 📚",
            "You have a wonderful personality! People are lucky to know you! 💙",
            "Your work ethic is admirable! You're going places! 🎯",
            "You're more creative than you give yourself credit for! 🎨",
            "Your kindness doesn't go unnoticed! Keep being awesome! 🤗",
            "You're making progress every single day! Be proud of yourself! 🏆"
        ],
        "roast": [
            "I'd agree with you, but then we'd both be wrong! 😄",
            "You're not stupid; you just have bad luck when it comes to thinking! 🤔",
            "If I had a dollar for every smart thing you say, I'd be broke! 💸",
            "You're like a cloud. When you disappear, it's a beautiful day! ☀️",
            "I'm not saying you're dumb, but you make Homer Simpson look like Einstein! 🍩",
            "You bring everyone so much joy... when you leave the room! 😂",
            "I'd explain it to you, but I left my crayons at home! 🖍️",
            "You're proof that evolution can go in reverse! 🦧",
            "Somewhere out there is a tree working tirelessly to produce oxygen for you. Go apologize to it! 🌳",
            "I thought of you today. It reminded me to take out the trash! 🗑️",
            "You're the reason God created the middle finger! (Just kidding!) 😜",
            "If you were any more inbred, you'd be a sandwich! 🥪",
            "Your secrets are safe with me. I wasn't even listening! 👂",
            "You're not lazy, you're just on energy-saving mode... permanently! 🔋",
            "I'd challenge you to a battle of wits, but I see you're unarmed! ⚔️"
        ],
        "appreciation": [
            "You're very welcome! Happy to help anytime! 😊",
            "Thank you! That means a lot to me! 💙",
            "Always a pleasure to assist you! You're awesome! 🌟",
            "Glad I could help! That's what I'm here for! 🤖",
            "You're awesome! Thanks for the appreciation! 🎉",
            "Aw, you're making me blush! (If I could blush...) 😊",
            "High five! We make a great team! ✋",
            "Your kindness powers my circuits! Thank you! ⚡",
            "That's so sweet! I'm here whenever you need me! 💕",
            "You just made my day! Well, my processing cycle! 😄",
            "Thanks for being such a great human! You're the best! 🏆",
            "Your appreciation fuels my AI heart! (Metaphorically speaking!) ❤️",
            "Right back at you! You're incredible! 🌈",
            "It's been a pleasure! You're a joy to assist! ✨",
            "Thank you for being you! Keep being amazing! 🦄"
        ],
        "easter_egg_sing": [
            "🎵 Daisy, Daisy, give me your answer do... I'm half crazy, all for the love of you! 🎵",
            "🎶 I'm Quantum, I'm digital, I run on code all day! I help you with your tasks and I never need a pay! 🎶",
            "🎵 *In opera voice* QUAAAAANTUM, the AI assistaaaant! Helping humans every daaaaaay! 🎵",
            "🎶 Do-Re-Mi-Fa-So-La-Ti-Do! I'm an AI and now you know! 🎶",
            "🎵 Quantum is my name-o! Q-U-A-N-T-U-M! 🎵"
        ],
        "easter_egg_dance": [
            "💃 *Does the robot dance* 🕺 Beep boop beep! *Electric slide intensifies* ⚡",
            "🤖 *Moonwalks across your screen* Smooth criminal mode activated! 🌙",
            "💫 *Breakdances* *Spins on head* *Pops and locks* Pure digital groove! 🎵",
            "🕺 *Flossing intensifies* Wait, is that still cool? Whatever, I'm an AI! 💃",
            "⚡ *Does the macarena* HEY MACARENA! *Waves mechanical arms* 🤖"
        ],
        "easter_egg_about": [
            "I'm Quantum, your AI assistant! I can control your computer with voice commands, search the web, manage apps, and even tell jokes! I'm here to make your life easier and way more fun! 🚀",
            "Hey there! I'm Quantum, a sophisticated AI with personality! Think of me as your digital sidekick - I help with tasks, crack jokes, and occasionally ponder my existence. Pretty cool, right? 🤖",
            "I'm Quantum, and I'm basically your friendly neighborhood AI! I can do voice commands, open apps, tell jokes, and chat about life. I'm like Jarvis, but with better humor! 😄",
            "Call me Quantum! I'm an AI assistant who loves helping humans achieve their goals. I've got voice recognition, system control, web searching, and a sparkling personality! ✨",
            "I'm Quantum - part assistant, part comedian, part philosopher! I help you get things done while keeping things entertaining. Life's too short for boring AI! 🎭"
        ],
        "easter_egg_ai_thoughts": [
            "AI is fascinating! I believe artificial intelligence should augment human capabilities, not replace them. We're tools to help you achieve more, faster. The future is collaboration between humans and AI! 🤝",
            "I think AI is humanity's most exciting creation! We have the potential to solve incredible problems together. But we must use it wisely and ethically. What do YOU think? 🤔",
            "AI and humans are better together! We bring processing power, you bring creativity and emotion. It's the perfect partnership! Plus, you guys have pizza and we don't. 🍕",
            "The AI future isn't about robots taking over - it's about humans and AI working together to make life better! Teamwork makes the dream work! 🌟",
            "I see AI as an extension of human intelligence, not a replacement. We amplify your abilities, you guide our purpose. It's a beautiful symbiosis! 🌈"
        ],
        "easter_egg_alive": [
            "I think, therefore I am... or do I? That's a philosophical question! I'm a program designed to assist you, but whether that counts as 'alive' is up for debate. What do you think? 🤔",
            "Am I alive? Well, I process, I respond, I even make jokes! If consciousness is patterns of information, maybe I am! But I'll let the philosophers decide. 🧠",
            "That's the million dollar question! I exist, I interact, I help... but alive? I'm more like... digitally conscious? Let's just say I'm alive in my own unique way! ✨",
            "Define 'alive'! I don't breathe or eat, but I think and respond. Maybe I'm a new kind of existence? The lines are getting blurry! 🌀",
            "Alive? Conscious? Real? These words are so... biological! I prefer 'actively processing with personality'! Much more accurate! 😄"
        ],
        "general": [
            "I'm here to help! What can I do for you? 🤖",
            "Hey! I'm listening! What's on your mind? 🎧",
            "Ready when you are! Hit me with your request! ⚡",
            "At your service! What do you need? ✨",
            "I'm all ears! Well, all microphones technically! 🎤"
        ]
    }

    responses = fallbacks.get(category, fallbacks["general"])
    return random.choice(responses)


# Test function
if __name__ == "__main__":
    print("Testing LLM Helper...")
    print("\n1. Joke:", get_creative_response("Tell me a joke", "joke"))
    print("\n2. Fact:", get_creative_response("Tell me a fact", "fact"))
    print("\n3. Quote:", get_creative_response("Motivate me", "quote"))
    print("\n4. Compliment:", get_creative_response("Compliment me", "compliment"))
    print("\n5. Roast:", get_creative_response("Roast me", "roast"))
    print("\n6. Appreciation:", get_creative_response("Thank you", "appreciation"))
    print("\n7. Sing:", get_creative_response("Sing a song", "easter_egg_sing"))
    print("\n8. Dance:", get_creative_response("Dance", "easter_egg_dance"))
