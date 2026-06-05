"""HTTP Servers for 2-Agent Architecture
Starts both Analyzer-Strategist and Proposer agents for each team
"""

import sys
from pathlib import Path
import asyncio
from typing import Any, Dict
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
import uvicorn

from paradigms.judge_mediated.agents.analyzer_strategist import AnalyzerStrategistAgent
from paradigms.judge_mediated.agents.proposer_agent import ProposerAgent
from communication.a2a_message import A2AMessage, A2AStatus


def create_analyzer_strategist_app(team_id: int, provider: str) -> FastAPI:
    """Create FastAPI app for Analyzer-Strategist agent."""
    app = FastAPI()
    try:
        agent = AnalyzerStrategistAgent(provider=provider)
    except ValueError as e:
        # No API keys available - create without provider and patch the call_llm method
        print(f"[AgentServer] Team {team_id}: Analyzer-Strategist: No API keys, using fallback mode")
        # Create agent with dummy provider, then it will fail and fall back to exception handling
        # which returns a fallback result
        import sys
        sys.stderr.write(f"[AgentServer] Bypassing LLM: {str(e)}\n")
        # Create a custom agent that doesn't require LLM initialization
        class MockAnalyzer(AnalyzerStrategistAgent):
            def _initialize_llm(self):
                self.llm = {"type": "mock"}  # Dummy LLM

            def call_llm(self, prompt: str) -> str:
                # Return a dummy response that will be caught by the fallback logic
                raise ValueError("Mock LLM: no API keys available")

        agent = MockAnalyzer(provider=provider)

    @app.post("/analyze_and_strategize")
    def analyze_and_strategize(body: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze constraints and develop strategy."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            # ⭐ AGENT MANAGES ITS OWN MEMORY
            # No longer passing analysis_history - agent uses self.analysis_history
            result = agent.analyze_and_strategize(
                guess_history=payload.get("guess_history", []),
                last_feedback=payload.get("last_feedback", {}),
                competitive_analysis=payload.get("competitive_analysis", {}),
                difficulty=payload.get("difficulty", "easy"),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
                round_num=payload.get("round_num", 1),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            return response_msg.to_dict()

        except Exception as e:
            print(f"[ERROR] Analyzer-Strategist Team {team_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "analyzer_strategist", "team": team_id}

    return app


def create_proposer_app(team_id: int, provider: str) -> FastAPI:
    """Create FastAPI app for Proposer agent."""
    app = FastAPI()
    try:
        agent = ProposerAgent(provider=provider)
    except ValueError as e:
        # No API keys available - create with mock LLM that will trigger fallback logic
        print(f"[AgentServer] Team {team_id}: Proposer: No API keys, using fallback mode")
        import sys
        sys.stderr.write(f"[AgentServer] Bypassing LLM: {str(e)}\n")

        class MockProposer(ProposerAgent):
            def _initialize_llm(self):
                self.llm = {"type": "mock"}  # Dummy LLM

            def call_llm(self, prompt: str) -> str:
                # Return a dummy response that will be caught by the fallback logic
                raise ValueError("Mock LLM: no API keys available")

        agent = MockProposer(provider=provider)

    @app.post("/propose_guess")
    def propose_guess(body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate guess from strategy."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            result = agent.propose_guess(
                strategy=payload.get("strategy", {}),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            return response_msg.to_dict()

        except Exception as e:
            print(f"[ERROR] Proposer Team {team_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "proposer", "team": team_id}

    return app


def start_agent_servers(
    provider: str,
    team_id: int,
    base_port: int = 8301,
) -> Dict[str, str]:
    """Start both agents for a team."""
    analyzer_port = base_port + (team_id - 1) * 50
    proposer_port = analyzer_port + 1

    print(f"\n[AgentServer] Team {team_id}")
    print(f"  Analyzer-Strategist starting on port {analyzer_port}...")
    print(f"  Proposer starting on port {proposer_port}...")

    analyzer_app = create_analyzer_strategist_app(team_id=team_id, provider=provider)
    analyzer_config = uvicorn.Config(
        analyzer_app,
        host="127.0.0.1",
        port=analyzer_port,
        log_level="warning",
    )
    analyzer_server = uvicorn.Server(analyzer_config)

    proposer_app = create_proposer_app(team_id=team_id, provider=provider)
    proposer_config = uvicorn.Config(
        proposer_app,
        host="127.0.0.1",
        port=proposer_port,
        log_level="warning",
    )
    proposer_server = uvicorn.Server(proposer_config)

    def run_analyzer():
        asyncio.run(analyzer_server.serve())

    def run_proposer():
        asyncio.run(proposer_server.serve())

    analyzer_thread = threading.Thread(target=run_analyzer, daemon=True, name=f"analyzer-{team_id}")
    proposer_thread = threading.Thread(target=run_proposer, daemon=True, name=f"proposer-{team_id}")

    analyzer_thread.start()
    proposer_thread.start()

    # Wait longer for servers to initialize
    time.sleep(3)

    analyzer_url = f"http://127.0.0.1:{analyzer_port}"
    proposer_url = f"http://127.0.0.1:{proposer_port}"

    print(f"[AgentServer] Team {team_id} agents online!")
    print(f"  Analyzer: {analyzer_url}")
    print(f"  Proposer: {proposer_url}")
    sys.stdout.flush()

    return {
        "analyzer_url": analyzer_url,
        "proposer_url": proposer_url,
    }
