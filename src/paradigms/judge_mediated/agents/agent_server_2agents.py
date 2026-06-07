"""HTTP Servers for 2-Agent Architecture
Starts both Analyzer-Strategist and Proposer agents for each team
"""

import sys
from pathlib import Path
import asyncio
from typing import Any, Dict
import threading
import time
import socket
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
import uvicorn

from paradigms.judge_mediated.agents.analyzer_strategist import AnalyzerStrategistAgent
from paradigms.judge_mediated.agents.proposer_agent import ProposerAgent
from communication.a2a_message import A2AMessage, A2AStatus


def _kill_port(port: int) -> None:
    """⭐ CRITICAL FIX: Kill any existing process on this port."""
    try:
        # Use lsof to find process on port
        result = subprocess.run(
            f"lsof -ti :{port}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(f"kill -9 {pid}", shell=True, timeout=2)
                        print(f"[PortCleanup] Killed process {pid} on port {port}")
                    except:
                        pass
            time.sleep(0.5)  # Wait for port to be released
    except Exception as e:
        print(f"[PortCleanup] Warning: Could not clean port {port}: {e}")


def _port_is_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0  # Return True if NOT connected (port available)
    except:
        return False


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

            # ⭐ REFLECTION/LEARNING: Pass last_feedback for hypothesis validation
            last_feedback = payload.get("last_feedback", {})

            result = agent.propose_guess(
                strategy=payload.get("strategy", {}),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
                round_num=payload.get("round_num", 1),
                last_feedback=last_feedback,  # ⭐ NEW: For reflection/learning loop
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

    @app.post("/reflect_on_feedback")
    def reflect_on_feedback(body: Dict[str, Any]) -> Dict[str, Any]:
        """Reflect on feedback to build learned hypotheses (Active Learning)."""
        try:
            round_num = body.get("round_num", 1)
            guess = body.get("guess", [])
            feedback = body.get("feedback", {})

            # ⭐ ACTIVE LEARNING: Agent processes feedback to accumulate knowledge
            agent.reflect_on_feedback(round_num, guess, feedback)

            return {
                "status": "ok",
                "message": f"Reflected on Round {round_num} feedback",
                "learned_hypotheses_count": len(agent.learned_hypotheses),
            }
        except Exception as e:
            print(f"[ERROR] Proposer Team {team_id} reflect: {str(e)}")
            return {"status": "error", "message": str(e)}

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

    # ⭐ CRITICAL FIX: Kill any existing processes on these ports
    print(f"[AgentServer] Cleaning up ports {analyzer_port}, {proposer_port}...")
    _kill_port(analyzer_port)
    _kill_port(proposer_port)

    # Wait for OS to release ports
    time.sleep(0.5)

    # Verify ports are available
    if not _port_is_available(analyzer_port):
        print(f"[AgentServer] WARNING: Port {analyzer_port} still in use, proceeding anyway...")
    if not _port_is_available(proposer_port):
        print(f"[AgentServer] WARNING: Port {proposer_port} still in use, proceeding anyway...")

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

    # Wait for servers to initialize and health check
    print(f"[AgentServer] Waiting for Team {team_id} servers to initialize...")
    max_retries = 10
    for attempt in range(max_retries):
        try:
            import httpx
            with httpx.Client() as client:
                analyzer_resp = client.get(f"http://127.0.0.1:{analyzer_port}/health", timeout=2)
                proposer_resp = client.get(f"http://127.0.0.1:{proposer_port}/health", timeout=2)
                if analyzer_resp.status_code == 200 and proposer_resp.status_code == 200:
                    print(f"[AgentServer] Team {team_id} servers health check OK!")
                    break
        except:
            pass
        if attempt < max_retries - 1:
            time.sleep(0.5)
        else:
            print(f"[AgentServer] WARNING: Health check failed after {max_retries} attempts, proceeding anyway...")

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
