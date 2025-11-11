import random

class SimpleAI:
    def __init__(self, name="Bot"):
        self.name = name
        self.is_bot = True

    def decide(self, state: dict) -> dict:
        actions = state.get("legal_actions", [])
        if not actions:
            return {"move": "check", "raise_amount": 0}

        if "raise" in actions and random.random() < 0.25:
            return {"move": "raise", "raise_amount": random.choice([30, 40, 50])}
        elif "call" in actions:
            return {"move": "call", "raise_amount": 0}
        elif "check" in actions:
            return {"move": "check", "raise_amount": 0}
        else:
            return {"move": "fold", "raise_amount": 0}
