# Boss-Worker Boss Agent
# Central orchestrator that delegates tasks and manages workflow
# Only the Boss communicates across agents; workers only reply to Boss

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import asyncio
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from communication.a2a_message import A2AMessage, A2AStatus
from base.role import AgentRole, ParadigmType


AGENT_CARD = {
    "agent_id": "boss_boss_worker",
    "agent_name": "Boss",
    "agent_type": "orchestrator",
    "paradigm": "boss_worker",
    "version": "1.0.0",
    "description": "Boss agent that delegates tasks to workers in Boss-Worker paradigm",
    "url": "http://localhost:8101",
    "health_endpoint": "/health",
    "capabilities": {
        "delegate": {
            "description": "Delegate analysis task to Analyzer",
            "parameters": {"type": "object"},
            "returns": {"type": "object"},
        },
        "orchestrate": {
            "description": "Orchestrate workflow",
            "parameters": {"type": "object"},
            "returns": {"type": "object"},
        },
    },
    "constraints_owned": ["Workflow orchestration"],
    "team_members": ["analyzer", "strategist", "proposer", "validator"],
    "can_communicate": True,
}


class BossAgent(BaseAgent):
    """Boss Agent - Central Orchestrator

    The Boss:
    - Receives initial puzzle/feedback from main orchestrator
    - Delegates analysis to Analyzer
    - Receives Analyzer's constraints
    - Delegates strategy to Strategist
    - Delegates proposal to Proposer
    - Delegates validation to Validator
    - Returns final guess to orchestrator
    - Controls ALL inter-agent communication
    """

    def __init__(
        self,
        provider: str = "ollama",
        comm_layer: Optional[Any] = None,
        registry_url: Optional[str] = None,
    ):
        super().__init__(
            name="Boss_BossWorker",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.BOSS,
            paradigm=ParadigmType.BOSS_WORKER,
            team_members=["analyzer", "strategist", "proposer", "validator"],
            can_communicate=True,
            constraints_owned=["Workflow orchestration"],
            registry_url=registry_url,
        )
        self.worker_urls: Dict[str, str] = {}

    def set_worker_urls(self, worker_urls: Dict[str, str]) -> None:
        """Set URLs for all worker agents."""
        self.worker_urls = worker_urls

    def discover_worker_urls(self) -> Dict[str, str]:
        """Discover worker URLs from the registry by querying for agent names.

        Returns a dict mapping agent_name (analyzer, strategist, etc.) to their URL.
        """
        worker_urls = {}

        if not self.registry_url:
            return worker_urls

        try:
            resp = httpx.get(f"{self.registry_url}/agents", timeout=5.0)
            if resp.status_code != 200:
                return worker_urls

            data = resp.json()
            agents_list = data.get("payload", {}).get("agents", [])

            for agent_data in agents_list:
                paradigm = agent_data.get("paradigm", "")

                # Only get agents from boss_worker paradigm
                if paradigm != "boss_worker":
                    continue

                agent_name = agent_data.get("agent_name", "").lower()
                agent_url = agent_data.get("url", "")

                if agent_name and agent_url:
                    worker_urls[agent_name] = agent_url

            self.worker_urls = worker_urls
            return worker_urls
        except Exception as e:
            print(f"[Boss] Error discovering workers from registry: {e}")
            return worker_urls

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get descriptions of available agents from registry for decision-making.

        Returns a dict of agent info that the LLM can use to understand
        what capabilities are available.
        """
        import httpx

        agents_info = {}

        if not self.registry_url:
            return agents_info

        try:
            resp = httpx.get(f"{self.registry_url}/agents", timeout=5.0)
            if resp.status_code != 200:
                return agents_info

            data = resp.json()
            agents_list = data.get("payload", {}).get("agents", [])

            for agent_data in agents_list:
                paradigm = agent_data.get("paradigm", "")

                if paradigm != "boss_worker":
                    continue

                agent_id = agent_data.get("agent_id", "")
                agent_name = agent_data.get("agent_name", "Unknown").lower()
                description = agent_data.get("description", "")
                capabilities = agent_data.get("capabilities", {})

                agents_info[agent_name] = {
                    "id": agent_id,
                    "description": description,
                    "capabilities": list(capabilities.keys()),
                }

            return agents_info
        except Exception:
            return agents_info

    async def delegate_to_analyzer(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        guess_history: List[Dict],
        available_colors: List[str],
        difficulty: str,
        num_pegs: int,
    ) -> Dict[str, Any]:
        """Delegate analysis task to Analyzer."""
        # ✅ Discover worker URLs from registry if not already done
        if not self.worker_urls:
            self.discover_worker_urls()

        analyzer_url = self.worker_urls.get("analyzer")
        if not analyzer_url:
            raise RuntimeError("Analyzer URL not found in registry")

        msg = A2AMessage.request(
            sender_id="boss_boss_worker",
            receiver_id="analyzer_boss_worker",
            action="analyze",
            payload={
                "last_guess": last_guess,
                "feedback": feedback,
                "guess_history": guess_history,
                "available_colors": available_colors,
                "difficulty": difficulty,
                "num_pegs": num_pegs,
            }
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{analyzer_url}/analyze",
                        json=msg.to_dict(),
                        timeout=300.0
                    )
                    if resp.status_code == 200:
                        # ✅ Parse A2A response envelope
                        response_data = resp.json()
                        response_msg = A2AMessage.from_dict(response_data)

                        if response_msg.status == A2AStatus.OK:
                            print(f"[Boss] ✓ Analyzer analysis received (msg_id: {response_msg.message_id}, trace: {response_msg.response_to})")
                            return response_msg.payload
                        else:
                            print(f"[Boss] ! Analyzer error: {response_msg.error_code} - {response_msg.error_message}")
                            if attempt < 2:
                                wait = 10 * (attempt + 1)
                                print(f"[Boss] Retrying in {wait}s...")
                                await asyncio.sleep(wait)
                    else:
                        print(f"[Boss] ! Analyzer returned {resp.status_code}")
                except Exception as e:
                    if attempt < 2:
                        wait = 10 * (attempt + 1)
                        print(f"[Boss] Error calling Analyzer (attempt {attempt+1}/3), retrying in {wait}s: {e}")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[Boss] Error calling Analyzer after 3 attempts: {e}")
                        raise

        return {}

    async def delegate_to_strategist(
        self,
        guess_history: List[Dict],
        difficulty: str,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delegate strategy task to Strategist."""
        # ✅ Discover worker URLs from registry if not already done
        if not self.worker_urls:
            self.discover_worker_urls()

        strategist_url = self.worker_urls.get("strategist")
        if not strategist_url:
            raise RuntimeError("Strategist URL not found in registry")

        msg = A2AMessage.request(
            sender_id="boss_boss_worker",
            receiver_id="strategist_boss_worker",
            action="propose_strategy",
            payload={
                "guess_history": guess_history,
                "difficulty": difficulty,
                "analysis": analysis.get("analysis", ""),
                "impossible_colors": analysis.get("impossible_colors", []),
                "locked_positions": analysis.get("locked_positions", []),
                "misplaced_colors": analysis.get("misplaced_colors", []),
            }
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{strategist_url}/propose_strategy",
                        json=msg.to_dict(),
                        timeout=300.0
                    )
                    if resp.status_code == 200:
                        # ✅ Parse A2A response envelope
                        response_data = resp.json()
                        response_msg = A2AMessage.from_dict(response_data)

                        if response_msg.status == A2AStatus.OK:
                            print(f"[Boss] ✓ Strategist strategy received (msg_id: {response_msg.message_id})")
                            return response_msg.payload
                        else:
                            print(f"[Boss] ! Strategist error: {response_msg.error_code} - {response_msg.error_message}")
                            if attempt < 2:
                                await asyncio.sleep(10 * (attempt + 1))
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(10 * (attempt + 1))

        return {}

    async def delegate_to_proposer(
        self,
        guess_history: List[Dict],
        available_colors: List[str],
        difficulty: str,
        strategy: Dict[str, Any],
        analysis: Dict[str, Any],
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Delegate proposal task to Proposer."""
        # ✅ Discover worker URLs from registry if not already done
        if not self.worker_urls:
            self.discover_worker_urls()

        proposer_url = self.worker_urls.get("proposer")
        if not proposer_url:
            raise RuntimeError("Proposer URL not found in registry")

        msg = A2AMessage.request(
            sender_id="boss_boss_worker",
            receiver_id="proposer_boss_worker",
            action="propose_guess",
            payload={
                "guess_history": guess_history,
                "available_colors": available_colors,
                "difficulty": difficulty,
                "strategy": strategy,
                "analysis": analysis,
                "num_pegs": num_pegs,
            }
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{proposer_url}/propose_guess",
                        json=msg.to_dict(),
                        timeout=300.0
                    )
                    if resp.status_code == 200:
                        # ✅ Parse A2A response envelope
                        response_data = resp.json()
                        response_msg = A2AMessage.from_dict(response_data)

                        if response_msg.status == A2AStatus.OK:
                            print(f"[Boss] ✓ Proposer guess received (msg_id: {response_msg.message_id})")
                            return response_msg.payload
                        else:
                            print(f"[Boss] ! Proposer error: {response_msg.error_code} - {response_msg.error_message}")
                            if attempt < 2:
                                await asyncio.sleep(10 * (attempt + 1))
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(10 * (attempt + 1))

        return {}

    async def delegate_to_validator(
        self,
        proposed_guess: List[str],
        guess_history: List[Dict],
        analysis: Dict[str, Any],
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Delegate validation task to Validator."""
        # ✅ Discover worker URLs from registry if not already done
        if not self.worker_urls:
            self.discover_worker_urls()

        validator_url = self.worker_urls.get("validator")
        if not validator_url:
            raise RuntimeError("Validator URL not found in registry")

        msg = A2AMessage.request(
            sender_id="boss_boss_worker",
            receiver_id="validator_boss_worker",
            action="validate",
            payload={
                "proposed_guess": proposed_guess,
                "guess_history": guess_history,
                "analysis": analysis,
                "num_pegs": num_pegs,
            }
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{validator_url}/validate",
                        json=msg.to_dict(),
                        timeout=300.0
                    )
                    if resp.status_code == 200:
                        # ✅ Parse A2A response envelope
                        response_data = resp.json()
                        response_msg = A2AMessage.from_dict(response_data)

                        if response_msg.status == A2AStatus.OK:
                            print(f"[Boss] ✓ Validator validation received (msg_id: {response_msg.message_id})")
                            return response_msg.payload
                        else:
                            print(f"[Boss] ! Validator error: {response_msg.error_code} - {response_msg.error_message}")
                            if attempt < 2:
                                await asyncio.sleep(10 * (attempt + 1))
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(10 * (attempt + 1))

        return {}

    async def decide_next_action(
        self,
        game_state: Dict[str, Any],
        current_results: Dict[str, Any],
        iteration: int,
    ) -> Dict[str, Any]:
        """Use LLM to autonomously decide which agent to contact next.

        The Boss reasons about the current game state and results,
        then decides intelligently which agent is needed next.
        """
        system_prompt = """You are an autonomous Boss agent in a Mastermind game.
Your role: Analyze the current game state and decide which agent to contact next.

Available agents:
- Analyzer: Extracts constraints from feedback
- Strategist: Decides strategy based on constraints
- Proposer: Generates guesses using strategy
- Validator: Validates guesses before submission

DECISION FRAMEWORK:
1. No feedback yet? → Contact Analyzer (even if empty, to process initial state)
2. Have feedback but no analysis? → Contact Analyzer
3. Have analysis but no strategy? → Contact Strategist
4. Have strategy but no proposal? → Contact Proposer
5. Have proposal but no validation? → Contact Validator
6. Have validation with issues? → Re-contact Strategist or Proposer to fix
7. Have validation passed? → Return "done" to submit and move to next round
8. Stuck in loop? → Contact a different agent to break the pattern

RE-CONTACT RULES (you CAN re-contact agents):
- Re-contact Analyzer if new feedback contradicts previous analysis
- Re-contact Strategist if validation rejects the guess (strategy needs revision)
- Re-contact Proposer if validation failed or strategy changed
- Re-contact Validator ONLY if the proposal changed (don't re-validate same guess)
- Only return "done" when: validation passed AND you're ready to submit

DECISION OUTPUT (JSON ONLY):
{
  "next_agent": "analyzer|strategist|proposer|validator|done",
  "reason": "Detailed reasoning for this decision",
  "confidence": 0.95,
  "alternative_if_fails": "fallback agent if current fails"
}"""

        available = {
            "analysis": "analysis" in current_results,
            "strategy": "strategy" in current_results,
            "proposal": "proposal" in current_results,
            "validation": "validation" in current_results,
        }

        # Get available agents from registry
        agents_info = self.get_available_agents()
        agents_desc = ""
        if agents_info:
            agents_desc = "\n\nAvailable Agents (from registry):\n"
            for agent_name, info in agents_info.items():
                agents_desc += f"- {agent_name}: {info['description']}\n"
                agents_desc += f"  Capabilities: {', '.join(info['capabilities'])}\n"

        game_summary = f"""Current Game State (Round {len(game_state.get('guess_history', [])) + 1}, Iteration {iteration}):
- Last feedback: {game_state.get('last_feedback', {})}
- Available results: {available}
- Analysis: {current_results.get('analysis', {}).get('analysis', '')[:100]}{'...' if len(str(current_results.get('analysis', {}).get('analysis', ''))) > 100 else ''}
- Strategy: {current_results.get('strategy', {}).get('strategy', '')[:100]}{'...' if len(str(current_results.get('strategy', {}).get('strategy', ''))) > 100 else ''}
- Proposal: {current_results.get('proposal', {}).get('guess', 'none')}
- Validation: {current_results.get('validation', {}).get('is_valid', 'not checked')}{agents_desc}

What should we do next?"""

        try:
            response = self.call_llm_conversation(system_prompt, game_summary)
            decision = self.parse_json_response(response)
            return decision
        except Exception as e:
            print(f"[Boss] Decision-making error: {e}")
            # Fallback to standard sequence if LLM fails
            return self._get_default_next_action(current_results)

    def _get_default_next_action(self, current_results: Dict[str, Any]) -> Dict[str, Any]:
        """Default decision sequence when LLM decision fails."""
        # Sequential order: analyzer → strategist → proposer → validator → done
        if "analysis" not in current_results:
            return {"next_agent": "analyzer", "reason": "Need analysis", "confidence": 1.0}
        elif "strategy" not in current_results:
            return {"next_agent": "strategist", "reason": "Need strategy", "confidence": 1.0}
        elif "proposal" not in current_results:
            return {"next_agent": "proposer", "reason": "Need proposal", "confidence": 1.0}
        elif "validation" not in current_results:
            return {"next_agent": "validator", "reason": "Need validation", "confidence": 1.0}
        else:
            return {"next_agent": "done", "reason": "All results available, ready to submit", "confidence": 1.0}

    async def orchestrate_round(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        guess_history: List[Dict],
        available_colors: List[str],
        difficulty: str,
        num_pegs: int,
    ) -> Dict[str, Any]:
        """Autonomously orchestrate one complete round of the game.

        The Boss uses reasoning to decide which agent to contact next,
        in what order, and when to stop.
        """
        print(f"[Boss] 🧠 Starting autonomous round orchestration...")

        game_state = {
            "round": len(guess_history) + 1,
            "last_guess": last_guess,
            "last_feedback": feedback,
            "guess_history": guess_history,
            "available_colors": available_colors,
            "difficulty": difficulty,
            "num_pegs": num_pegs,
        }

        current_results = {}
        max_iterations = 10  # Safety limit to prevent infinite loops

        for iteration in range(max_iterations):
            # Autonomously decide which agent to contact
            decision = await self.decide_next_action(game_state, current_results, iteration + 1)
            next_agent = decision.get("next_agent")
            confidence = decision.get("confidence", 0.8)

            print(f"[Boss] 🤔 Decision (iteration {iteration + 1}): Contact {next_agent} (confidence: {confidence:.2f})")
            print(f"[Boss]    Reason: {decision.get('reason', 'N/A')}")

            if next_agent == "analyzer":
                print(f"[Boss] → Delegating to Analyzer")
                current_results["analysis"] = await self.delegate_to_analyzer(
                    last_guess, feedback, guess_history, available_colors, difficulty, num_pegs
                )

            elif next_agent == "strategist":
                print(f"[Boss] → Delegating to Strategist")
                current_results["strategy"] = await self.delegate_to_strategist(
                    guess_history, difficulty, current_results.get("analysis", {})
                )

            elif next_agent == "proposer":
                print(f"[Boss] → Delegating to Proposer")
                current_results["proposal"] = await self.delegate_to_proposer(
                    guess_history, available_colors, difficulty,
                    current_results.get("strategy", {}),
                    current_results.get("analysis", {}),
                    num_pegs
                )

            elif next_agent == "validator":
                print(f"[Boss] → Delegating to Validator")
                current_results["validation"] = await self.delegate_to_validator(
                    current_results.get("proposal", {}).get("guess", []),
                    guess_history,
                    current_results.get("analysis", {}),
                    num_pegs
                )

            elif next_agent == "done":
                print(f"[Boss] ✓ Round orchestration complete")
                break

            else:
                print(f"[Boss] ⚠️  Unknown agent: {next_agent}, continuing...")
                continue

        if iteration + 1 >= max_iterations:
            print(f"[Boss] ⚠️  Reached max iterations ({max_iterations}), completing round")
        return {
            "analysis": current_results.get("analysis"),
            "strategy": current_results.get("strategy"),
            "proposal": current_results.get("proposal"),
            "validation": current_results.get("validation"),
            "guess": current_results.get("validation", {}).get("proposed_guess",
                    current_results.get("proposal", {}).get("guess", [])),
            "decision_history": decision,
        }

    def run_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for orchestrate_round called by LangGraph.

        Converts sync call to async orchestration.
        """
        print(f"[Boss] run_round called for round {game_state.get('round_number', 1)}")
        try:
            # Discover worker URLs from registry
            if not self.worker_urls:
                self.worker_urls = self.discover_workers()
                print(f"[Boss] Discovered workers: {list(self.worker_urls.keys())}")

            result = asyncio.run(self.orchestrate_round(
                last_guess=game_state.get("last_guess", []),
                feedback=game_state.get("last_feedback", {"correct_pegs": 0, "correct_positions": 0}),
                guess_history=game_state.get("guess_history", []),
                available_colors=game_state.get("available_colors", []),
                difficulty=game_state.get("difficulty", "easy"),
                num_pegs=game_state.get("pegs", 4),
            ))

            return {
                "submit": True,
                "guess": result.get("guess", []),
                "analysis": result.get("analysis"),
                "strategy": result.get("strategy"),
                "proposal": result.get("proposal"),
                "validation": result.get("validation"),
            }
        except Exception as e:
            print(f"[Boss] ERROR in run_round: {e}")
            import traceback
            traceback.print_exc()
            return {
                "submit": False,
                "guess": [],
                "error": str(e),
            }

    def discover_workers(self) -> Dict[str, str]:
        """Dynamically discover worker URLs and capabilities from registry.

        Queries the registry for all agents with capabilities matching the
        boss-worker paradigm, then maps agent names to their URLs based on
        their agent cards (not hardcoded).
        """
        import httpx

        if not self.registry_url:
            print("[Boss] ⚠️  No registry URL configured, using fallback")
            return {
                "analyzer": "http://localhost:8201",
                "strategist": "http://localhost:8202",
                "proposer": "http://localhost:8203",
                "validator": "http://localhost:8204",
            }

        try:
            # Query registry for all agents in boss-worker paradigm
            resp = httpx.get(f"{self.registry_url}/agents", timeout=5.0)
            if resp.status_code != 200:
                raise Exception(f"Registry returned {resp.status_code}")

            data = resp.json()
            # Registry returns wrapped response: {payload: {agents: [...]}}
            agents_list = data.get("payload", {}).get("agents", [])
            worker_urls = {}

            # Map agents by their capabilities and agent card info
            for agent_info in agents_list:
                # agent_info is the full agent data from registry
                paradigm = agent_info.get("paradigm", "")
                agent_name = agent_info.get("agent_name", "").lower()
                url = agent_info.get("url", "")

                # Only include boss-worker paradigm agents
                if paradigm != "boss_worker" or not url:
                    continue

                # Map by agent name (Analyzer, Strategist, Proposer, Validator)
                if "analyzer" in agent_name.lower():
                    worker_urls["analyzer"] = url
                elif "strategist" in agent_name.lower():
                    worker_urls["strategist"] = url
                elif "proposer" in agent_name.lower():
                    worker_urls["proposer"] = url
                elif "validator" in agent_name.lower():
                    worker_urls["validator"] = url

            if worker_urls:
                print(f"[Boss] Discovered {len(worker_urls)} workers from registry")
                return worker_urls
            else:
                print("[Boss] ⚠️  No boss-worker agents found in registry, using fallback")
                raise Exception("No agents found")

        except Exception as e:
            print(f"[Boss] ⚠️  Registry discovery failed: {e}, using fallback URLs")
            # Fallback to hardcoded URLs if registry unavailable
            return {
                "analyzer": "http://localhost:8201",
                "strategist": "http://localhost:8202",
                "proposer": "http://localhost:8203",
                "validator": "http://localhost:8204",
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent."""
        return self.run_round(kwargs)

    def close(self) -> None:
        """Close any resources (stub for compatibility)."""
        pass
