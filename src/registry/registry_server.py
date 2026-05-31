"""
A2A Agent Registry — HTTP Server with standardized A2A protocol.

Agents POST their agent card here on startup (with validation).
Boss GETs agent URLs by type to discover workers.
All responses use A2AMessage envelope.
"""
import sys
import time
import threading
import uvicorn
import httpx
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request, Response
from typing import Dict, Any, List

from base.agent_card_schema import A2AAgentCard
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode

# ── FastAPI app ──────────────────────────────────────────────────────────────

registry_app = FastAPI(title="A2A Agent Registry (standardized)")

# In-memory store: agent_id → agent card dict
_registry: Dict[str, Dict[str, Any]] = {}

# ── Helper: Wrap response in A2AMessage ───────────────────────────────────────

def wrap_response(
    data: Any = None,
    status: A2AStatus = A2AStatus.OK,
    error_code: str = None,
    error_message: str = None,
) -> Response:
    """Wrap response in A2AMessage envelope."""
    msg = A2AMessage(
        message_id=f"reg_{int(time.time()*1000)}",
        timestamp=time.time(),
        sender_id="registry",
        receiver_id="caller",
        action="registry_response",
        payload=data or {},
        status=status,
        error_code=error_code,
        error_message=error_message,
    )
    status_code = 200
    if status == A2AStatus.ERROR:
        status_code = 500
    elif status == A2AStatus.INVALID:
        status_code = 400
    elif status == A2AStatus.NOT_FOUND:
        status_code = 404

    return Response(
        content=json.dumps(msg.to_dict()),
        status_code=status_code,
        media_type="application/json",
    )


# ── Registry endpoints ────────────────────────────────────────────────────────

@registry_app.post("/register")
def register_agent(data: Dict[str, Any]):
    """Register an agent card in the registry.

    Expects agent card dict with: agent_id, agent_name, agent_type, paradigm, url, capabilities
    """
    try:
        agent_id = data.get("agent_id")
        if not agent_id:
            return wrap_response(
                status=A2AStatus.INVALID,
                error_code=A2AErrorCode.MISSING_FIELD.value,
                error_message="agent_id is required",
            )

        # Convert to A2AAgentCard for validation
        card = A2AAgentCard.from_dict(data)
        errors = card.validate()
        if errors:
            return wrap_response(
                status=A2AStatus.INVALID,
                error_code=A2AErrorCode.INVALID_PAYLOAD.value,
                error_message="; ".join(errors),
            )

        # Store in registry
        card.registered_at = time.time()
        card.last_heartbeat = time.time()
        _registry[agent_id] = card.to_dict()
        print(f"[Registry] ✓ Registered: {agent_id} ({card.agent_type}) @ {card.url}")

        return wrap_response(
            data={"agent_id": agent_id, "registered_at": card.registered_at},
        )
    except Exception as e:
        return wrap_response(
            status=A2AStatus.ERROR,
            error_code=A2AErrorCode.INTERNAL_ERROR.value,
            error_message=str(e),
        )


@registry_app.get("/agents")
def list_all_agents():
    """List all registered agents."""
    return wrap_response(data={"agents": list(_registry.values())})


@registry_app.get("/agents/type/{agent_type}")
def get_agents_by_type(agent_type: str):
    """Get all agents of a specific type."""
    agents = [a for a in _registry.values() if a.get("agent_type") == agent_type]
    if not agents:
        return wrap_response(
            data={"agents": []},
            status=A2AStatus.NOT_FOUND,
        )
    return wrap_response(data={"agents": agents})


@registry_app.get("/agents/id/{agent_id}")
def get_agent_by_id(agent_id: str):
    """Get a specific agent by ID."""
    agent = _registry.get(agent_id)
    if not agent:
        return wrap_response(
            status=A2AStatus.NOT_FOUND,
            error_code=A2AErrorCode.AGENT_NOT_FOUND.value,
            error_message=f"Agent '{agent_id}' not found",
        )
    return wrap_response(data={"agent": agent})


@registry_app.post("/heartbeat")
def heartbeat(data: Dict[str, Any]):
    """Agent sends heartbeat to stay registered."""
    agent_id = data.get("agent_id")
    if agent_id not in _registry:
        return wrap_response(
            status=A2AStatus.NOT_FOUND,
            error_code=A2AErrorCode.AGENT_NOT_FOUND.value,
            error_message=f"Agent '{agent_id}' not registered",
        )

    _registry[agent_id]["last_heartbeat"] = time.time()
    return wrap_response(data={"agent_id": agent_id, "heartbeat_acked": True})


@registry_app.get("/health")
def health_check():
    """Health check endpoint."""
    return wrap_response(
        data={
            "registry_status": "ok",
            "total_agents": len(_registry),
            "registered_agents": list(_registry.keys()),
        },
    )


@registry_app.delete("/clear")
def clear_registry():
    """Clear all registrations (for testing)."""
    _registry.clear()
    return wrap_response(data={"cleared": True})


# ── Server lifecycle helpers ──────────────────────────────────────────────────

def start_registry_server(port: int = 8100) -> str:
    """Spin up the registry in a daemon thread. Returns its base URL."""
    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": "registry.registry_server:registry_app",
            "host": "0.0.0.0",
            "port": port,
            "log_level": "error",
        },
        daemon=True,
    )
    thread.start()
    url = f"http://localhost:{port}"
    _wait_for_healthy(url)
    return url


def _wait_for_healthy(url: str, retries: int = 20, delay: float = 0.3) -> None:
    for _ in range(retries):
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError(f"Registry at {url} never became healthy")
