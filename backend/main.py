# main.py
#from poker_engine.heuristic_ai import HeuristicAI
#from poker_engine.simple_ai import SimpleAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from concurrent.futures import ProcessPoolExecutor
import asyncio
from poker_engine.monte_carlo_ai import MonteCarloAI
from fastapi import Body

# Import your engine
from poker_engine.poker_engine_api import PokerGame

app = FastAPI(title="Poker Game API")

# Allow requests from your React/Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active games (room_id -> PokerGame)
games = {}
locks = {}
executor = ProcessPoolExecutor(max_workers=2)

# --- Request models ---
class CreateGameRequest(BaseModel):
    player_names: list[str]

class ActionRequest(BaseModel):
    player_index: int
    action: str
    raise_amount: int | None = 0


# --- Routes ---

@app.post("/create_game")
async def create_game(req: CreateGameRequest):
    """Create a new poker game session with 1 AI opponent."""
    if len(req.player_names) < 1:
        raise HTTPException(status_code=400, detail="Need at least one human player")

    game_id = str(uuid4())[:8]

    # Add a bot player automatically
    all_players = req.player_names + ["Bot"]
    game = PokerGame(all_players)

    # Mark bot flag
    for p in game.players:
        if p.name == "Bot":
            p.is_bot = True

    games[game_id] = game
    locks[game_id] = asyncio.Lock()
    return {"game_id": game_id, "state": game.get_game_state()}


@app.post("/start_hand/{game_id}")
async def start_hand(game_id: str):
    """Start a new hand for an existing game"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    async with locks[game_id]:
        game.play_hand()
        return {"message": "New hand started", "state": game.get_game_state()}


@app.post("/action/{game_id}")
async def player_action(game_id: str, data: dict = Body(...)):
    """Execute a player's action and trigger AI responses."""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    async with locks[game_id]:
        player_index = data["player_index"]
        action = data["action"]
        raise_amount = data.get("raise_amount", 0)

        messages = []  # Collect all action messages

        # --- Human player action ---
        result = game.execute_action(player_index, action, raise_amount)
        if "message" in result:
            messages.append(result["message"])

        # --- AI auto-turn(s) ---
        while (
            not game.game_over
            and game.current_player_index is not None
            and getattr(game.players[game.current_player_index], "is_bot", False)
        ):
            ai_state = game.get_game_state(viewer_name=game.players[game.current_player_index].name)
            loop = asyncio.get_event_loop()
            ai_player = MonteCarloAI(
                name=game.players[game.current_player_index].name,
                simulations=200
            )

            try:
                ai_decision = await loop.run_in_executor(executor, ai_player.decide, ai_state)
                move = ai_decision.get("move", "check")
                amt = ai_decision.get("raise_amount", 0)

                ai_result = game.execute_action(game.current_player_index, move, amt)
                if "message" in ai_result:
                    messages.append(ai_result["message"])

                print(f"[AI] {ai_player.name} -> {move} {amt if amt else ''}")

            except Exception as e:
                print(f"[AI ERROR] {ai_player.name}: {e}")
                break

        state = game.get_game_state()
        return {"messages": messages, "state": state}

@app.get("/state/{game_id}")
async def get_state(game_id: str):
    """Return full current state of the game"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return {"state": game.get_game_state()}
