from .card import Deck
from .player import Player
from .utils import eval_hand

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
        
        # API additions: track current player and game state
        self.current_player_index = None
        self.game_over = False
        self.winner = None
        self.players_to_act = set()
        self.player_order = []
        self.action_index = 0

    def rotate_dealer(self):
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def post_blinds(self):
        sb_player = self.players[(self.dealer_index + 1) % len(self.players)]
        bb_player = self.players[(self.dealer_index + 2) % len(self.players)]

        sb_amount = sb_player.bet(self.small_blind)
        bb_amount = bb_player.bet(self.big_blind)

        self.current_bet = self.big_blind
        self.pot = sb_amount + bb_amount

    def deal_hole_cards(self):
        for player in self.players:
            player.hand = self.deck.deal(2)
    
    def deal_flop(self):
        self.community_cards += self.deck.deal(3)

    def deal_turn(self):
        self.community_cards += self.deck.deal(1)

    def deal_river(self):
        self.community_cards += self.deck.deal(1)

    def setup_betting_round(self):
        """API addition: Initialize betting round and set current player"""
        if self.stage == "preflop":
            if len(self.players) == 2:
                start_pos = self.dealer_index
            else:
                start_pos = (self.dealer_index + 3) % len(self.players)
        else:
            start_pos = (self.dealer_index + 1) % len(self.players)

        self.players_to_act = set(range(len(self.players)))

        self.player_order = []
        for i in range(len(self.players)):
            self.player_order.append((start_pos + i) % len(self.players))

        self.action_index = 0
        self.advance_to_next_player()

    def advance_to_next_player(self):
        """API addition: Find next player who needs to act"""
        while len(self.players_to_act) > 0:
            if self.action_index >= len(self.player_order):
                self.action_index = 0

            p_idx = self.player_order[self.action_index]
            p = self.players[p_idx]

            if p_idx not in self.players_to_act:
                self.action_index += 1
                continue
            
            if p.folded:
                self.players_to_act.discard(p_idx)
                self.action_index += 1
                continue

            if p.chips <= 0:
                self.players_to_act.discard(p_idx)
                self.action_index += 1
                continue
            
            self.current_player_index = p_idx
            return
        
        # Betting round complete
        self.current_player_index = None
        self.advance_stage()

    def advance_stage(self):
        """API addition: Move to next stage automatically"""
        if sum(1 for p in self.players if not p.folded) <= 1:
            self.award_pot_to_remaining_player()
            return

        if self.stage == "preflop":
            self.current_bet = 0
            for p in self.players:
                p.reset_for_betting_round()
            self.stage = "flop"
            self.deal_flop()
            self.setup_betting_round()
        elif self.stage == "flop":
            self.current_bet = 0
            for p in self.players:
                p.reset_for_betting_round()
            self.stage = "turn"
            self.deal_turn()
            self.setup_betting_round()
        elif self.stage == "turn":
            self.current_bet = 0
            for p in self.players:
                p.reset_for_betting_round()
            self.stage = "river"
            self.deal_river()
            self.setup_betting_round()
        elif self.stage == "river":
            self.showdown()

    def get_legal_actions(self):
        """API addition: Return legal actions for current player"""
        if self.current_player_index is None or self.game_over:
            return []
        
        p = self.players[self.current_player_index]
        to_call = max(0, self.current_bet - p.current_bet)
        
        actions = []
        if to_call == 0:
            actions.append("check")
        else:
            actions.append("call")
        
        actions.append("fold")
        
        if to_call < p.chips:
            actions.append("raise")
        
        return actions

    def execute_action(self, player_index, action, raise_amount=0):
        """API addition: Execute action without input(), return result"""
        if self.game_over:
            return {"error": "Game is over"}
        
        if player_index != self.current_player_index:
            return {"error": "Not this player's turn"}
        
        p = self.players[player_index]
        to_call = max(0, self.current_bet - p.current_bet)

        if action == "call":
            if to_call > 0:
                amount_bet = p.bet(to_call)
                self.pot += amount_bet
                self.players_to_act.discard(player_index)
                self.action_index += 1
                self.advance_to_next_player()
                return {"success": True, "message": f"{p.name} calls {to_call}"}
            else:
                return {"error": "No bet to call, you can check instead"}

        elif action == "fold":
            p.folded = True
            self.players_to_act.discard(player_index)
            
            if sum(1 for pl in self.players if not pl.folded) == 1:
                self.award_pot_to_remaining_player()
                return {"success": True, "message": f"{p.name} folds. Everyone else folded!"}
            
            self.action_index += 1
            self.advance_to_next_player()
            return {"success": True, "message": f"{p.name} folds"}

        elif action == "check":
            if to_call == 0:
                self.players_to_act.discard(player_index)
                self.action_index += 1
                self.advance_to_next_player()
                return {"success": True, "message": f"{p.name} checks"}
            else:
                return {"error": "Cannot check when there is a bet to call!"}

        elif action == "raise":
            if to_call >= p.chips:
                return {"error": "You only have chips. You can only call or fold."}
            
            if raise_amount <= 0:
                return {"error": "Raise amount must be positive!"}
            
            total_to_bet = to_call + raise_amount

            if total_to_bet > p.chips:
                return {"error": f"You only have {p.chips} chips remaining!"}
            
            amount_bet = p.bet(total_to_bet)
            self.pot += amount_bet
            self.current_bet = p.current_bet

            self.players_to_act = set(range(len(self.players)))
            self.players_to_act.discard(player_index)
            
            self.action_index += 1
            self.advance_to_next_player()
            return {"success": True, "message": f"{p.name} raises to {self.current_bet}"}

        else:
            return {"error": "Invalid input! Please try again."}

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
        
        best_rank = None
        best_hand = None
        winner = None
        
        for p in self.players:
            if not p.folded:
                all_cards = p.hand + self.community_cards
                rank, hand = eval_hand(all_cards)
                
                if best_rank is None or rank > best_rank:
                    best_rank = rank
                    best_hand = hand
                    winner = p
        
        if winner:
            winner.chips += self.pot
            self.winner = winner
            self.game_over = True

    def play_hand(self):
        """Start a new hand - for API, call this to initialize"""
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.game_over = False
        self.winner = None
        
        for p in self.players:
            p.reset_for_new_hand()
        
        self.post_blinds()
        self.deal_hole_cards()

        self.stage = "preflop"
        self.setup_betting_round()

    def award_pot_to_remaining_player(self):
        """Award pot to the last remaining player when others fold"""
        for p in self.players:
            if not p.folded:
                p.chips += self.pot
                self.winner = p
                self.game_over = True
                break

    def get_game_state(self, viewer_name=None):
        current_player = None
        to_call = 0

        if self.current_player_index is not None:
            current_player = self.players[self.current_player_index].name
            p = self.players[self.current_player_index]
            to_call = max(0, self.current_bet - p.current_bet)

        players_state = []
        for p in self.players:
            hand = []
            if viewer_name is None or p.name == viewer_name:
                hand = [str(c) for c in p.hand]  # show full hand
            elif not p.folded:
                hand = ["??", "??"]  # hide opponents’ cards
            else:
                hand = []  # folded players have no visible cards

            players_state.append({
                "name": p.name,
                "chips": p.chips,
                "hand": hand,
                "current_bet": p.current_bet,
                "folded": p.folded
            })

        return {
            "stage": self.stage,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "community_cards": [str(c) for c in self.community_cards],
            "current_player": current_player,
            "current_player_index": self.current_player_index,
            "to_call": to_call,
            "legal_actions": self.get_legal_actions(),
            "game_over": self.game_over,
            "winner": self.winner.name if self.winner else None,
            "dealer": self.players[self.dealer_index].name,
            "players": players_state
        }
