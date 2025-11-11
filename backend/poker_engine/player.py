class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hand = []
        self.folded = False
        self.current_bet = 0

    def bet(self, amount):
        
        if amount > self.chips:
            raise ValueError(f"{self.name} cannot bet more chips than available ({self.chips}).")
        
        self.chips -= amount
        self.current_bet += amount
        return amount

    def reset_for_next_round(self):
        self.current_bet = 0
        self.folded = False

    def reset_for_new_hand(self):
        self.current_bet = 0
        self.folded = False
        self.hand = []

    def reset_for_betting_round(self):
        self.current_bet = 0


    def __repr__(self):
        return f"{self.name}({self.chips} chips)"
    
    