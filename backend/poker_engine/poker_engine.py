from card import Deck
from player import Player
from utils import eval_hand

class PokerGame:
    def __init__(self, player_names):
        self.players = [Player(name) for name in player_names]
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.dealer_index = 0
        self.small_blind = 10
        self.big_blind = 20
        self.current_bet = 0
        self.stage = "preflop"

    def rotate_dealer(self):
        self.dealer_index = (self.dealer_index + 1) % len(self.players)
        

    def post_blinds(self):
        sb_player = self.players[(self.dealer_index + 1) % len(self.players)]
        bb_player = self.players[(self.dealer_index + 2) % len(self.players)]

        sb_amount = sb_player.bet(self.small_blind)
        bb_amount = bb_player.bet(self.big_blind)

        self.current_bet = self.big_blind
        self.pot = sb_amount + bb_amount
        dealer = self.players[self.dealer_index]
        
        print(f"Dealer: {dealer.name}")
        print(f"Small blind: {sb_player.name} posts {self.small_blind} chips")
        print(f"Big blind: {bb_player.name} posts {self.big_blind} chips")

    def deal_hole_cards(self):
        for player in self.players:
            player.hand = self.deck.deal(2)
    
    def deal_flop(self):
        self.community_cards += self.deck.deal(3)

    def deal_turn(self):
        self.community_cards += self.deck.deal(1)

    def deal_river(self):
        self.community_cards += self.deck.deal(1)

    def show_table(self):
        print(f"\nCommunity Cards: {self.community_cards}")
        for p in self.players:
            if not p.folded:
                print(f"{p.name}: {p.hand} (Chips: {p.chips}, Bet this round: {p.current_bet})")

    def betting_round(self):
        print(f"\n--- {self.stage.upper()} BETTING ROUND ---")
        print(f"Pot: {self.pot}")

        if self.stage == "preflop":
            
            
            
            if len(self.players) == 2:
                start_pos = self.dealer_index  # Heads-up: dealer/SB acts first preflop
            else:
                start_pos = (self.dealer_index + 3) % len(self.players)  # After BB
        else:
            start_pos = (self.dealer_index + 1) % len(self.players)  # After dealer post-flop

        players_to_act = set(range(len(self.players)))

        player_order = []
        for i in range(len(self.players)):
            player_order.append((start_pos + i) % len(self.players))

        action_index = 0

        while len(players_to_act) > 0:
            if action_index >= len(player_order):
                action_index = 0

            p_idx = player_order[action_index]
            p = self.players[p_idx]

            if p_idx not in players_to_act:
                action_index += 1
                continue
            
            if p.folded:
                players_to_act.discard(p_idx)
                action_index += 1
                continue

            if p.chips <= 0:
                print(f"{p.name} is all-in!")
                players_to_act.discard(p_idx)
                action_index += 1
                continue
            
            to_call = max(0, self.current_bet - p.current_bet)

            print(f"\nCurrent bet to match: {self.current_bet}")
            print(f"{p.name}'s turn (Chips: {p.chips}, Already bet this round: {p.current_bet})")
            print(f"Amount to call: {to_call}")

            valid = False
            while not valid:
                action = input("Enter action (call / check / fold / raise): ").strip().lower()

                if action == "call":
                    if to_call > 0:
                        amount_bet = p.bet(to_call)
                        self.pot += amount_bet
                        print(f"{p.name} calls {to_call}.")
                        players_to_act.discard(p_idx)
                        valid = True
                    else:
                        print(f"No bet to call, you can check instead.")

                elif action == "fold":
                    p.folded = True
                    print(f"{p.name} folds.")
                    players_to_act.discard(p_idx)
                    valid = True

                    if sum(1 for pl in self.players if not pl.folded) == 1:
                        print("Everyone else folded!")
                        return

                elif action == "check":
                    if to_call == 0:
                        print(f"{p.name} checks.")
                        players_to_act.discard(p_idx)
                        valid = True
                    else:
                        print(f"Cannot check when there is a bet to call!")

                elif action == "raise":
                    if to_call >= p.chips:
                        print(f"You only have {p.chips} chips. You can only call or fold.")
                        continue

                    while True:
                        try:
                            raise_amount = int(input("Enter raise amount (additional chips): "))
                            if raise_amount <= 0:
                                print("Raise amount must be positive!")
                                continue
                            
                            total_to_bet = to_call + raise_amount

                            if total_to_bet > p.chips:
                                print(f"You only have {p.chips} chips remaining!")
                                continue
                            
                            amount_bet = p.bet(total_to_bet)
                            self.pot += amount_bet
                            self.current_bet = p.current_bet

                            print(f"{p.name} raises to {self.current_bet}.")

                            # FIX: Reset players_to_act so everyone gets to respond to the raise
                            players_to_act = set(range(len(self.players)))
                            players_to_act.discard(p_idx)

                            valid = True
                            break

                        except ValueError:
                            print("Enter a valid number.")

                else:
                    print(f"Invalid input! Please try again.")

            print(f"Pot is now: {self.pot}")
            action_index += 1

        print(f"\nBetting round complete.")

    def showdown(self):
        HAND_RANKS = {
            "high_card": 1,
            "one_pair": 2,
            "two_pair": 3,
            "three_of_a_kind": 4,
            "straight": 5,
            "flush": 6,
            "full_house": 7,
            "four_of_a_kind": 8,
            "straight_flush": 9,
            "royal_flush": 10
        }
        RANK_NAMES = {v: k for k, v in HAND_RANKS.items()}
        
        print(f"\n=== SHOWDOWN ===")
        print(f"Community Cards: {self.community_cards}\n")
        
        best_rank = None
        best_hand = None
        winner = None
        
        for p in self.players:
            if not p.folded:
                print(f"{p.name}: {p.hand}")
                all_cards = p.hand + self.community_cards
                rank, hand = eval_hand(all_cards)
                
                if best_rank is None or rank > best_rank:
                    best_rank = rank
                    best_hand = hand
                    winner = p
        
        if winner:
            hand_name = RANK_NAMES[best_rank[0]].replace('_', ' ').title()
            print(f"\n{winner.name} WINS with {hand_name}!")
            print(f"Winning hand: {best_hand}")
            winner.chips += self.pot
            print(f"{winner.name} wins {self.pot} chips!")

        for p in self.players:
            print(f"\n{p.name}: {p.chips}(chips)")

    def play_hand(self):
        print(f"\n==== NEW HAND ====\n")
        
        # Reset game state
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        
        # Reset all players
        for p in self.players:
            p.reset_for_new_hand()
        
        # Post blinds
        self.post_blinds()
        self.deal_hole_cards()
        self.show_table()

        # Preflop
        self.stage = "preflop"
        self.betting_round()
        
        # Check if hand ended early
        if sum(1 for p in self.players if not p.folded) <= 1:
            self.award_pot_to_remaining_player()
            return

        # Reset for flop
        self.current_bet = 0
        for p in self.players:
            p.reset_for_betting_round()
        
        self.stage = "flop"
        self.deal_flop()
        self.show_table()
        self.betting_round()
        
        if sum(1 for p in self.players if not p.folded) <= 1:
            self.award_pot_to_remaining_player()
            return

        # Reset for turn
        self.current_bet = 0
        for p in self.players:
            p.reset_for_betting_round()
        
        self.stage = "turn"
        self.deal_turn()
        self.show_table()
        self.betting_round()
        
        if sum(1 for p in self.players if not p.folded) <= 1:
            self.award_pot_to_remaining_player()
            return

        # Reset for river
        self.current_bet = 0
        for p in self.players:
            p.reset_for_betting_round()
        
        self.stage = "river"
        self.deal_river()
        self.show_table()
        self.betting_round()
        
        if sum(1 for p in self.players if not p.folded) <= 1:
            self.award_pot_to_remaining_player()
            return

        # Showdown
        self.showdown()

    def award_pot_to_remaining_player(self):
        """Award pot to the last remaining player when others fold"""
        for p in self.players:
            if not p.folded:
                print(f"\n{p.name} wins {self.pot} chips (everyone else folded)!")
                p.chips += self.pot
                break