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
        self.stage = "lobby"  # Changed from "preflop" to "lobby"
        
        # API additions: track current player and game state
        self.current_player_index = None
        self.game_over = False
        self.winner = None
        self.players_to_act = set()
        self.player_order = []
        self.action_index = 0
        
        # Lobby state
        self.lobby_timer = 15
        self.game_starting = False

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
        print(f"DEBUG: Setting up betting round for stage: {self.stage}")
        
        if self.stage == "preflop":
            if len([p for p in self.players if p.name]) == 2:  # Only count active players
                start_pos = (self.dealer_index + 1) % len(self.players)
            else:
                start_pos = (self.dealer_index + 3) % len(self.players)
        else:
            start_pos = (self.dealer_index + 1) % len(self.players)
    
        # Only include players who are actually playing (have names and chips)
        self.players_to_act = set()
        for i, p in enumerate(self.players):
            if p.name and p.name != "" and p.chips > 0 and not p.folded:
                self.players_to_act.add(i)
    
        self.player_order = []
        for i in range(len(self.players)):
            idx = (start_pos + i) % len(self.players)
            if self.players[idx].name and self.players[idx].name != "" and self.players[idx].chips > 0:
                self.player_order.append(idx)
    
        self.action_index = 0
        print(f"DEBUG: Players to act: {self.players_to_act}, Player order: {self.player_order}")
        self.advance_to_next_player()


    def advance_to_next_player(self):
        print(f"DEBUG: Advancing to next player. Players to act: {self.players_to_act}")

        # If no players to act, advance stage
        if not self.players_to_act:
            print("DEBUG: No players to act, advancing stage")
            self.advance_stage()
            return

        # Find next player who can act
        attempts = 0
        while attempts < len(self.player_order) * 2:  # Safety limit
            if self.action_index >= len(self.player_order):
                self.action_index = 0

            p_idx = self.player_order[self.action_index]
            p = self.players[p_idx]

            print(f"DEBUG: Checking player {p_idx} ({p.name}), in players_to_act: {p_idx in self.players_to_act}, folded: {p.folded}, chips: {p.chips}")

            if p_idx not in self.players_to_act:
                self.action_index += 1
                attempts += 1
                continue
            if p.folded:
                self.players_to_act.discard(p_idx)
                self.action_index += 1
                attempts += 1
                continue
            if p.chips <= 0:
                self.players_to_act.discard(p_idx)
                self.action_index += 1
                attempts += 1
                continue
            
            # Found a player who can act
            self.current_player_index = p_idx
            print(f"DEBUG: Set current player to {p_idx} ({p.name})")
            return  # This return should be the last statement in the method

        # If we get here, no valid player found
        print("DEBUG: No valid player found, advancing stage")
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
        # No legal actions during lobby phase
        if self.stage == "lobby":
            return []
            
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
        # Don't allow actions during lobby phase
        if self.stage == "lobby":
            return {"error": "Game is in lobby phase - cannot perform actions"}
            
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
        # Reset lobby state and start the actual game
        self.stage = "preflop"
        self.lobby_timer = None
        self.game_starting = False
        
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
        self.setup_betting_round()

    def award_pot_to_remaining_player(self):
        for p in self.players:
            if not p.folded:
                p.chips += self.pot
                self.winner = p
                self.game_over = True
                break

    def get_active_player_count(self):
        """Count how many players are actively seated (non-empty names)"""
        return sum(1 for p in self.players if p.name and p.name != "")

    def join_seat(self, seat_index, player_name):
        """Join a seat during lobby phase"""
        if self.stage != "lobby":
            return False, "Can only join seats during lobby phase"
            
        if seat_index < 0 or seat_index >= len(self.players):
            return False, "Invalid seat index"
            
        existing_player = self.players[seat_index]
        if existing_player.name and existing_player.name != "":
            return False, "Seat already taken"
            
        # Set player properties
        existing_player.name = player_name
        existing_player.is_bot = False
        existing_player.folded = False
        existing_player.current_bet = 0
        
        # Give default buy-in if chips are 0
        if existing_player.chips <= 0:
            existing_player.chips = 1000
            
        # Reset hand
        existing_player.hand = []
        
        return True, "Seat joined successfully"

    def leave_seat(self, seat_index):
        """Leave a seat during lobby phase"""
        if self.stage != "lobby":
            return False, "Can only leave seats during lobby phase"
            
        if seat_index < 0 or seat_index >= len(self.players):
            return False, "Invalid seat index"
            
        player = self.players[seat_index]
        if not player.name or player.name == "":
            return False, "Seat is already empty"
            
        player_name = player.name
        
        # Clear the seat but preserve chips for potential rejoin
        player.name = ""
        player.is_bot = False
        player.folded = False
        player.current_bet = 0
        player.hand = []
        # Note: We keep the chips so player can rejoin with same stack
        
        return True, f"{player_name} left seat {seat_index + 1}"

    # In your PokerGame class in poker_engine_api.py

    def get_legal_actions(self):
        """API addition: Return legal actions for current player"""
        # No legal actions during lobby phase
        if self.stage == "lobby":
            print("DEBUG: In lobby phase - no legal actions")
            return []

        if self.current_player_index is None:
            print("DEBUG: No current player - no legal actions")
            return []

        if self.game_over:
            print("DEBUG: Game over - no legal actions")
            return []

        p = self.players[self.current_player_index]
        to_call = max(0, self.current_bet - p.current_bet)

        print(f"DEBUG: Player {p.name}, to_call: {to_call}, chips: {p.chips}, current_bet: {p.current_bet}, game_bet: {self.current_bet}")

        actions = []
        if to_call == 0:
            actions.append("check")
        else:
            actions.append("call")

        actions.append("fold")

        if to_call < p.chips:
            actions.append("raise")

        print(f"DEBUG: Legal actions for {p.name}: {actions}")
        return actions
    
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
            # Only show cards if game is active and not in lobby
            if self.stage != "lobby":
                if viewer_name is None or p.name == viewer_name:
                    hand = [str(c) for c in p.hand]  # show full hand
                elif not p.folded:
                    hand = ["??", "??"]  # hide opponents' cards
                else:
                    hand = []  # folded players have no visible cards
            else:
                # In lobby phase, don't show any cards
                hand = []

            players_state.append({
                "name": p.name,
                "chips": p.chips,
                "hand": hand,
                "current_bet": p.current_bet,
                "folded": p.folded
            })
        print(f"[GET_STATE] viewer_name={viewer_name}")
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
            "players": players_state,
            "lobby_timer": getattr(self, 'lobby_timer', None),
            "game_starting": getattr(self, 'game_starting', False)
        }