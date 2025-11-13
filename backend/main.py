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
import random
from poker_engine.poker_engine_api import PokerGame
from ws_manager import ConnectionManager
from fastapi import WebSocket, WebSocketDisconnect
import time

manager = ConnectionManager()

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
lobby_timers = {}  # Track lobby timers for each game
executor = ProcessPoolExecutor(max_workers=2)

# Lobby configuration
LOBBY_DURATION = 15  # 15 seconds lobby phase
MIN_PLAYERS = 2      # Minimum players to start game

# --- Request models ---
class CreateGameRequest(BaseModel):
    player_names: list[str]
    seat_count: int | None = 6

class ActionRequest(BaseModel):
    player_index: int
    action: str
    raise_amount: int | None = 0

class JoinSeatRequest(BaseModel):
    player_name: str
    seat_index: int

class LeaveSeatRequest(BaseModel):
    seat_index: int

# --- Lobby Management ---
async def start_lobby_timer(game_id: str):
    """Start or restart the lobby timer for a game"""
    if game_id in lobby_timers:
        lobby_timers[game_id].cancel()
    
    lobby_timers[game_id] = asyncio.create_task(lobby_countdown(game_id))

async def lobby_countdown(game_id: str):
    """Countdown timer for lobby phase"""
    game = games.get(game_id)
    if not game:
        return

    try:
        for remaining in range(LOBBY_DURATION, -1, -1):
            # Update lobby timer in game state
            game.lobby_timer = remaining
            game.game_starting = remaining <= 5 and remaining > 0
            
            # Broadcast timer update
            await manager.broadcast(game_id, {
                "type": "state_update",
                "state": game.get_game_state()
            })
            
            if remaining == 0:
                break
                
            await asyncio.sleep(1)
        
        # Timer ended - check if we can start the game
        await check_and_start_game(game_id)
        
    except asyncio.CancelledError:
        # Timer was cancelled (player joined/left)
        pass
    except Exception as e:
        print(f"Lobby timer error for game {game_id}: {e}")

async def check_and_start_game(game_id: str):
    """Check if game can start and begin if conditions are met"""
    game = games.get(game_id)
    if not game:
        return

    async with locks[game_id]:
        # Count active players (non-empty seats)
        active_players = sum(1 for p in game.players if getattr(p, "name", "") and getattr(p, "name", "") != "")
        
        if active_players >= MIN_PLAYERS:
            # Start the game!
            print(f"Starting game {game_id} with {active_players} players")
            game.stage = "preflop"  # Or whatever your initial stage is
            game.lobby_timer = None
            game.game_starting = False
            
            # Start the first hand
            game.play_hand()
            
            await manager.broadcast(game_id, {
                "type": "state_update", 
                "state": game.get_game_state()
            })
        else:
            # Not enough players - reset timer
            print(f"Not enough players for game {game_id} ({active_players}/{MIN_PLAYERS})")
            game.lobby_timer = LOBBY_DURATION
            await manager.broadcast(game_id, {
                "type": "state_update",
                "state": game.get_game_state()
            })
            # Restart timer
            await start_lobby_timer(game_id)

def get_active_player_count(game: PokerGame) -> int:
    """Count how many players are actively seated"""
    return sum(1 for p in game.players if getattr(p, "name", "") and getattr(p, "name", "") != "")

# --- Routes ---
@app.post("/create_game")
async def create_game(req: CreateGameRequest):
    """Create a new poker game session with optional seat_count."""
    if len(req.player_names) < 1:
        raise HTTPException(status_code=400, detail="Need at least one human player")

    game_id = str(uuid4())[:8]
    seat_count = req.seat_count or 6

    # Prepare initial list of names: put provided names into seats 0..n-1, leave others as '' (empty)
    initial_names = req.player_names.copy()

    # Fill remaining seats with empty placeholder names (empty string)
    while len(initial_names) < seat_count:
        initial_names.append("")  # "" indicates empty seat

    game = PokerGame(initial_names)

    # Initialize lobby state
    game.stage = "lobby"
    game.lobby_timer = LOBBY_DURATION
    game.game_starting = False

    # mark any "Bot" names as bot
    for i, p in enumerate(game.players):
        if p.name == "Bot":
            p.is_bot = True
            print(f"Added Bot to seat {i}")

    games[game_id] = game
    locks[game_id] = asyncio.Lock()

    # Start lobby timer
    await start_lobby_timer(game_id)

    return {"game_id": game_id, "state": game.get_game_state()}

@app.post("/add_ai_player/{game_id}")
async def add_ai_player(game_id: str, payload: dict = Body(...)):
    """Add an AI player to an empty seat"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    seat_index = payload.get("seat_index")
    ai_name = payload.get("ai_name", "AI Player")

    async with locks[game_id]:
        if game.stage != "lobby":
            raise HTTPException(status_code=400, detail="Can only add AI players during lobby phase")

        if seat_index < 0 or seat_index >= len(game.players):
            raise HTTPException(status_code=400, detail="Invalid seat index")

        existing = game.players[seat_index]
        if existing.name and existing.name != "":
            raise HTTPException(status_code=409, detail="Seat already taken")

        # Set player as AI
        existing.name = ai_name
        existing.is_bot = True
        existing.folded = False
        existing.current_bet = 0
        if existing.chips <= 0:
            existing.chips = 1000
        existing.hand = []

        # Restart lobby timer
        await start_lobby_timer(game_id)

        await manager.broadcast(game_id, {
            "type": "state_update",
            "state": game.get_game_state()
        })

    return {"success": True, "state": game.get_game_state()}



@app.post("/start_hand/{game_id}")
async def start_hand(game_id: str):
    """Start a new hand for an existing game"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    async with locks[game_id]:
        # If we're in lobby, check if we can start
        if getattr(game, 'stage', '') == 'lobby':
            active_players = get_active_player_count(game)
            if active_players < MIN_PLAYERS:
                raise HTTPException(status_code=400, detail=f"Need at least {MIN_PLAYERS} players to start")
            
            # Cancel lobby timer and start game
            if game_id in lobby_timers:
                lobby_timers[game_id].cancel()
                del lobby_timers[game_id]
            
            game.stage = "preflop"
            game.lobby_timer = None
            game.game_starting = False
        
        game.play_hand()
        await manager.broadcast(game_id, {
            "type": "state_update",
            "state": game.get_game_state()
        })

        return {"message": "New hand started", "state": game.get_game_state()}

@app.post("/join_seat/{game_id}")
async def join_seat(game_id: str, payload: JoinSeatRequest):
    """
    Join a seat in the game during lobby phase
    """
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    player_name = payload.player_name
    seat_index = payload.seat_index

    async with locks[game_id]:
        # Check if we're in lobby phase
        if getattr(game, 'stage', '') != 'lobby':
            raise HTTPException(status_code=400, detail="Can only join seats during lobby phase")

        if seat_index < 0 or seat_index >= len(game.players):
            raise HTTPException(status_code=400, detail="Invalid seat index")

        existing = game.players[seat_index]
        # If seat occupied and not empty string -> reject
        if getattr(existing, "name", "") and getattr(existing, "name", "") != "":
            raise HTTPException(status_code=409, detail="Seat already taken")

        # Set player properties
        existing.name = player_name
        existing.is_bot = False
        existing.folded = False
        existing.current_bet = 0
        # give default buy-in if chips are 0
        if getattr(existing, "chips", 0) <= 0:
            existing.chips = 1000

        # Reset hand
        existing.hand = []

        # Restart lobby timer when someone joins
        await start_lobby_timer(game_id)

        # Broadcast updated state
        await manager.broadcast(game_id, {
            "type": "state_update",
            "state": game.get_game_state()
        })

    return {"success": True, "state": game.get_game_state()}

@app.post("/leave_seat/{game_id}")
async def leave_seat(game_id: str, payload: LeaveSeatRequest):
    """
    Leave a seat during lobby phase
    """
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    seat_index = payload.seat_index

    async with locks[game_id]:
        # Check if we're in lobby phase
        if getattr(game, 'stage', '') != 'lobby':
            raise HTTPException(status_code=400, detail="Can only leave seats during lobby phase")

        if seat_index < 0 or seat_index >= len(game.players):
            raise HTTPException(status_code=400, detail="Invalid seat index")

        player = game.players[seat_index]
        player_name = getattr(player, "name", "")
        
        if not player_name or player_name == "":
            raise HTTPException(status_code=400, detail="Seat is already empty")

        # Clear the seat
        player.name = ""
        player.is_bot = False
        player.folded = False
        player.current_bet = 0
        player.hand = []
        # Keep chips so player can rejoin with same stack?

        # Restart lobby timer when someone leaves
        await start_lobby_timer(game_id)

        # Broadcast updated state
        await manager.broadcast(game_id, {
            "type": "state_update", 
            "state": game.get_game_state()
        })

    return {"success": True, "state": game.get_game_state()}

@app.post("/action/{game_id}")
async def player_action(game_id: str, data: dict = Body(...)):
    """Execute a player's action, and trigger AI moves if it's the bot's turn."""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Don't allow actions during lobby phase
    if getattr(game, 'stage', '') == 'lobby':
        raise HTTPException(status_code=400, detail="Game is in lobby phase - cannot perform actions")

    async with locks[game_id]:
        player_index = data["player_index"]
        action = data["action"]
        raise_amount = data.get("raise_amount", 0)

        # Apply human action
        result = game.execute_action(player_index, action, raise_amount)
        state = game.get_game_state()

        await manager.broadcast(game_id, {
            "type": "state_update",
            "state": game.get_game_state()
        })

        # Log messages from human player
        messages = [f"{game.players[player_index].name} chose {action} {raise_amount if raise_amount else ''}".strip()]

        while (
            not game.game_over
            and game.current_player_index is not None
            and getattr(game.players[game.current_player_index], "is_bot", False)
        ):
            ai_player_obj = game.players[game.current_player_index]
            ai_name = ai_player_obj.name

            think_time = random.uniform(3, 5)
            await asyncio.sleep(think_time)

            ai_state = game.get_game_state()
            loop = asyncio.get_event_loop()

            # Create AI instance (MonteCarlo, Heuristic, etc.)
            ai_player = MonteCarloAI(name=ai_name, simulations=200)
            ai_decision = await loop.run_in_executor(executor, ai_player.decide, ai_state)

            move = ai_decision["move"]
            amt = ai_decision.get("raise_amount", 0)

            # Execute and log AI move
            print(f"[AI] {ai_name} chooses {move} {amt if amt else ''} after {think_time:.1f}s")
            messages.append(f"{ai_name} ({ai_player.__class__.__name__}) waited {think_time:.1f}s → {move} {amt if amt else ''}")

            game.execute_action(game.current_player_index, move, amt)
            state = game.get_game_state()

            await manager.broadcast(game_id, {
                "type": "state_update",
                "state": state
            })

        return {"result": result, "state": state, "messages": messages}

@app.get("/state/{game_id}")
async def get_state(game_id: str):
    """Return full current state of the game"""
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return {"state": game.get_game_state()}

@app.websocket("/ws/{game_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_name: str):
    # Player joins the game room
    await manager.connect(game_id, websocket)

    # Immediately send the current state
    game = games.get(game_id)
    if game:
        await manager.broadcast(game_id, {
            "type": "state_update",
            "state": game.get_game_state(viewer_name=player_name)
        })

    try:
        while True:
            # For now we don't expect messages from client
            # But you can later handle: WS actions, chat messages, etc.
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(game_id, websocket)

# Cleanup when game ends
@app.delete("/game/{game_id}")
async def cleanup_game(game_id: str):
    """Clean up a game session"""
    if game_id in games:
        if game_id in lobby_timers:
            lobby_timers[game_id].cancel()
            del lobby_timers[game_id]
        del games[game_id]
        if game_id in locks:
            del locks[game_id]
    return {"message": "Game cleaned up"}