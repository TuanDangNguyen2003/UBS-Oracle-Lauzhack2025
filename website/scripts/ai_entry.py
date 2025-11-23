# scripts/ai_entry.py

import sys
import json
from typing import Any, Dict, List

from friend_agent import answer

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input payload"}))
        return

    try:
        data: Dict[str, Any] = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON from Node"}))
        return

    prompt: str = data.get("prompt", "")
    history: List[Dict[str, str]] = data.get("history", [])

    # Call your friend’s AI function
    reply = answer(prompt, history)

    # Always print JSON so Node can parse it
    print(json.dumps({"reply": reply}))

if __name__ == "__main__":
    main()
