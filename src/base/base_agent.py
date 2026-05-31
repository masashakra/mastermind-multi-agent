# Base Agent Class
# Abstract base for all agents (Strategist, Analyzer, Proposer, Validator)
# Handles LLM calls, error handling, response parsing
# Supports Kaggle (primary), Ollama (local), or Claude API
# Uses A2A protocol for agent-to-agent communication
# NEW: Explicit role awareness for 30-50% better coordination (Adimulam et al. 2026)

import json
import os
import time
import sys
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import A2ACommunicationLayer, A2AMessage
from base.role import AgentRole, ParadigmType, RoleContext


class BaseAgent(ABC):
    """Base class for all worker agents.

    Provides:
    - LLM interface (Ollama or Claude)
    - Response parsing (JSON)
    - Error handling
    - Token tracking (optional)

    Subclasses implement specific agent roles.
    """

    def __init__(
        self,
        name: str,
        model: str = "mistral",
        provider: str = "ollama",
        comm_layer: Optional[A2ACommunicationLayer] = None,
        # NEW: Role awareness parameters (Adimulam et al. 2026)
        role: Optional[AgentRole] = None,
        paradigm: Optional[ParadigmType] = None,
        team_members: Optional[List[str]] = None,
        can_communicate: bool = True,
        constraints_owned: Optional[List[str]] = None,
    ):
        """Initialize base agent.

        Args:
            name: Agent name (e.g., "Strategist", "Analyzer")
            model: Model identifier (e.g., "mistral" for Ollama, "claude-3-sonnet" for Claude)
            provider: "ollama" (dev) or "claude" (final)
            comm_layer: A2A communication layer for agent-to-agent interaction
            role: Explicit agent role (NEW: for 30-50% better coordination)
            paradigm: Explicit paradigm type (NEW: for role awareness)
            team_members: List of agent IDs on the team (NEW: for coordination)
            can_communicate: Whether agent can send A2A requests (NEW: explicit flag)
            constraints_owned: List of constraints agent is responsible for (NEW: explicit awareness)
        """
        self.name = name
        self.agent_id = name.lower()  # Unique agent identifier
        self.model = model
        self.provider = provider
        self.llm = None
        self._initialize_llm()
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # A2A Communication
        self.comm_layer = comm_layer
        if self.comm_layer:
            self.comm_layer.register_agent(self.agent_id, self)

        # NEW: Role awareness (Adimulam et al. 2026 - 30-50% coordination improvement)
        self.role = role
        self.paradigm = paradigm
        self.team_members = team_members or []
        self.can_communicate = can_communicate
        self.constraints_owned = constraints_owned or []

        # Create RoleContext for explicit role awareness
        self.role_context = RoleContext(
            agent_id=self.agent_id,
            role=role or AgentRole.STRATEGIST,  # Default fallback
            paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=self.team_members,
            can_communicate=self.can_communicate,
            constraints_owned=self.constraints_owned
        )

    def _initialize_llm(self) -> None:
        """Initialize LLM client based on provider."""
        if self.provider == "kaggle":
            # Kaggle backend: remote Ollama-compatible API via ngrok
            kaggle_url = os.getenv("KAGGLE_URL")
            if not kaggle_url:
                raise ValueError("KAGGLE_URL environment variable not set")
            self.llm = {"url": kaggle_url, "type": "kaggle"}
        elif self.provider == "groq":
            # Groq API - OpenAI compatible
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("GROQ_API_KEY environment variable not set")
            self.llm = {
                "api_key": groq_key,
                "type": "groq",
                "model": "llama-3.1-8b-instant"  # Fast, currently available
            }
        elif self.provider == "ollama":
            try:
                from langchain_ollama import OllamaLLM
                self.llm = OllamaLLM(model=self.model)
            except ImportError:
                try:
                    from langchain.llms import Ollama
                    self.llm = Ollama(model=self.model)
                except ImportError:
                    raise ImportError("Install langchain-ollama: pip install langchain-ollama")
        elif self.provider == "claude":
            try:
                from anthropic import Anthropic
                self.llm = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                raise ImportError("Install anthropic: pip install anthropic")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def call_llm(self, prompt: str) -> str:
        """Call LLM with prompt and return response.

        Args:
            prompt: Complete prompt for LLM

        Returns:
            LLM response as string

        Raises:
            RuntimeError: If LLM call fails
        """
        self.call_count += 1

        # Rate limiting for Groq API (free tier: ~30 req/min = 2 sec per request minimum, but with 5 agents it's ~10 sec)
        if self.provider == "groq":
            time.sleep(6.0)

        try:
            if self.provider == "kaggle":
                # Kaggle backend: POST request to remote Ollama-compatible API
                url = self.llm["url"]
                model = os.getenv("KAGGLE_MODEL", "llama3.1:8b")

                response = requests.post(
                    f"{url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=300
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            elif self.provider == "groq":
                # Groq API - OpenAI compatible with retry on rate limit
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {self.llm['api_key']}"},
                            json={
                                "model": self.llm["model"],
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 1024,
                                "temperature": 0.7
                            },
                            timeout=30
                        )
                        response.raise_for_status()
                        result = response.json()
                        return result["choices"][0]["message"]["content"]
                    except requests.exceptions.HTTPError as e:
                        if response.status_code == 429 and attempt < max_retries - 1:
                            # Rate limited - backoff and retry
                            wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                            time.sleep(wait_time)
                            continue
                        raise
            elif self.provider == "ollama":
                # OllamaLLM uses invoke() method
                response = self.llm.invoke(prompt)
            elif self.provider == "claude":
                message = self.llm.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                response = message.content[0].text
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            return response

        except Exception as e:
            raise RuntimeError(f"LLM call failed for {self.name}: {str(e)}")

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.

        Handles:
        - Markdown code blocks (```json ... ```)
        - Direct JSON
        - Malformed JSON (returns error dict)

        Args:
            response: Raw LLM response text

        Returns:
            Parsed JSON dictionary or error dict
        """
        try:
            # Try direct parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```json" in response:
            try:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass

        # If all parsing fails, return error
        return {
            "error": "Failed to parse JSON response",
            "raw_response": response[:200]  # First 200 chars for debugging
        }

    def get_role_system_prompt(self) -> str:
        """Get explicit role context for agent prompts.

        NEW: Based on Adimulam et al. (2026) recommendation that agents
        explicitly stating their role and constraints improve coordination
        by 30-50%.

        Returns:
            System prompt with role context
        """
        return self.role_context.get_system_prompt()

    def send_request(
        self,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> A2AMessage:
        """Send a request to another agent via A2A protocol.

        NEW: Now validates that agent can communicate (explicit check)

        Args:
            receiver_id: Target agent ID
            action: Action to request
            payload: Request data

        Returns:
            Message object

        Raises:
            RuntimeError: If communication not allowed or layer not initialized
        """
        # NEW: Explicit communication validation
        if not self.can_communicate:
            raise RuntimeError(
                f"{self.role.value.upper()} cannot communicate directly "
                f"in {self.paradigm.value} paradigm"
            )

        if receiver_id not in self.team_members:
            raise RuntimeError(
                f"{self.role.value.upper()} cannot communicate with {receiver_id}. "
                f"Team members: {', '.join(self.team_members)}"
            )

        if not self.comm_layer:
            raise RuntimeError("Communication layer not initialized")

        return self.comm_layer.send_request(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            action=action,
            payload=payload
        )

    def send_response(
        self,
        receiver_id: str,
        correlation_id: str,
        payload: Dict[str, Any],
        status: str = "success"
    ) -> A2AMessage:
        """Send a response to another agent via A2A protocol.

        Args:
            receiver_id: Target agent ID
            correlation_id: Links to original request
            payload: Response data
            status: success or error

        Returns:
            Message object
        """
        if not self.comm_layer:
            raise RuntimeError("Communication layer not initialized")

        return self.comm_layer.send_response(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id,
            payload=payload,
            status=status
        )

    def get_messages(self) -> list:
        """Get all messages for this agent."""
        if not self.comm_layer:
            return []
        return self.comm_layer.get_agent_messages(self.agent_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary with call count and token usage
        """
        return {
            "agent_name": self.name,
            "agent_id": self.agent_id,
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "provider": self.provider,
            "model": self.model
        }

    @abstractmethod
    def process(self, **kwargs) -> Dict[str, Any]:
        """Process input and return agent-specific output.

        Implemented by subclasses.

        Args:
            **kwargs: Agent-specific arguments

        Returns:
            Agent-specific output dictionary
        """
        pass
