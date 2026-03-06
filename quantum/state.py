"""
Shared mutable state for the Quantum assistant.

All modules import this module and read/write these attributes directly
(e.g. `state.is_awake = True`) so changes are visible everywhere.
"""

# File explorer state
file_exp_status = False
files = []
path = ''

# Bot lifecycle
is_awake = True
assistant_name = "Quantum"

# Input handling
blank_input_responses = [
    "I didn't catch that. Could you repeat?",
    "Sorry, I couldn't hear you clearly.",
    "Hmm, it seems you didn't say anything.",
    "I'm listening... but I didn't hear a command.",
    "Could you speak a bit louder? I missed that."
]
blank_response_index = 0
typing_mode = False
text_input_mode = False

# Confirmation flow for risky actions
pending_confirmation = None
