# Direct Debate Team Agent
# One autonomous agent per team — uses LLM to reason, analyze, strategize, propose

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType


AGENT_CARD = {
    "agent_id": "team_agent_direct_debate",
    "agent_name": "Team Agent",
    "agent_type": "team_agent",
    "paradigm": "direct_debate",
    "version": "1.0.0",
    "description": "Autonomous Team Agent for Direct Debate. Uses LLM for all reasoning.",
    "url": "http://localhost:8301",
    "capabilities": {
        "solve_round": {
            "description": "LLM-driven analysis, strategy, and guess generation",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "difficulty": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "guess": {"type": "array"},
                    "analysis": {"type": "string"},
                    "strategy": {"type": "string"},
                    "reasoning": {"type": "string"},
                },
            },
        },
        "debate": {
            "description": "LLM-driven debate about strategy and standing",
            "parameters": {
                "type": "object",
                "properties": {
                    "round_number": {"type": "integer"},
                    "my_guess": {"type": "array"},
                    "my_feedback": {"type": "object"},
                    "all_results": {"type": "object"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "debate_message": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        },
    },
    "constraints_owned": ["Analysis", "Strategy", "Proposal", "Validation", "Team Debate"],
    "team_members": [],
    "can_communicate": True,
}


class TeamAgent(BaseAgent):
    """Autonomous Team Agent — Uses LLM for all puzzle-solving and debate."""

    def __init__(self, provider: str = "deepseek", team_id: str = "team_1"):
        super().__init__(
            name=f"Agent_{team_id}",
            provider=provider,
            role=AgentRole.PROPOSER,
            paradigm=ParadigmType.DIRECT_DEBATE,
            team_members=[],
            can_communicate=True,
            constraints_owned=["Analysis", "Strategy", "Proposal", "Validation", "Team Debate"],
        )
        self.team_id = team_id
        # Store peer messages for real debate context
        self.peer_messages = []  # List of {"sender": team_id, "message": str, "round": int}
        # Game reflection & learning
        self.learned_hypotheses = []  # Hypotheses learned during game (e.g., "red is in code")
        self.color_analysis = {}  # Track which colors appeared in feedback
        self.position_analysis = {}  # Track position constraints learned

    def solve_round(
        self,
        guess_history: List[Dict[str, Any]],
        difficulty: str,
        available_colors: List[str],
        num_pegs: int,
        public_leaderboard: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Autonomous solve using LLM.

        Args:
            guess_history: List of previous guesses and feedback
            difficulty: Puzzle difficulty level
            available_colors: Available colors
            num_pegs: Number of pegs in code

        Returns:
            {
                "guess": [...],
                "analysis": "...",
                "strategy": "...",
                "reasoning": "...",
            }
        """
        # Build context from guess history
        history_text = self._format_history(guess_history)

        # Build context from peer messages (A2A debate)
        peer_intel = self._format_peer_intel()

        # Build competitive context from PUBLIC LEADERBOARD (feedback scores only, guesses private)
        leaderboard_text = self._format_leaderboard(public_leaderboard)

        # Build knowledge from reflection & learning
        learned_text = self._format_learned_knowledge()

        prompt = f"""You are {self.team_id}, solving a Mastermind puzzle competitively.

PUZZLE STATE:
- Available colors: {available_colors}
- Code length: {num_pegs} pegs
- Difficulty: {difficulty}

YOUR PAST GUESSES:
{history_text if history_text else "No previous guesses yet."}

YOUR LEARNED KNOWLEDGE (patterns discovered):
{learned_text if learned_text else "No patterns learned yet - this is our first round."}

PUBLIC LEADERBOARD (feedback scores only - guesses are private):
{leaderboard_text if leaderboard_text else "No public scores yet."}

PEER DEBATE MESSAGES (from A2A communication):
{peer_intel if peer_intel else "No peer messages yet."}

YOUR COMPETITIVE STRATEGY (use your learned knowledge!):
1. ASSESS: Where are we on the leaderboard? What patterns have we learned?
2. LEVERAGE: Use learned hypotheses to eliminate wrong colors/positions
3. PROPOSE: Generate a guess that tests new hypotheses while using confirmed knowledge

Return ONLY valid JSON (no markdown):
{{
  "analysis": "What we learned and how peers influence us...",
  "strategy": "Our competitive approach...",
  "guess": ["color1", "color2", ...],
  "reasoning": "Why this guess gives us advantage..."
}}

CONSTRAINTS:
- guess must have exactly {num_pegs} colors
- Each color must be from: {available_colors}
- Colors can be repeated
- Never repeat a previous guess
"""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)

            guess = result.get("guess", [])

            # Validate the guess
            if not self._is_valid_guess(guess, available_colors, num_pegs, guess_history):
                # If invalid, use fallback
                guess = self._fallback_guess(available_colors, num_pegs, guess_history)

            return {
                "guess": guess,
                "analysis": result.get("analysis", "Analysis failed"),
                "strategy": result.get("strategy", "Strategy failed"),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            print(f"[{self.team_id}] LLM error in solve_round: {e}")
            guess = self._fallback_guess(available_colors, num_pegs, guess_history)
            return {
                "guess": guess,
                "analysis": f"Error: {str(e)}",
                "strategy": "Fallback strategy",
                "reasoning": "LLM call failed",
            }

    def debate(
        self,
        round_number: int,
        my_guess: List[str],
        my_feedback: Dict[str, Any],
        all_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Autonomous debate using LLM — respond to peer strategies.

        Args:
            round_number: Current round
            my_guess: This team's guess
            my_feedback: Feedback for this team's guess
            all_results: All teams' results

        Returns:
            {
                "debate_message": "...",
                "confidence": 0.0-1.0,
            }
        """
        # Format all results for LLM
        results_text = "\n".join([
            f"{team_id}: guess={result.get('guess')}, "
            f"feedback=pegs:{result.get('feedback', {}).get('correct_pegs', 0)} "
            f"pos:{result.get('feedback', {}).get('correct_positions', 0)}"
            for team_id, result in all_results.items()
        ])

        # Format peer messages for debate context
        peer_messages_text = self._format_peer_messages_for_debate(round_number)

        prompt = f"""You are {self.team_id} in a competitive puzzle-solving game.

ROUND {round_number} RESULTS:
{results_text}

YOUR PERFORMANCE:
- Guess: {my_guess}
- Correct pegs: {my_feedback.get('correct_pegs', 0)}
- Correct positions: {my_feedback.get('correct_positions', 0)}

PEER STATEMENTS THIS ROUND:
{peer_messages_text if peer_messages_text else "(No peer statements yet)"}

YOUR RESPONSE — ENGAGE DIRECTLY:
1. Address peer claims: do you agree/disagree with their strategies?
2. Justify your approach: why is yours better/different?
3. Competitive stance: are we leading, catching up, or pivoting?

Return ONLY valid JSON:
{{
  "debate_message": "Direct response to peers with counter-arguments and justification...",
  "confidence": 0.0-1.0
}}

Be direct, competitive, and respond to specific peer claims. Don't just announce your strategy—argue why it's superior."""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)

            confidence = result.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            confidence = max(0.0, min(1.0, float(confidence)))

            return {
                "debate_message": result.get("debate_message", "Unable to analyze standing"),
                "confidence": confidence,
            }
        except Exception as e:
            print(f"[{self.team_id}] LLM error in debate: {e}")
            my_pegs = my_feedback.get("correct_pegs", 0)
            my_positions = my_feedback.get("correct_positions", 0)
            return {
                "debate_message": f"Round {round_number}: Status unclear (pegs={my_pegs}, pos={my_positions})",
                "confidence": 0.5,
            }

    def receive_peer_message(self, sender: str, message: str, round_num: int) -> None:
        """Store peer message for debate context."""
        self.peer_messages.append({
            "sender": sender,
            "message": message,
            "round": round_num,
        })

    def _reflect_on_round(self, round_num: int, guess: List[str], feedback: Dict[str, Any]) -> None:
        """Analyze feedback and build learned hypotheses.

        This is where agents learn patterns and build knowledge:
        - Track which colors appear in correct guesses
        - Identify position constraints
        - Form hypotheses about the code
        """
        pegs = feedback.get("correct_pegs", 0)
        positions = feedback.get("correct_positions", 0)

        # Analyze color appearances
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1

        # If we got correct_pegs feedback, those colors are likely in the code
        if pegs > 0:
            colors_in_guess = set(guess)

            # Hypothesis: Colors that appeared when we got positive feedback are PROBABLY in code
            if not any(h.startswith(f"R{round_num}: Colors in code") for h in self.learned_hypotheses):
                hypothesis = f"R{round_num}: {pegs} colors from {guess} are in code (feedback: {pegs}p {positions}pos)"
                self.learned_hypotheses.append(hypothesis)

        # Position analysis: If we got positions right, lock those
        if positions > 0:
            hypothesis = f"R{round_num}: {positions} colors locked in positions (feedback: {pegs}p {positions}pos). Guess: {guess}"
            self.learned_hypotheses.append(hypothesis)

        # If we got 0 pegs, we learned which colors are NOT in code
        if pegs == 0:
            wrong_colors = ", ".join(guess)
            hypothesis = f"R{round_num}: Colors NOT in code: {wrong_colors}"
            self.learned_hypotheses.append(hypothesis)

        # Track color frequency
        for i, color in enumerate(guess):
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1
            if pegs > 0:
                self.color_analysis[color]["correct_feedback"] += 1

    def _format_learned_knowledge(self) -> str:
        """Format learned hypotheses and analysis for LLM context."""
        if not self.learned_hypotheses and not self.color_analysis:
            return ""

        lines = []
        lines.append("LEARNED PATTERNS & HYPOTHESES:")

        # Add hypotheses
        if self.learned_hypotheses:
            for hyp in self.learned_hypotheses[-5:]:  # Last 5 learnings
                lines.append(f"  • {hyp}")

        # Add color frequency analysis
        if self.color_analysis:
            high_confidence_colors = [
                c for c, stats in self.color_analysis.items()
                if stats["correct_feedback"] >= 2
            ]
            if high_confidence_colors:
                lines.append(f"  • HIGH CONFIDENCE colors (appeared in correct feedback): {high_confidence_colors}")

        return "\n".join(lines)

    def _format_leaderboard(self, public_leaderboard: List[Dict[str, Any]]) -> str:
        """Format public leaderboard (feedback scores only, no guesses)."""
        if not public_leaderboard:
            return ""

        lines = []
        team_best_scores = {}

        # Track best score per team
        for entry in public_leaderboard:
            team = entry.get("team_id", "unknown")
            fb = entry.get("feedback", {})
            pegs = fb.get("correct_pegs", 0)
            pos = fb.get("correct_positions", 0)
            solved = entry.get("solved", False)

            if team not in team_best_scores:
                team_best_scores[team] = (pegs, pos)
            else:
                # Update if better (more pegs, or same pegs with more positions)
                old_p, old_pos = team_best_scores[team]
                if pegs > old_p or (pegs == old_p and pos > old_pos):
                    team_best_scores[team] = (pegs, pos)

            if solved:
                lines.append(f"{team}: {pegs}p {pos}pos ✅ SOLVED")

        # Show current standings
        if team_best_scores:
            lines.append("\nCurrent Standings (best score per team):")
            for team in sorted(team_best_scores.keys()):
                pegs, pos = team_best_scores[team]
                marker = "⭐" if team == self.team_id else ""
                lines.append(f"  {team}: {pegs}p {pos}pos {marker}")

        return "\n".join(lines)

    def _format_peer_intel(self) -> str:
        """Format recent peer messages as competitive intelligence."""
        if not self.peer_messages:
            return ""

        lines = []
        for msg in self.peer_messages[-6:]:  # Last 6 messages
            sender = msg.get("sender", "unknown")
            round_num = msg.get("round", "?")
            message = msg.get("message", "")
            lines.append(f"[{sender} R{round_num}] {message}")

        return "\n".join(lines)

    def _format_peer_messages_for_debate(self, current_round: int) -> str:
        """Format this round's peer messages for debate response."""
        this_round_msgs = [m for m in self.peer_messages if m.get("round") == current_round]

        if not this_round_msgs:
            return ""

        lines = []
        for msg in this_round_msgs:
            sender = msg.get("sender", "unknown").replace("agent_", "")
            message = msg.get("message", "")
            lines.append(f"{sender}: \"{message}\"")

        return "\n".join(lines)

    def _format_history(self, guess_history: List[Dict[str, Any]]) -> str:
        """Format guess history for LLM context."""
        if not guess_history:
            return ""

        lines = []
        for entry in guess_history:
            guess = entry.get("guess", [])
            feedback = entry.get("feedback", {})
            pegs = feedback.get("correct_pegs", 0)
            positions = feedback.get("correct_positions", 0)
            lines.append(f"Round {entry.get('round')}: {guess} → {pegs} pegs, {positions} positions")

        return "\n".join(lines)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        try:
            # Look for JSON block
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start < end:
                    json_str = response[start:end]
                    return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return {}

    def _is_valid_guess(
        self,
        guess: List[str],
        available_colors: List[str],
        num_pegs: int,
        guess_history: List[Dict[str, Any]],
    ) -> bool:
        """Check if guess is valid."""
        if not isinstance(guess, list):
            return False
        if len(guess) != num_pegs:
            return False
        for color in guess:
            if color not in available_colors:
                return False

        prev_guesses = [g.get("guess", []) for g in guess_history]
        if guess in prev_guesses:
            return False

        return True

    def _fallback_guess(
        self,
        available_colors: List[str],
        num_pegs: int,
        guess_history: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate a simple fallback guess when LLM fails."""
        if not guess_history:
            return available_colors[:num_pegs]

        last_guess = guess_history[-1].get("guess", [])
        new_guess = []

        for i in range(num_pegs):
            if i < len(last_guess):
                current_color = last_guess[i]
                try:
                    current_idx = available_colors.index(current_color)
                    next_idx = (current_idx + 1) % len(available_colors)
                    new_guess.append(available_colors[next_idx])
                except ValueError:
                    new_guess.append(available_colors[i % len(available_colors)])
            else:
                new_guess.append(available_colors[i % len(available_colors)])

        return new_guess

    def run_autonomous_puzzle(self, puzzle: Dict[str, Any], registry_url: str, orchestrator_url: str = "") -> None:
        """Run autonomous puzzle solving loop.

        Agent discovers peers, debates, and submits guesses to orchestrator.
        """
        self.registry_url = registry_url
        self.orchestrator_url = orchestrator_url
        self.puzzle = puzzle
        self.available_colors = puzzle.get("available_colors", [])
        self.num_pegs = puzzle.get("pegs", 4)
        self.difficulty = puzzle.get("difficulty", "easy")

        print(f"[{self.team_id}] Starting autonomous puzzle solving...")

        guess_history = []
        public_leaderboard = []  # Track public feedback scores
        max_rounds = 16

        for round_num in range(1, max_rounds + 1):
            print(f"\n[{self.team_id}] Round {round_num}")

            # Step 1: Solve this round (with public leaderboard context)
            result = self.solve_round(
                guess_history=guess_history,
                difficulty=self.difficulty,
                available_colors=self.available_colors,
                num_pegs=self.num_pegs,
                public_leaderboard=public_leaderboard,  # Public feedback for strategy
            )

            guess = result.get("guess", [])
            if not guess:
                print(f"[{self.team_id}] Failed to generate valid guess")
                break

            print(f"[{self.team_id}] Proposed: {guess}")

            # Step 2: Submit guess to orchestrator
            feedback = self._submit_guess(guess)
            if feedback and feedback.get("valid", False):
                guess_result = feedback.get("feedback", {})
                guess_history.append({
                    "round": round_num,
                    "guess": guess,
                    "feedback": guess_result,
                })

                # Step 2b: REFLECT on the feedback to learn patterns
                self._reflect_on_round(round_num, guess, guess_result)

                # Update public leaderboard (only feedback, no guesses)
                if "public_leaderboard" in feedback:
                    public_leaderboard = feedback.get("public_leaderboard", [])

                # Check if solved
                if feedback.get("solved", False):
                    print(f"[{self.team_id}] ✓ SOLVED!")
                    break
            else:
                print(f"[{self.team_id}] Guess rejected: {feedback}")
                break

            # Step 3: Discover peers and debate (include feedback for context)
            peers = self._discover_peers()
            if peers:
                self._debate_with_peers(peers, round_num, guess, feedback.get("feedback", {}))

    def _submit_guess(self, guess: List[str]) -> Dict[str, Any]:
        """Submit guess to orchestrator for validation."""
        if not self.orchestrator_url:
            return {"valid": False, "error": "No orchestrator URL"}

        try:
            import httpx
            resp = httpx.post(
                f"{self.orchestrator_url}/submit_guess",
                json={
                    "team_id": self.team_id,
                    "guess": guess,
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                return {"valid": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            print(f"[{self.team_id}] Failed to submit guess: {e}")
            return {"valid": False, "error": str(e)}

    def _discover_peers(self) -> Dict[str, str]:
        """Discover other team agents from registry."""
        if not self.registry_url:
            return {}

        try:
            import httpx
            resp = httpx.get(f"{self.registry_url}/agents", timeout=5.0)
            if resp.status_code != 200:
                return {}

            data = resp.json()
            agents_list = data.get("payload", {}).get("agents", [])
            peers = {}

            for agent_data in agents_list:
                agent_id = agent_data.get("agent_id", "")
                url = agent_data.get("url", "")

                # Find agents from other teams
                if "team_" in agent_id and self.team_id not in agent_id:
                    peers[agent_id] = url

            return peers
        except Exception as e:
            print(f"[{self.team_id}] Failed to discover peers: {e}")
            return {}

    def _debate_with_peers(self, peers: Dict[str, str], round_num: int, my_guess: List[str], feedback: Dict[str, Any] = None) -> None:
        """Send debate message to peers via A2A — engage competitively.

        Args:
            peers: Dict of peer_id → peer_url
            round_num: Current round
            my_guess: This round's guess
            feedback: Feedback received for this guess
        """
        if not peers:
            return

        # Include feedback in debate if available
        feedback_str = ""
        if feedback:
            pegs = feedback.get("correct_pegs", 0)
            positions = feedback.get("correct_positions", 0)
            feedback_str = f"Our guess got {pegs} correct pegs and {positions} correct positions."

        # Format recent peer messages for context
        recent_peer_msgs = "\n".join([
            f"- {m.get('sender', 'unknown').replace('agent_', '')}: {m.get('message', '')}"
            for m in self.peer_messages[-3:]  # Last 3 peer messages
        ]) if self.peer_messages else "(No prior messages)"

        prompt = f"""You are {self.team_id} in round {round_num} of competitive Mastermind.

YOUR MOVE:
- Guess: {my_guess}
{feedback_str}

RECENT PEER MESSAGES:
{recent_peer_msgs}

COMPOSE COMPETITIVE RESPONSE:
1. Reference specific peer claims if they made any
2. Argue why your strategy is superior (or acknowledge if theirs is better)
3. Be direct and engaging—this is real-time competition

Keep it 1-2 sentences, competitive but respectful.

Return ONLY JSON:
{{"debate_message": "Your competitive response..."}}
"""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)
            message = result.get("debate_message", f"Round {round_num}: {my_guess}")

            print(f"[{self.team_id}] Debate: {message}")

            # Send to each peer
            import httpx
            from communication.a2a_message import A2AMessage

            for peer_id, peer_url in peers.items():
                msg = A2AMessage.request(
                    sender_id=f"agent_{self.team_id}",
                    receiver_id=peer_id,
                    action="debate_statement",
                    payload={"message": message, "round": round_num},
                )

                try:
                    httpx.post(f"{peer_url}/receive_message", json=msg.to_dict(), timeout=5.0)
                except Exception as e:
                    print(f"[{self.team_id}] Failed to send to {peer_id}: {e}")

        except Exception as e:
            print(f"[{self.team_id}] Debate failed: {e}")

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state."""
        return state
