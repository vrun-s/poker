"use client";

import { useState } from "react";

type Player = {
  name: string;
  chips: number;
  current_bet: number;
  folded: boolean;
  hand: string[];
};

type GameState = {
  stage: string;
  pot: number;
  current_bet: number;
  community_cards: string[];
  current_player: string | null;
  current_player_index: number | null;
  legal_actions: string[];
  game_over: boolean;
  winner: string | null;
  dealer: string;
  players: Player[];
};

export default function Page() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerNames, setPlayerNames] = useState("Alice,Bob");
  const [raiseAmount, setRaiseAmount] = useState(20);
  const [loading, setLoading] = useState(false);
  const apiBase = "http://localhost:8000";

  async function createGame() {
    setLoading(true);
    const res = await fetch(`${apiBase}/create_game`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_names: playerNames.split(",") }),
    });
    const data = await res.json();
    setGameId(data.game_id);
    setGameState(data.state);
    setLoading(false);
  }

  async function startHand() {
    if (!gameId) return;
    setLoading(true);
    const res = await fetch(`${apiBase}/start_hand/${gameId}`, { method: "POST" });
    const data = await res.json();
    setGameState(data.state);
    setLoading(false);
  }

  async function doAction(action: string) {
    if (!gameId || !gameState) return;
    const currentIndex = gameState.current_player_index;
    setLoading(true);
    const res = await fetch(`${apiBase}/action/${gameId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_index: currentIndex,
        action,
        raise_amount: raiseAmount,
      }),
    });
    const data = await res.json();
    setGameState(data.state);
    setLoading(false);
  }

  return (
    <main className="p-6 flex flex-col gap-6 text-white bg-gray-900 min-h-screen">
      <h1 className="text-3xl font-bold text-center">♠ Poker Game</h1>

      {!gameId ? (
        <div className="flex flex-col items-center gap-3">
          <input
            className="p-2 text-black rounded"
            value={playerNames}
            onChange={(e) => setPlayerNames(e.target.value)}
            placeholder="Comma-separated player names"
          />
          <button
            onClick={createGame}
            className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded"
            disabled={loading}
          >
            Create Game
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <h2 className="text-lg">Game ID: {gameId}</h2>
          <button
            onClick={startHand}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
            disabled={loading}
          >
            Start New Hand
          </button>

          {gameState && (
            <div className="w-full max-w-3xl bg-gray-800 p-4 rounded-lg">
              <div className="mb-4">
                <p>Stage: {gameState.stage}</p>
                <p>Pot: 💰 {gameState.pot}</p>
                <p>Current Bet: {gameState.current_bet}</p>
                <p>Dealer: {gameState.dealer}</p>
                {gameState.game_over && (
                  <p className="text-green-400">🏆 Winner: {gameState.winner}</p>
                )}
              </div>

              <div className="mb-4">
                <h3 className="font-semibold">Community Cards:</h3>
                <div className="flex gap-2">
                  {gameState.community_cards.map((card, i) => (
                    <span
                      key={i}
                      className="bg-gray-700 px-3 py-1 rounded border border-gray-500"
                    >
                      {card}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-4">
                <h3 className="font-semibold mb-2">Players:</h3>
                <div className="flex flex-col gap-2">
                  {gameState.players.map((p, i) => (
                    <div
                      key={i}
                      className={`p-2 rounded border ${
                        i === gameState.current_player_index
                          ? "border-yellow-400"
                          : "border-gray-600"
                      }`}
                    >
                      <p>
                        {p.name} — 💵 {p.chips}{" "}
                        {p.folded && <span className="text-red-400">(Folded)</span>}
                      </p>
                      <p>Current Bet: {p.current_bet}</p>
                      <div className="flex gap-2">
                        {p.hand.map((c, j) => (
                          <span
                            key={j}
                            className="bg-gray-700 px-2 py-1 rounded border border-gray-500"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {gameState.current_player && !gameState.game_over && (
                <div className="flex flex-col items-center gap-3">
                  <p className="text-yellow-300">
                    🎯 Current Turn: {gameState.current_player}
                  </p>
                  <div className="flex gap-3 flex-wrap justify-center">
                    {gameState.legal_actions.includes("check") && (
                      <button
                        onClick={() => doAction("check")}
                        className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded"
                        disabled={loading}
                      >
                        Check
                      </button>
                    )}
                    {gameState.legal_actions.includes("call") && (
                      <button
                        onClick={() => doAction("call")}
                        className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
                        disabled={loading}
                      >
                        Call
                      </button>
                    )}
                    {gameState.legal_actions.includes("fold") && (
                      <button
                        onClick={() => doAction("fold")}
                        className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
                        disabled={loading}
                      >
                        Fold
                      </button>
                    )}
                    {gameState.legal_actions.includes("raise") && (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          className="w-20 p-1 text-black rounded"
                          value={raiseAmount}
                          onChange={(e) => setRaiseAmount(Number(e.target.value))}
                        />
                        <button
                          onClick={() => doAction("raise")}
                          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded"
                          disabled={loading}
                        >
                          Raise
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
