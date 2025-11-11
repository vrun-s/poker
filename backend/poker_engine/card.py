import random

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit}"
    
class Deck:
    suits = ['s', 'h', 'd', 'c']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def __init__(self):
        self.cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, n):
        dealt_cards = self.cards[:n]
        self.cards = self.cards[n:]
        return dealt_cards



'''
d = Deck()
print(d.deal(2))
'''