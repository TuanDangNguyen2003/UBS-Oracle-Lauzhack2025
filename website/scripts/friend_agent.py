# website/scripts/friend_agent.py

from typing import List, Dict
from bank_agent_runtime import step

def answer(prompt: str, history: List[Dict[str, str]]) -> str:
    # History is tracked in the web UI; the real conversation state
    # is stored inside bank_agent_runtime via the global `conversation`.
    return step(prompt)
