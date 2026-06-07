# Agent 1: Analyzer-Strategist
# Extracts constraints AND develops strategy based on competitive intelligence

from typing import List, Dict, Any, Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "analyzer_strategist_judge_mediated",
    "agent_name": "Analyzer-Strategist",
    "agent_type": "analyzer_strategist",
    "paradigm": "judge_mediated",
    "version": "1.0.0",
    "description": "Agent 1: Analyzes constraints and develops winning strategy",
    "capabilities": {
        "analyze_and_strategize": {
            "description": "Extract constraints and develop strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "last_feedback": {"type": "object"},
                    "competitive_analysis": {"type": "object"},
                    "difficulty": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                }
            },
            "returns": {
                "type": "object",
                "description": "Constraints and strategy"
            }
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class AnalyzerStrategistAgent(BaseAgent):
    """Agent 1: Analyzer-Strategist

    Responsibilities:
    1. Extract constraints from game history
    2. Consider competitive status
    3. Develop winning strategy
    4. Pass clear strategy to Proposer

    MEMORY: This agent maintains its own analysis_history (stateful).
    Memory grows with each round as constraints are discovered.
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="AnalyzerStrategist",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.ANALYZER,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

        # ⭐ AGENT-MANAGED MEMORY: Initialize analysis history
        self.analysis_history: List[Dict[str, Any]] = []  # Per-agent memory!

    def _check_color_consistency(self, guess_history: List[List[str]],
                                 feedback_history: List[Dict[str, int]],
                                 identified_colors: List[str]) -> Dict[str, Any]:
        """⭐ PHASE 2: Detect when color identification contradicts feedback.

        Problem: If we tested 4 colors and got 3P feedback, one tested color is WRONG!
        Current code assumes all 4 are in puzzle, which causes infinite loops.

        This detects the inconsistency and triggers recovery mode.
        """
        if not guess_history or not feedback_history:
            return {"is_consistent": True}

        # Check each round's feedback
        for i, (guess, feedback) in enumerate(zip(guess_history, feedback_history)):
            if not isinstance(guess, list) or not isinstance(feedback, dict):
                continue

            num_tested = len(set(guess))
            pegs = feedback.get("correct_pegs", 0)

            # KEY INSIGHT: If we tested N different colors but only N-1 are correct (pegs < N),
            # then 1 of the tested colors is WRONG!
            if pegs < num_tested and num_tested == 4:
                print(f"[Color Consistency] ⚠️ ANOMALY at round {i+1}:")
                print(f"   Tested 4 colors: {set(guess)}")
                print(f"   Got {pegs}P feedback (only {pegs} are correct)")
                print(f"   → ONE of tested colors is WRONG!")
                print(f"   → Current color_in = {identified_colors}")

                return {
                    "is_consistent": False,
                    "issue": "color_count_mismatch",
                    "round": i + 1,
                    "tested_colors": list(set(guess)),
                    "tested_count": num_tested,
                    "correct_count": pegs,
                    "wrong_color_count": num_tested - pegs,
                    "identified_colors": identified_colors
                }

        return {"is_consistent": True}

    def _generate_color_hypotheses(self, guess: List[str], feedback: Dict[str, int],
                                   available_colors: List[str]) -> List[Dict[str, Any]]:
        """⭐ PHASE 2: Generate alternative color sets when feedback is inconsistent.

        When we detect that 1 of 4 tested colors is wrong, generate hypotheses
        for which color might be wrong and what might replace it.

        ⭐ PRIORITY: Score hypotheses by likelihood (position-based)
        - Colors at position 1-2 more likely to be wrong than 0 or 3
        """
        pegs = feedback.get("correct_pegs", 0)
        tested_colors = list(set(guess))

        if len(tested_colors) != 4 or pegs >= 4:
            return []

        # One color is wrong - generate hypotheses
        untested = [c for c in available_colors if c not in tested_colors]

        # ⭐ PRIORITY SCORING: By position likelihood
        position_scores = {0: 1, 1: 3, 2: 3, 3: 2}  # Middle positions more likely wrong

        hypotheses = []
        for wrong_color_idx, wrong_color in enumerate(tested_colors):
            # Find position of this color in the guess
            color_positions = [i for i, c in enumerate(guess) if c == wrong_color]
            avg_position = sum(color_positions) / len(color_positions) if color_positions else 1.5
            position_score = position_scores.get(int(avg_position), 1.5)

            for replacement in untested:
                hypothesis_colors = [
                    replacement if c == wrong_color else c
                    for c in guess  # ⭐ FIX: Use guess directly, not tested_colors set
                ]
                hypotheses.append({
                    "assumption": f"{wrong_color} is WRONG, {replacement} is IN",
                    "colors": hypothesis_colors[:4],  # ⭐ Preserve order
                    "wrong_color": wrong_color,
                    "replacement": replacement,
                    "score": position_score,  # ⭐ NEW: Priority score
                    "confidence": 0.5 if replacement in untested else 0.0
                })

        # ⭐ SORT BY SCORE (highest first) then by replacement availability
        hypotheses.sort(key=lambda h: (-h["score"], untested.index(h["replacement"]) if h["replacement"] in untested else 999))

        print(f"[Color Hypotheses] Generated {len(hypotheses)} hypotheses (prioritized by position)")
        if hypotheses:
            print(f"  #1 (priority): {hypotheses[0]['assumption']} → colors={hypotheses[0]['colors']}")

        return hypotheses

    def _detect_locked_positions(self, guess_history: List[List[str]],
                                  feedback_history: List[Dict[str, int]]) -> Dict[str, str]:
        """⭐ EXPLICIT POSITION DETECTION: Infer locked positions from guess patterns.

        Algorithm: If a color at position N appears across multiple guesses and
        the feedback consistently improves or stays high when that color is there,
        it's likely locked to that position.
        """
        print(f"[_detect_locked_positions] Called with {len(guess_history)} guesses")
        if not guess_history or len(guess_history) < 2:
            print(f"[_detect_locked_positions] Not enough guesses ({len(guess_history)}), returning empty")
            return {}

        locked = {}
        num_pegs = len(guess_history[0]) if guess_history else 4

        # For each position
        for pos in range(num_pegs):
            position_history = []

            # Collect all colors tried at this position with their feedback
            for i, guess in enumerate(guess_history):
                if i < len(feedback_history):
                    color_at_pos = guess[pos]
                    feedback = feedback_history[i]
                    correct_pos = feedback.get("correct_positions", 0)
                    correct_pegs = feedback.get("correct_pegs", 0)
                    position_history.append({
                        "color": color_at_pos,
                        "pegs": correct_pegs,
                        "pos": correct_pos,
                    })

            # Find if any color appears multiple times at this position
            color_counts = {}
            for entry in position_history:
                color = entry["color"]
                if color not in color_counts:
                    color_counts[color] = []
                color_counts[color].append(entry)

            # Check if a color appeared 2+ times and ALWAYS gave better/same feedback
            for color, appearances in color_counts.items():
                if len(appearances) >= 2:
                    # Check if all appearances had high feedback (3+ correct positions)
                    avg_pos = sum(a["pos"] for a in appearances) / len(appearances)
                    print(f"[_detect_locked_positions] Pos {pos}, Color {color}: {len(appearances)} appearances, avg_pos={avg_pos:.1f}")
                    if avg_pos >= 2:  # If average is 2+ positions correct
                        # Check consistency: does removing this color drop feedback?
                        all_consistent = all(a["pos"] >= 2 for a in appearances)
                        print(f"[_detect_locked_positions]   → All consistent (pos>=2): {all_consistent}")
                        if all_consistent:
                            locked[str(pos)] = color
                            print(f"[_detect_locked_positions]   → LOCKED position {pos}={color}")

        print(f"[_detect_locked_positions] Final result: {locked}")
        return locked

    def _compute_cumulative_constraints(self) -> Dict[str, Any]:
        """Compute constraints accumulated across all previous rounds.

        Returns: {colors_in: [...], colors_out: [...], locked_positions: {...}}
        """
        cumulative_in = set()
        cumulative_out = set()
        cumulative_locked = {}

        # Merge all constraints from history
        for entry in self.analysis_history:
            # Accumulate colors confirmed IN
            colors_in = entry.get("colors_in", [])
            if colors_in:
                cumulative_in.update(colors_in)

            # Accumulate colors confirmed OUT
            colors_out = entry.get("colors_out", [])
            if colors_out:
                cumulative_out.update(colors_out)

            # Merge locked positions (keep most recent lock)
            locked = entry.get("locked_positions", {})
            if locked:
                cumulative_locked.update(locked)

        return {
            "colors_in": sorted(list(cumulative_in)),
            "colors_out": sorted(list(cumulative_out)),
            "locked_positions": cumulative_locked,
        }

    def analyze_and_strategize(
        self,
        guess_history: List[List[str]] = None,
        last_feedback: Dict[str, Any] = None,
        competitive_analysis: Dict[str, Any] = None,
        difficulty: str = "easy",
        available_colors: List[str] = None,
        num_pegs: int = 4,
        round_num: int = 1,
    ) -> Dict[str, Any]:
        """Analyze constraints and develop strategy.

        ⭐ Uses self.analysis_history (agent's own memory) instead of parameter.
        After analyzing, updates self.analysis_history with new deductions.
        ⭐ BOSS-WORKER: Now detects and accumulates LOCKED POSITIONS across rounds
        """

        if guess_history is None:
            guess_history = []
        if last_feedback is None:
            last_feedback = {}
        if competitive_analysis is None:
            competitive_analysis = {}
        if available_colors is None:
            available_colors = []

        # Build analysis history context from AGENT'S OWN MEMORY
        analysis_history_text = ""
        # ⭐ DEBUG: Verify memory is persisting
        print(f"[Agent Memory] Round {round_num}: self.analysis_history has {len(self.analysis_history)} entries")
        if self.analysis_history:
            print(f"[Agent Memory] Last entry: Round {self.analysis_history[-1].get('round')}, colors_in={self.analysis_history[-1].get('colors_in')}")

        if self.analysis_history:  # ← Read from self, not parameter!
            analysis_history_text = "=== YOUR PREVIOUS DEDUCTIONS (Build on this!) ===\n"
            for entry in self.analysis_history[-3:]:  # Last 3 rounds to avoid token overflow
                try:
                    round_num_prev = entry.get("round", "?")
                    colors_in = entry.get("colors_in", [])
                    colors_out = entry.get("colors_out", [])
                    locked = entry.get("locked_positions", {})

                    analysis_history_text += f"\nRound {round_num_prev}:\n"
                    if colors_in:
                        analysis_history_text += f"  ✓ IN: {', '.join(colors_in)}\n"
                    if colors_out:
                        analysis_history_text += f"  ✗ OUT: {', '.join(colors_out)}\n"
                    if locked:
                        for pos, col in sorted(locked.items()):
                            analysis_history_text += f"  🔒 Position {pos} = {col}\n"
                except:
                    pass
            analysis_history_text += "\n"

        # Build context
        history_text = ""
        if guess_history:
            history_text = "Previous guesses:\n"
            for i, guess in enumerate(guess_history, 1):
                history_text += f"  {i}. {guess}\n"

        # Build feedback context
        feedback_text = ""
        if last_feedback and "game_feedback" in last_feedback:
            fb = last_feedback["game_feedback"]
            feedback_text = f"\nLast Result: {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} positions\n"
            feedback_text += f"Your Rank: #{last_feedback.get('your_rank', '?')}\n"

        # Build competitive context
        competitive_text = ""
        if competitive_analysis:
            competitive_text = "\n=== COMPETITIVE STATUS ===\n"
            for team_key, analysis in competitive_analysis.items():
                colors = analysis.get("colors_found", 0)
                positions = analysis.get("positions_locked", 0)
                strategy = analysis.get("strategy", "unknown")
                competitive_text += f"{team_key}: {colors} colors, {positions} positions locked ({strategy})\n"

        # ⭐ ENHANCED PROMPT: Better constraint deduction + position inference
        prompt = f"""Mastermind Analyzer ({num_pegs} pegs). Colors: {', '.join(available_colors)}.

{analysis_history_text}{history_text}{feedback_text}

⭐ CONSTRAINT DEDUCTION LOGIC:
1. If pegs=0: ALL colors in that guess are OUT (impossible)
2. If pegs=N from a guess of N different colors: EXACTLY N are IN, the rest are OUT
   - Example: [red,blue,green,yellow]→1P means only 1 is IN, 3 are definitely OUT
   - Mark the 3 as colors_out!
3. If same color set consistently gives low pegs: Those colors are exhausted, test NEW colors
4. Track which colors appear in guesses with HIGHER pegs - those are the IN colors

LOCKED POSITION INFERENCE:
- If a color appears at SAME position in multiple guesses with CONSISTENT feedback → LOCKED
- If swapping positions CHANGED feedback → those positions must be locked
- Example: [red,blue,green,yellow]→3P/2L, [red,blue,yellow,green]→3P/0L means green/yellow positions were locked

EXTRACT:
1. colors_in: Colors confirmed IN the secret
2. colors_out: Colors CONFIRMED OUT (from 0P guesses or logical deduction)
3. locked_positions: Positions with same color giving consistent results
4. CRITICAL: Once locked, NEVER change it

DEDUCTION STRATEGY:
- Identify colors that appear only in LOW-feedback guesses → mark as OUT
- Identify colors in HIGH-feedback guesses → mark as IN
- If testing 4 different colors gives 1P consistently: Only 1 is IN, rest are OUT - EXPAND search!
- When a color set is exhausted (same results), try completely different colors

NEXT ACTION:
- If 2+ positions locked → permute remaining colors in unknown positions
- If 3+ colors found AND exploring positions → test different arrangements
- If only 1-2 colors found from current set → EXPAND to new untested colors
- Never re-guess the exact same combination

OUTPUT JSON ONLY:
{{"colors_in": ["color1"], "colors_out": [], "locked_positions": {{"0": "red"}}, "strategy": "...", "near_solve_state": false}}
"""

        try:
            # ⭐ CRITICAL FIX: Use call_llm_conversation() to maintain reasoning history
            # This allows LLM to build on its own prior deductions across rounds
            # (This is how boss_worker successfully solves puzzles!)
            system_prompt = f"""You are the Analyzer-Strategist agent in a Mastermind game.
Your role: extract constraints from feedback and develop winning strategy.

MASTERMIND RULES:
- correct_pegs = total colors in guess that exist in secret (counting duplicates!)
- correct_positions = colors in the EXACT right position
- If pegs=0 → NONE of those colors are in the secret (all impossible)
- misplaced = pegs - positions = colors that exist but in WRONG position
- Colors CAN repeat in the secret (CRITICAL: a color can appear 1, 2, 3, or 4 times!)

⭐ KEY INSIGHT: The secret uses exactly 4 colors (possibly with repeats).
If testing 4 different colors gives low pegs (1-2), most are WRONG → must expand to untested colors.
Don't keep permuting the same 4 colors if feedback plateaus!

You have perfect memory of all prior analysis via conversation history.
Use it to build constraints progressively without restarting.
When stuck, deduct which colors are OUT and explore new colors!"""

            response = self.call_llm_conversation(system_prompt, prompt)

            # Parse JSON with better error handling
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                import re
                # Strip markdown code blocks first
                cleaned = re.sub(r'```json\s*\n?|\n?```', '', response, flags=re.DOTALL)
                # Try to find JSON object
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Fall back to systematic testing
                        result = {
                            "colors_in": available_colors[:num_pegs],
                            "colors_out": [],
                            "locked_positions": {},
                            "unknown_positions": list(range(num_pegs)),
                            "strategy": "Systematic color testing"
                        }
                else:
                    result = {
                        "colors_in": available_colors[:num_pegs],
                        "colors_out": [],
                        "locked_positions": {},
                        "unknown_positions": list(range(num_pegs)),
                        "strategy": "Systematic color testing"
                    }

            # ⭐ EXPLICIT POSITION DETECTION: Use code-based inference, not just LLM
            # Build feedback history from guess history for position analysis
            feedback_history = []
            for entry in self.analysis_history:
                # Get feedback from the stored feedback if available
                # For now, we'll try to extract from the stored entry
                fb_entry = entry.copy()
                feedback_history.append(fb_entry)

            # Build actual guess history from analysis_history for position detection
            guess_history_for_analysis = []
            for entry in self.analysis_history:
                # Try to reconstruct guesses from history
                # NOTE: We may not have full guess history in analysis_history
                pass

            # If we have guess_history from input, use that for position detection
            print(f"[Analyzer] Round {round_num}: Checking guess_history, type={type(guess_history)}, len={len(guess_history) if isinstance(guess_history, list) else 'N/A'}")
            if isinstance(guess_history, list) and len(guess_history) > 0:
                print(f"[Analyzer] First entry in guess_history: {guess_history[0] if guess_history else 'empty'}")

                # Extract feedback values
                feedback_for_positions = []
                for i, g_entry in enumerate(guess_history):
                    if isinstance(g_entry, dict) and "feedback" in g_entry:
                        feedback_for_positions.append(g_entry["feedback"])
                    else:
                        feedback_for_positions.append({})

                # Get actual guesses
                actual_guesses = []
                for g_entry in guess_history:
                    if isinstance(g_entry, dict) and "guess" in g_entry:
                        actual_guesses.append(g_entry["guess"])
                    elif isinstance(g_entry, list):
                        actual_guesses.append(g_entry)
                    else:
                        actual_guesses.append([])

                print(f"[Analyzer] Extracted {len(actual_guesses)} guesses, {len(feedback_for_positions)} feedback entries")
                print(f"[Analyzer] Actual guesses: {actual_guesses}")
                print(f"[Analyzer] Feedback: {feedback_for_positions}")

                # ⭐ PHASE 2: Check for color identification inconsistencies
                consistency_check = self._check_color_consistency(
                    actual_guesses, feedback_for_positions, result.get("colors_in", [])
                )
                if not consistency_check.get("is_consistent"):
                    print(f"[Phase 2] Color inconsistency detected: {consistency_check}")
                    # Generate hypotheses to test
                    hypotheses = self._generate_color_hypotheses(
                        actual_guesses[consistency_check.get("round", 1) - 1] if actual_guesses else [],
                        feedback_for_positions[consistency_check.get("round", 1) - 1] if feedback_for_positions else {},
                        available_colors
                    )
                    result["color_hypotheses"] = hypotheses
                    result["color_inconsistency"] = consistency_check
                    print(f"[Phase 2] Added {len(hypotheses)} hypotheses to strategy")

                # ⭐ CONSTRAINT DEDUCTION: Infer colors_out from feedback patterns
                # If we have multiple guesses with consistently low pegs on initial colors, deduce what's OUT
                inferred_colors_out = set()
                if len(actual_guesses) >= 4 and feedback_for_positions:
                    # Get the FIRST 4 guesses which test the base color set
                    first_4_guesses = actual_guesses[:4]
                    first_4_feedback = feedback_for_positions[:4]

                    # Colors in the first 4 guesses
                    first_4_colors = set()
                    for guess in first_4_guesses:
                        first_4_colors.update(guess)

                    # If the first 4 guesses consistently give ≤1 peg, 3+ of those colors are OUT
                    first_4_pegs = [fb.get("correct_pegs", 0) for fb in first_4_feedback]
                    max_pegs_first4 = max(first_4_pegs, default=0)
                    avg_pegs_first4 = sum(first_4_pegs) / len(first_4_pegs) if first_4_pegs else 0

                    # If first 4 guesses (all permutations of 4 colors) give max 1P, deduce:
                    # Only 1 of those 4 colors is IN, the rest are OUT
                    if max_pegs_first4 <= 1 and len(first_4_colors) == 4:
                        colors_in_from_llm = set(result.get("colors_in", []))
                        # If LLM thinks more than 1-2 are IN, it's wrong - mark most as OUT
                        if len(colors_in_from_llm) >= 3:
                            inferred_colors_out = first_4_colors - set(list(colors_in_from_llm)[:2])
                            print(f"[Constraint Deduction] First 4 guesses max {max_pegs_first4}P → colors OUT: {inferred_colors_out}")

                    # Second pattern: if feedback plateaus (same peg count across 3+ recent guesses),
                    # and pegs are low, then those colors are likely exhausted
                    if len(actual_guesses) >= 5:
                        recent_5_feedback = feedback_for_positions[-5:]
                        recent_5_pegs = [fb.get("correct_pegs", 0) for fb in recent_5_feedback]
                        recent_5_guesses = actual_guesses[-5:]
                        recent_5_colors = set()
                        for guess in recent_5_guesses:
                            recent_5_colors.update(guess)

                        # If pegs plateau at low value (1-2), current search space is exhausted
                        if len(set(recent_5_pegs)) == 1 and recent_5_pegs[0] <= 1:
                            colors_in_from_llm = set(result.get("colors_in", []))
                            initial_colors = set(actual_guesses[0]) if actual_guesses else set()
                            # Old colors that don't help should be OUT
                            old_unhelpful = initial_colors - colors_in_from_llm
                            inferred_colors_out.update(old_unhelpful)
                            if old_unhelpful:
                                print(f"[Constraint Deduction] Plateaued at {recent_5_pegs[0]}P → mark OUT: {old_unhelpful}")

                # Run position detection
                if actual_guesses and feedback_for_positions:
                    detected_locked = self._detect_locked_positions(actual_guesses, feedback_for_positions)
                    print(f"[Position Detection] Round {round_num}: Detected locked positions: {detected_locked}")
                    print(f"[Position Detection] Guesses analyzed: {actual_guesses}")
                    print(f"[Position Detection] Feedback analyzed: {feedback_for_positions}")

                    # Merge with LLM results, preferring explicit detection
                    llm_locked = result.get("locked_positions", {})
                    if isinstance(llm_locked, list):
                        llm_locked_dict = {str(item.get("position")): item.get("color") for item in llm_locked if isinstance(item, dict)}
                    else:
                        llm_locked_dict = llm_locked if isinstance(llm_locked, dict) else {}

                    # Merge: explicit detection takes precedence
                    for pos, color in detected_locked.items():
                        llm_locked_dict[pos] = color
                    result["locked_positions"] = llm_locked_dict

                    if llm_locked_dict:
                        print(f"[Position Detection] After merge: {llm_locked_dict}")

                    # Also merge inferred colors_out
                    if inferred_colors_out:
                        current_out = set(result.get("colors_out", []))
                        current_out.update(inferred_colors_out)
                        result["colors_out"] = list(current_out)
                        print(f"[Constraint Deduction] Updated colors_out: {result['colors_out']}")

            # Ensure colors_in has at least num_pegs colors
            colors_in = result.get("colors_in", [])
            if len(colors_in) < num_pegs:
                # Add untested colors to reach num_pegs
                colors_out = set(result.get("colors_out", []))
                for color in available_colors:
                    if color not in colors_in and color not in colors_out and len(colors_in) < num_pegs:
                        colors_in.append(color)
                result["colors_in"] = colors_in

            # ===== IMPROVEMENT #1 & #2: DETECT NEAR-SOLVE STATE =====
            pegs_found = len(result.get("colors_in", []))
            locked_positions = result.get("locked_positions", {})
            positions_locked = len(locked_positions)

            # If 3+ pegs found (all 4 colors known) OR 4 pegs + 1+ position = NEAR SOLVE
            # Trigger permutation testing when we have enough colors to solve
            if (pegs_found >= 4) or (pegs_found >= 3 and positions_locked >= 1):
                result["near_solve_state"] = True
                result["missing_color_count"] = num_pegs - pegs_found
                result["unknown_positions"] = [i for i in range(num_pegs)
                                              if str(i) not in locked_positions]

                # Set explicit permutation strategy
                result["permutation_strategy"] = {
                    "action": "test_permutations",
                    "locked_colors": locked_positions,
                    "remaining_colors": result.get("colors_in", []),
                    "unknown_positions": [i for i in range(num_pegs)
                                         if str(i) not in locked_positions],
                }

                # Update strategy description for permutation mode
                unknown_pos = result["permutation_strategy"]["unknown_positions"]
                missing_count = result["missing_color_count"]
                result["strategy"] = (
                    f"NEAR-SOLVE: {pegs_found}/{num_pegs} correct pegs, "
                    f"{positions_locked}/{num_pegs} positions locked. "
                    f"Permute the {len(unknown_pos)} unknown position(s) with the "
                    f"{missing_count} remaining color(s) while keeping locked positions fixed."
                )

            # ⭐ PHASE 2: Track max feedback for Proposer's recovery logic
            max_pegs_feedback = 0
            if feedback_for_positions:
                max_pegs_feedback = max(
                    fb.get("correct_pegs", 0) for fb in feedback_for_positions
                )
            result["max_pegs_feedback"] = max_pegs_feedback

            # ⭐ UPDATE AGENT'S OWN MEMORY
            memory_entry = {
                "round": round_num,
                "colors_in": result.get("colors_in", []),
                "colors_out": result.get("colors_out", []),
                "locked_positions": result.get("locked_positions", {}),
                "strategy": result.get("strategy", ""),
                "near_solve_state": result.get("near_solve_state", False),
            }
            self.analysis_history.append(memory_entry)
            print(f"[Agent Memory] ✓ SAVED Round {round_num}: colors_in={memory_entry['colors_in']}, locked={memory_entry['locked_positions']}")
            print(f"[Agent Memory] Total history now: {len(self.analysis_history)} entries")

            # ⭐ COMPUTE CUMULATIVE CONSTRAINTS for Proposer
            cumulative_constraints = self._compute_cumulative_constraints()
            result["cumulative_constraints"] = cumulative_constraints
            print(f"[Constraint Tracking] Cumulative: IN={cumulative_constraints['colors_in']}, OUT={cumulative_constraints['colors_out']}, LOCKED={cumulative_constraints['locked_positions']}")

            self.call_count += 1
            return result

        except Exception as e:
            print(f"Error in analyze_and_strategize: {e}")
            # Ensure at least num_pegs colors in fallback
            colors_in = available_colors[:num_pegs]
            while len(colors_in) < num_pegs and len(colors_in) < len(available_colors):
                colors_in.append(available_colors[len(colors_in)])

            result = {
                "colors_in": colors_in[:num_pegs],
                "colors_out": [],
                "locked_positions": {},
                "unknown_positions": list(range(num_pegs)),
                "strategy": f"Error: {str(e)}",
                "near_solve_state": False,
                "permutation_strategy": None,
            }

            # ⭐ STILL RUN POSITION DETECTION even on LLM error!
            # This is critical because position detection is algorithmic, not LLM-based
            print(f"[Analyzer] ERROR PATH: Attempting position detection with guess_history")
            if isinstance(guess_history, list) and len(guess_history) > 0:
                print(f"[Analyzer] ERROR PATH: First entry: {guess_history[0] if guess_history else 'empty'}")

                # Extract feedback values
                feedback_for_positions = []
                for i, g_entry in enumerate(guess_history):
                    if isinstance(g_entry, dict) and "feedback" in g_entry:
                        feedback_for_positions.append(g_entry["feedback"])
                    else:
                        feedback_for_positions.append({})

                # Get actual guesses
                actual_guesses = []
                for g_entry in guess_history:
                    if isinstance(g_entry, dict) and "guess" in g_entry:
                        actual_guesses.append(g_entry["guess"])
                    elif isinstance(g_entry, list):
                        actual_guesses.append(g_entry)
                    else:
                        actual_guesses.append([])

                print(f"[Analyzer] ERROR PATH: {len(actual_guesses)} guesses, {len(feedback_for_positions)} feedback")
                # Run position detection
                if actual_guesses and feedback_for_positions:
                    try:
                        detected_locked = self._detect_locked_positions(actual_guesses, feedback_for_positions)
                        if detected_locked:
                            result["locked_positions"] = detected_locked
                            print(f"[Analyzer] ERROR PATH: Detected locked: {detected_locked}")
                    except Exception as pd_e:
                        print(f"[Analyzer] Position detection failed: {pd_e}")

            # ⭐ SAVE FALLBACK TO MEMORY TOO (even on error)
            # ⭐ PHASE 2: Track max feedback in error path too
            max_pegs_feedback = 0
            if 'feedback_for_positions' in locals():
                max_pegs_feedback = max(
                    fb.get("correct_pegs", 0) for fb in feedback_for_positions if isinstance(fb, dict)
                )
            result["max_pegs_feedback"] = max_pegs_feedback

            fallback_memory = {
                "round": round_num,
                "colors_in": result["colors_in"],
                "colors_out": result["colors_out"],
                "locked_positions": result["locked_positions"],
                "strategy": result["strategy"],
                "near_solve_state": False,
            }
            self.analysis_history.append(fallback_memory)
            print(f"[Agent Memory] SAVED FALLBACK Round {round_num}: error={str(e)[:60]}, locked={result['locked_positions']}")
            print(f"[Agent Memory] Total history now: {len(self.analysis_history)} entries")

            return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process analysis and strategy."""
        return self.analyze_and_strategize(
            guess_history=kwargs.get("guess_history", []),
            last_feedback=kwargs.get("last_feedback", {}),
            competitive_analysis=kwargs.get("competitive_analysis", {}),
            difficulty=kwargs.get("difficulty", "easy"),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
            round_num=kwargs.get("round_num", 1),
        )
