import random
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import trange

from poker_engine.poker_engine_api import PokerGame
from poker_engine.ai_player import SimpleAI
from poker_engine.heuristic_ai import HeuristicAI
from poker_engine.monte_carlo_ai import MonteCarloAI


def simulate_game(ai_model_class, num_hands=50):
    """
    Runs multiple poker hands for a given AI model (vs a basic bot)
    and returns results for analysis.
    """
    results = []
    ai_name = ai_model_class.__name__

    for i in trange(num_hands, desc=f"Simulating {ai_name}"):
        # Each hand: AI vs Simple bot
        players = ["AI_Bot", "Simple_Bot"]
        game = PokerGame(players)

        # Mark which player is AI type
        for p in game.players:
            if p.name == "AI_Bot":
                p.is_bot = True
            else:
                p.is_bot = True

        # Instantiate both AIs
        main_ai = ai_model_class(name="AI_Bot")
        opponent = SimpleAI(name="Simple_Bot")

        # Start the hand
        game.play_hand()

        # Run till game over
        while not game.game_over:
            p_idx = game.current_player_index
            if p_idx is None:
                break

            player = game.players[p_idx]
            state = game.get_game_state()

            # Choose which AI acts
            if player.name == "AI_Bot":
                ai = main_ai
            else:
                ai = opponent

            # Make decision
            decision = ai.decide(state)
            move = decision.get("move", "check")
            amt = decision.get("raise_amount", 0)
            game.execute_action(p_idx, move, amt)

        results.append({
            "ai_type": ai_name,
            "winner": game.winner.name,
            "stage": game.stage
        })

    return results


def visualize(results):
    df = pd.DataFrame(results)

    # Win rates
    win_rates = df.groupby("ai_type")["winner"].value_counts(normalize=True).unstack().fillna(0)

    win_rates.plot(kind="bar", figsize=(8, 5))
    plt.title("Win Rate Comparison")
    plt.ylabel("Win Rate")
    plt.xlabel("AI Type")
    plt.legend(title="Winner")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    all_results = []

    # You can adjust number of simulations here
    for ai_class in [SimpleAI, HeuristicAI, MonteCarloAI]:
        res = simulate_game(ai_class, num_hands=30)
        all_results.extend(res)

    visualize(all_results)
