"""
Boss Agent — LLM-powered coordinator for Boss-Worker paradigm.

The Boss (with A2A standardization):
  1. Searches registry for workers by agent_type → gets URLs
  2. Sends HTTP A2A requests using standard A2AMessage envelopes
  3. Implements retry logic and timeout handling
  4. Uses LLM to interpret results and make decisions
  5. Returns final guess to orchestrator
"""

import sys
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode
from communication.a2a_contract import get_contract


# ── Boss agent card ───────────────────────────────────────────────────────────

BOSS_AGENT_CARD = {
    "agent_id": "boss_boss_worker",
    "agent_name": "Boss",
    "agent_type": "boss",
    "paradigm": "boss_worker",
    "description": (
        "Central coordinator. Discovers workers via registry, "
        "delegates to them over HTTP (A2A), then synthesises a final guess."
    ),
    "capabilities": {
        "run_round": {
            "description": "Coordinate one full game round via worker agents",
            "parameters": {"type": "object"},
        }
    },
}


# ── Boss LLM Agent ────────────────────────────────────────────────────────────

class BossAgent(BaseAgent):
    """
    LLM-powered Boss.

    Lifecycle per round
    ──────────────────
    1. plan_round()       → LLM decides what to do this round
    2. discover(type)     → HTTP GET  registry → worker URL
    3. call_worker(url)   → HTTP POST worker   → worker result
    4. evaluate_round()   → LLM synthesises results → final decision
    5. return guess
    """

    def __init__(
        self,
        registry_url: str,
        provider: str = "ollama",
    ):
        super().__init__(
            name="Boss_BossWorker",
            provider=provider,
            role=AgentRole.BOSS,
            paradigm=ParadigmType.BOSS_WORKER,
            team_members=["analyzer", "strategist", "proposer", "validator"],
            can_communicate=True,
            constraints_owned=["Overall coordination", "Final guess decision"],
        )
        self.registry_url = registry_url
        self.http = httpx.Client(timeout=120.0)   # persistent sync client
        self.round_logs: List[Dict[str, Any]] = []

    # ── Registry discovery with error handling ───────────────────────────────

    def discover_worker(self, agent_type: str, retries: int = 3) -> str:
        """Query registry for worker URL by type. Retries on failure."""
        for attempt in range(retries):
            try:
                resp = self.http.get(
                    f"{self.registry_url}/agents/type/{agent_type}",
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()

                # Response is wrapped in A2AMessage
                if "payload" in data:
                    agents = data["payload"].get("agents", [])
                else:
                    agents = data  # Fallback to raw response

                if agents:
                    url = agents[0].get("url")
                    print(f"[Boss] Discovered {agent_type} @ {url}")
                    return url

            except Exception as e:
                print(f"[Boss] Discovery attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.5)

        raise RuntimeError(f"[Boss] Could not discover {agent_type} after {retries} attempts")

    # ── A2A HTTP calls with standard envelope + error handling ────────────────

    def call_worker(
        self,
        url: str,
        endpoint: str,
        payload: Dict[str, Any],
        retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Send A2A HTTP POST to worker.
        Uses A2AMessage envelope, handles errors, retries on failure.
        """
        msg_id = str(uuid.uuid4())[:8]

        # Get contract timeout
        agent_type = endpoint  # endpoint name matches agent capability
        contract = get_contract(agent_type, endpoint)
        timeout = contract.get("timeout", 30) if contract else 30

        for attempt in range(retries):
            try:
                print(f"[Boss→A2A] POST {url}/{endpoint} (msg_id={msg_id}, attempt {attempt+1})")

                # Create A2A request message
                request_msg = A2AMessage.request(
                    sender_id="boss_boss_worker",
                    receiver_id=f"{agent_type}_boss_worker",
                    action=endpoint,
                    payload=payload,
                )

                # Send HTTP POST with A2A envelope
                resp = self.http.post(
                    f"{url}/{endpoint}",
                    json=request_msg.to_dict(),
                    timeout=float(timeout),
                )

                # Parse response
                if resp.status_code == 200:
                    response_data = resp.json()

                    # If wrapped in A2AMessage envelope
                    if isinstance(response_data, dict) and "message_id" in response_data:
                        response_msg = A2AMessage.from_dict(response_data)
                        if response_msg.status == A2AStatus.OK:
                            result = response_msg.payload
                            print(f"[Boss←A2A] {endpoint} ✓ (msg_id={msg_id})")
                            return result
                        else:
                            error = response_msg.error_message or "Unknown error"
                            print(f"[Boss←A2A] {endpoint} ERROR: {error}")
                            if attempt < retries - 1:
                                time.sleep(0.5)
                            continue
                    else:
                        # Fallback: unwrapped response
                        print(f"[Boss←A2A] {endpoint} ✓ (msg_id={msg_id})")
                        return response_data

                elif resp.status_code == 408:
                    print(f"[Boss←A2A] {endpoint} TIMEOUT (attempt {attempt+1})")
                    if attempt < retries - 1:
                        time.sleep(1)
                    continue
                else:
                    error_msg = resp.text or f"HTTP {resp.status_code}"
                    print(f"[Boss←A2A] {endpoint} HTTP {resp.status_code}: {error_msg}")
                    if attempt < retries - 1:
                        time.sleep(0.5)
                    continue

            except httpx.TimeoutException:
                print(f"[Boss] Timeout calling {endpoint} (attempt {attempt+1})")
                if attempt < retries - 1:
                    time.sleep(1)
                continue
            except Exception as e:
                print(f"[Boss] Error calling {endpoint}: {e} (attempt {attempt+1})")
                if attempt < retries - 1:
                    time.sleep(0.5)
                continue

        raise RuntimeError(
            f"[Boss] Failed to call {endpoint} after {retries} attempts"
        )

    # ── LLM coordination ──────────────────────────────────────────────────────

    def plan_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to plan the upcoming round given current game state."""
        role_ctx = self.get_role_system_prompt()
        history_summary = ""
        for h in game_state.get("guess_history", [])[-3:]:
            fb = h.get("feedback", {})
            history_summary += (
                f"\n  Round {h['round']}: {h['guess']} "
                f"→ {fb.get('correct_pegs',0)} pegs, {fb.get('correct_positions',0)} positions"
            )
        if not history_summary:
            history_summary = "\n  [First round — no history yet]"

        prompt = f"""{role_ctx}

## YOUR TASK — Round Planning (Boss-Worker Paradigm)
You are the Boss. Before calling your workers you must plan this round.

GAME STATE:
- Round: {game_state['round_number']} / 8
- Difficulty: {game_state['difficulty']}
- Available colours: {game_state['available_colors']}
- Pegs: {game_state['pegs']}

GUESS HISTORY:{history_summary}

WORKERS AVAILABLE: analyzer, strategist, proposer, validator
You will call them in that order via HTTP.

Plan this round: what is the priority? What constraints matter most?
What should each worker focus on?

OUTPUT (JSON ONLY):
{{
  "round_priority": "Find new colors | Lock positions | Confirm solution",
  "guidance": {{
    "for_analyzer":   "What to look for",
    "for_strategist": "What phase / risk level",
    "for_proposer":   "What to try",
    "for_validator":  "What to be strict about"
  }},
  "boss_confidence": 0.7,
  "reasoning": "Why this plan"
}}"""

        resp = self.call_llm(prompt)
        plan = self.parse_json_response(resp)
        if "error" in plan:
            plan = {
                "round_priority": "Explore",
                "guidance": {
                    "for_analyzer": "Extract all constraints",
                    "for_strategist": "Exploration phase",
                    "for_proposer": "Try diverse colours",
                    "for_validator": "Check all constraints",
                },
                "boss_confidence": 0.4,
                "reasoning": "LLM plan failed — using fallback",
            }
        return plan

    def evaluate_round(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        strategy: Dict[str, Any],
        proposal: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use LLM to synthesise worker outputs and make the final call."""
        role_ctx = self.get_role_system_prompt()

        prompt = f"""{role_ctx}

## YOUR TASK — Round Evaluation (Boss-Worker Paradigm)
You are the Boss. Your workers have responded. Make the final decision.

ROUND PLAN: {json.dumps(plan, indent=2)}

ANALYZER SAID:
  Analysis: {analysis.get('analysis', '—')}
  Constraints: {analysis.get('constraints', [])}
  Confidence: {analysis.get('confidence', '—')}

STRATEGIST SAID:
  Phase: {strategy.get('phase', '—')}
  Strategy: {strategy.get('strategy', '—')}

PROPOSER SAID:
  Proposed guess: {proposal.get('proposed_guess', [])}
  Reasoning: {proposal.get('reasoning', '—')}

VALIDATOR SAID:
  Valid: {validation.get('valid', '—')}
  Violations: {validation.get('hard_violations', [])}
  Warnings: {validation.get('soft_warnings', [])}
  Strategic assessment: {validation.get('strategic_assessment', '—')}

As Boss, decide:
- Do you ACCEPT the validator's decision or OVERRIDE it?
- Is the proposed guess your final answer?
- Any final adjustments?

OUTPUT (JSON ONLY):
{{
  "final_decision": "ACCEPT | OVERRIDE",
  "submit_guess": true,
  "final_guess": {proposal.get('proposed_guess', [])},
  "override_reason": "Only if overriding",
  "boss_assessment": "Brief summary of this round",
  "confidence": 0.8
}}"""

        resp = self.call_llm(prompt)
        decision = self.parse_json_response(resp)
        if "error" in decision:
            decision = {
                "final_decision": "ACCEPT",
                "submit_guess": validation.get("valid", True),
                "final_guess": proposal.get("proposed_guess", []),
                "override_reason": "",
                "boss_assessment": "LLM evaluation failed — accepting validator",
                "confidence": 0.3,
            }
        return decision

    # ── Main round runner ─────────────────────────────────────────────────────

    def run_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full round coordination:
          plan → [discover+call analyzer] → [discover+call strategist]
               → [discover+call proposer] → [discover+call validator]
               → evaluate → return
        """
        round_num = game_state.get("round_number", 1)
        print(f"\n[Boss] ── Starting Round {round_num} coordination ──")

        # 1. Plan the round with LLM
        plan = self.plan_round(game_state)
        print(f"[Boss] Plan: {plan.get('round_priority')}")

        # 2. Analyzer — discover URL then call via HTTP
        analyzer_url = self.discover_worker("analyzer")
        analysis = self.call_worker(analyzer_url, "analyze", {
            "last_guess":        game_state.get("last_guess", []),
            "feedback":          game_state.get("last_feedback", {}),
            "previous_guesses":  game_state.get("guess_history", []),
        })
        print(f"[Boss] Analyzer → confidence={analysis.get('confidence','?')}")

        # 3. Strategist — discover URL then call via HTTP
        strategist_url = self.discover_worker("strategist")
        strategy = self.call_worker(strategist_url, "strategy", {
            "guess_history": game_state.get("guess_history", []),
            "difficulty":    game_state.get("difficulty", "easy"),
        })
        print(f"[Boss] Strategist → phase={strategy.get('phase','?')}")

        # 4. Proposer — discover URL then call via HTTP
        proposer_url = self.discover_worker("proposer")
        constraints_text = "\n".join(analysis.get("constraints", []))
        proposal = self.call_worker(proposer_url, "propose", {
            "strategy":        strategy.get("strategy", ""),
            "constraints_text": constraints_text,
            "available_colors": game_state.get("available_colors", []),
            "num_pegs":        game_state.get("pegs", 4),
            "previous_guesses": [g["guess"] for g in game_state.get("guess_history", [])],
        })
        print(f"[Boss] Proposer → {proposal.get('proposed_guess','?')}")

        # 5. Validator — discover URL then call via HTTP
        validator_url = self.discover_worker("validator")
        validation = self.call_worker(validator_url, "validate", {
            "guess":            proposal.get("proposed_guess", []),
            "available_colors": game_state.get("available_colors", []),
            "expected_length":  game_state.get("pegs", 4),
            "previous_guesses": [g["guess"] for g in game_state.get("guess_history", [])],
            "constraints": {
                "correct_positions":             analysis.get("correct_positions", []),
                "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
                "impossible_colors":             analysis.get("impossible_colors", []),
            },
        })
        print(f"[Boss] Validator → valid={validation.get('valid','?')}")

        # 6. Boss evaluates all outputs and makes final decision
        decision = self.evaluate_round(plan, analysis, strategy, proposal, validation)
        print(f"[Boss] Decision → {decision.get('final_decision')} | submit={decision.get('submit_guess')}")

        # Log the full round
        round_record = {
            "round": round_num,
            "plan":       plan,
            "analysis":   analysis,
            "strategy":   strategy,
            "proposal":   proposal,
            "validation": validation,
            "decision":   decision,
        }
        self.round_logs.append(round_record)

        return {
            "guess":           decision.get("final_guess", proposal.get("proposed_guess", [])),
            "submit":          decision.get("submit_guess", validation.get("valid", True)),
            "analysis":        analysis,
            "strategy":        strategy,
            "proposal":        proposal,
            "validation":      validation,
            "boss_decision":   decision,
            "round_log":       round_record,
        }

    def close(self) -> None:
        """Close the persistent HTTP client."""
        self.http.close()

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class.

        Delegates to run_round for this agent.
        """
        return self.run_round(kwargs)
