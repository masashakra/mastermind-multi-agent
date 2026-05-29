# LangGraph Orchestration Layer
# Manages game rounds, Boss agent, guess submission, and feedback
# COMPLETELY SEPARATE from A2A communication

from typing import Dict, Any, Optional, List
from communication.protocol import A2ACommunicationLayer
from agents.boss_a2a import BossA2AAgent


class GameRoundState:
    """Represents the state of a single game round."""

    def __init__(self, round_num: int, puzzle: Dict[str, Any], guess_history: List[Dict]):
        self.round_num = round_num
        self.puzzle = puzzle
        self.guess_history = guess_history
        self.proposed_guess: Optional[List[str]] = None
        self.feedback: Optional[Dict[str, Any]] = None
        self.boss_result: Optional[Dict[str, Any]] = None
        self.is_solved = False
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_num,
            "puzzle_id": self.puzzle.get("puzzle_id"),
            "proposed_guess": self.proposed_guess,
            "feedback": self.feedback,
            "is_solved": self.is_solved,
            "error": self.error,
            "guess_history_length": len(self.guess_history)
        }


class LangGraphMastermindOrchestrator:
    """
    LangGraph-based Game Orchestration.

    Manages:
    - Game rounds (higher level)
    - Boss agent lifecycle
    - Guess submission to game engine
    - Feedback collection and propagation
    - Win/loss detection

    Does NOT:
    - Handle A2A protocol (that's Communication Layer's job)
    - Manage agent task assignment (that's Boss's job)
    - Define agent capabilities (that's Agent Cards' job)
    """

    def __init__(self, provider: str = "groq"):
        """Initialize LangGraph orchestrator.

        Args:
            provider: LLM provider for Boss and workers
        """
        self.provider = provider

        # Create shared communication layer for all agents
        self.comm_layer = A2ACommunicationLayer()

        # Create Boss agent (will create workers via A2A)
        self.boss = BossA2AAgent(
            provider=provider,
            comm_layer=self.comm_layer
        )

        # Game state tracking
        self.current_puzzle: Optional[Dict[str, Any]] = None
        self.round_history: List[GameRoundState] = []
        self.total_guesses = 0
        self.max_rounds = 8

    def execute_game(self, puzzle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full game until solved or max rounds reached.

        Args:
            puzzle: Puzzle dict with secret_code and metadata

        Returns:
            Game result with statistics
        """
        self.current_puzzle = puzzle
        self.round_history = []
        self.total_guesses = 0

        print(f"\n{'='*70}")
        print(f"MASTERMIND GAME: {puzzle['puzzle_id']}")
        print(f"Secret: {puzzle['secret_code']}")
        print(f"{'='*70}\n")

        for round_num in range(1, self.max_rounds + 1):
            round_state = GameRoundState(
                round_num=round_num,
                puzzle=puzzle,
                guess_history=self._build_guess_history()
            )

            try:
                # LangGraph orchestration step 1: Ask Boss for a guess
                print(f"Round {round_num}...", end=" ", flush=True)

                boss_result = self._ask_boss_for_guess(round_state)
                round_state.boss_result = boss_result
                round_state.proposed_guess = boss_result.get("guess", [])

                print(f"Guess: {round_state.proposed_guess}", end="", flush=True)

                # LangGraph orchestration step 2: Submit guess to game engine
                feedback = self._submit_guess_to_engine(
                    round_state.proposed_guess,
                    puzzle
                )
                round_state.feedback = feedback
                round_state.total_guesses = feedback.get("guess_number", 0)
                self.total_guesses = round_state.total_guesses

                print(f", Feedback: {feedback['feedback']}")

                # LangGraph orchestration step 3: Check if solved
                if feedback.get("solved"):
                    round_state.is_solved = True
                    self.round_history.append(round_state)
                    return self._game_won(round_state)

                # Store for next round
                self.round_history.append(round_state)

            except Exception as e:
                round_state.error = str(e)
                round_state.is_solved = False
                self.round_history.append(round_state)
                print(f"ERROR: {str(e)}")
                return self._game_failed(round_state)

        # Max rounds reached without solving
        return self._game_lost()

    def _ask_boss_for_guess(self, round_state: GameRoundState) -> Dict[str, Any]:
        """
        Ask Boss agent to generate a guess (Boss does A2A task assignment).

        Args:
            round_state: Current round state

        Returns:
            Boss result with guess and agent results
        """
        game_state = {
            "puzzle": round_state.puzzle,
            "guess_history": round_state.guess_history,
            "difficulty": round_state.puzzle.get("difficulty", "easy")
        }

        return self.boss.orchestrate_round(game_state)

    def _submit_guess_to_engine(self, guess: List[str], puzzle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit guess to game engine (not A2A - this is game interaction).

        Args:
            guess: The guess to submit
            puzzle: The puzzle being solved

        Returns:
            Feedback from game engine
        """
        from game_engine import GameEngine

        # For this game, we simulate the engine
        # In real scenario, this would be a gRPC/HTTP call to game service
        engine = GameEngine(
            secret_code=puzzle["secret_code"],
            difficulty=puzzle["difficulty"]
        )

        # Apply all previous guesses to engine
        for prev_round in self.round_history:
            if prev_round.proposed_guess:
                engine.submit_guess(prev_round.proposed_guess)

        # Submit current guess
        feedback = engine.submit_guess(guess)
        return feedback

    def _build_guess_history(self) -> List[Dict[str, Any]]:
        """Build guess history from round history."""
        return [
            {
                "guess": round_state.proposed_guess,
                "feedback": round_state.feedback
            }
            for round_state in self.round_history
            if round_state.proposed_guess and round_state.feedback
        ]

    def _game_won(self, final_round: GameRoundState) -> Dict[str, Any]:
        """Handle game won state."""
        print(f"\n✓ SOLVED in {self.total_guesses} guesses!\n")

        return {
            "status": "won",
            "puzzle_id": self.current_puzzle["puzzle_id"],
            "secret_code": self.current_puzzle["secret_code"],
            "guesses_used": self.total_guesses,
            "max_guesses": self.max_rounds,
            "final_guess": final_round.proposed_guess,
            "rounds_executed": len(self.round_history),
            "a2a_messages_total": len(self.comm_layer.message_history),
            "round_history": [r.to_dict() for r in self.round_history]
        }

    def _game_lost(self) -> Dict[str, Any]:
        """Handle game lost state (max rounds exceeded)."""
        print(f"\n✗ NOT SOLVED - Max rounds ({self.max_rounds}) exceeded\n")

        return {
            "status": "lost",
            "reason": "max_rounds_exceeded",
            "puzzle_id": self.current_puzzle["puzzle_id"],
            "secret_code": self.current_puzzle["secret_code"],
            "guesses_used": self.total_guesses,
            "max_guesses": self.max_rounds,
            "rounds_executed": len(self.round_history),
            "a2a_messages_total": len(self.comm_layer.message_history),
            "round_history": [r.to_dict() for r in self.round_history]
        }

    def _game_failed(self, error_round: GameRoundState) -> Dict[str, Any]:
        """Handle game failed state (error occurred)."""
        print(f"\n✗ FAILED - {error_round.error}\n")

        return {
            "status": "failed",
            "error": error_round.error,
            "puzzle_id": self.current_puzzle["puzzle_id"],
            "secret_code": self.current_puzzle["secret_code"],
            "guesses_used": self.total_guesses,
            "max_guesses": self.max_rounds,
            "rounds_executed": len(self.round_history),
            "a2a_messages_total": len(self.comm_layer.message_history),
            "round_history": [r.to_dict() for r in self.round_history]
        }

    def get_game_statistics(self) -> Dict[str, Any]:
        """Get statistics about the game."""
        return {
            "total_puzzles_attempted": 1,
            "total_rounds": len(self.round_history),
            "total_a2a_messages": len(self.comm_layer.message_history),
            "boss_stats": self.boss.get_stats(),
            "comm_layer_stats": {
                "agents_registered": len(self.comm_layer.agents),
                "message_history_count": len(self.comm_layer.message_history)
            }
        }

    def get_round_history(self) -> List[Dict[str, Any]]:
        """Get history of all rounds."""
        return [r.to_dict() for r in self.round_history]
