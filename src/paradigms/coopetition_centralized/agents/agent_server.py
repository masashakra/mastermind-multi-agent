"""
Coopetition Centralized — HTTP Servers for 4 agents (2 per team)

Team A: AnalyzerStrategist_A, Proposer_A
Team B: AnalyzerStrategist_B, Proposer_B

Each agent runs on a unique port and self-registers with the registry.
Judge is a LangGraph node in the Orchestrator (not an A2A agent).
"""

import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paradigms.coopetition_centralized.agents.analyzer_strategist import AnalyzerStrategistAgent
from paradigms.coopetition_centralized.agents.proposer import ProposerAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


# ── Agent Handler ───────────────────────────────────────────────────────────


def create_handler(agent):
    """Factory function to create handler with agent bound."""
    class AgentHTTPHandler(BaseHTTPRequestHandler):
        """HTTP request handler for agents."""

        def do_GET(self):
            """Handle health checks."""
            if self.path in ["/health", "/"]:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "agent": agent.name}).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            """Handle A2A messages on any path."""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
                message = json.loads(body) if body else {}
                print(f"[{agent.name}] Received: {message}")
                result = agent.handle_message(message)
                print(f"[{agent.name}] Responding: {result}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except json.JSONDecodeError as e:
                print(f"[{agent.name}] JSON decode error: {e}")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode())
            except Exception as e:
                print(f"[{agent.name}] Exception: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        def log_message(self, format, *args):
            """Suppress logging."""
            pass

    return AgentHTTPHandler


def create_agent_server(agent_class, agent_id: str, team: str, port: int, provider: str, registry_url: str):
    """Create and start an agent HTTP server."""

    comm_layer = A2ACommunicationLayer(registry_url=registry_url)
    agent = agent_class(
        team=team,
        provider=provider,
        comm_layer=comm_layer,
        paradigm=ParadigmType.COOPETITION_CENTRALIZED,
        registry_url=registry_url,
    )

    AgentHTTPHandler.agent = agent

    server = HTTPServer(("0.0.0.0", port), AgentHTTPHandler)

    def run_server():
        print(f"[AgentServer] {agent.name} starting on port {port}")
        server.serve_forever()

    thread = Thread(target=run_server, daemon=True)
    thread.start()

    time.sleep(0.5)  # Give server time to start
    agent.register_with_registry()
    print(f"[AgentServer] {agent.name} registered at http://localhost:{port}")

    return f"http://localhost:{port}"


def _register_agent_with_registry(registry_url: str, agent_id: str, agent_url: str) -> None:
    """Register agent with HTTP registry."""
    import requests
    try:
        card = {
            "agent_id": agent_id,
            "agent_name": agent_id,
            "agent_type": "analyzer" if "analyzer" in agent_id else "proposer",
            "paradigm": "coopetition_centralized",
            "url": agent_url,
            "capabilities": [],
            "constraints_owned": [],
            "team_members": [],
        }
        response = requests.post(f"{registry_url}/register", json=card, timeout=5)
        if response.status_code == 200:
            print(f"[Registry] ✓ Registered {agent_id}")
        else:
            print(f"[Registry] ✗ Failed to register {agent_id}: {response.status_code}")
    except Exception as e:
        print(f"[Registry] ✗ Error registering {agent_id}: {e}")


def start_agent_servers(
    provider: str = "deepseek",
    registry_url: str = "http://localhost:8100",
    base_port: int = 8301,
) -> Dict[str, str]:
    """Start all 4 agent servers (2 per team).

    Judge is a LangGraph node in Orchestrator, not an A2A agent.
    """

    agent_configs = [
        (AnalyzerStrategistAgent, "analyzer_strategist_a", "A", base_port),
        (ProposerAgent, "proposer_a", "A", base_port + 1),
        (AnalyzerStrategistAgent, "analyzer_strategist_b", "B", base_port + 2),
        (ProposerAgent, "proposer_b", "B", base_port + 3),
    ]

    agent_urls = {}
    for agent_class, agent_id, team, port in agent_configs:
        comm_layer = A2ACommunicationLayer()
        agent = agent_class(
            team=team,
            provider=provider,
            comm_layer=comm_layer,
            paradigm=ParadigmType.COOPETITION_CENTRALIZED,
            registry_url=registry_url,
        )

        handler = create_handler(agent)
        server = HTTPServer(("127.0.0.1", port), handler)

        def run_server(srv=server, ag=agent):
            print(f"[AgentServer] {ag.name} starting on port {port}")
            srv.serve_forever()

        thread = Thread(target=run_server, daemon=True)
        thread.start()

        time.sleep(0.5)  # Give server time to start

        agent_url = f"http://localhost:{port}"
        _register_agent_with_registry(registry_url, agent_id, agent_url)

        agent_urls[agent_id] = agent_url

    return agent_urls
