# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from concurrent.futures import ProcessPoolExecutor
import asyncio

# Import your engine
from poker_engine.poker_engine_api import PokerGame

app = FastAPI(title="Poker Game API")

# Allow requests from your React/Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change this to your frontend URL in production
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
    """Create a new poker game session"""
    if len(req.player_names) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")

    game_id = str(uuid4())[:8]
    game = PokerGame(req.player_names)
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
async def player_action(game_id: str, req: ActionRequest):
    """Execute a player's action (call, fold, check, raise)"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    async with locks[game_id]:
        result = game.execute_action(req.player_index, req.action, req.raise_amount)
        state = game.get_game_state()
        return {"result": result, "state": state}


@app.get("/state/{game_id}")
async def get_state(game_id: str):
    """Return full current state of the game"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return {"state": game.get_game_state()}
