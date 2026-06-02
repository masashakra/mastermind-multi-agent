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
import asyncio
import httpx
import uuid
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import A2ACommunicationLayer
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode
from base.role import AgentRole, ParadigmType, RoleContext


class AgentMemory:
    """Agent memory system for tracking sent/received messages.

    Each agent maintains:
    - inbox: Messages received from other agents
    - sent: Messages sent to other agents
    - deductions: Self-discovered facts/constraints
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.inbox: List[Dict[str, Any]] = []
        self.sent: List[Dict[str, Any]] = []
        self.deductions: Dict[str, Any] = {}

    def receive_message(
        self,
        from_agent: str,
        action: str,
        payload: Dict[str, Any],
        msg_id: str = "",
        is_reply: bool = False,
    ) -> None:
        """Store incoming message in inbox."""
        self.inbox.append({
            "from": from_agent,
            "action": action,
            "payload": payload,
            "msg_id": msg_id,
            "is_reply": is_reply,
            "timestamp": time.time(),
        })

    def send_message(
        self,
        to_agent: str,
        action: str,
        payload: Dict[str, Any],
        msg_id: str = "",
        is_question: bool = False,
    ) -> None:
        """Log outgoing message."""
        self.sent.append({
            "to": to_agent,
            "action": action,
            "payload": payload,
            "msg_id": msg_id,
            "is_question": is_question,
            "timestamp": time.time(),
        })

    def get_conversation_with(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get conversation history with specific agent."""
        conversation = []
        for msg in self.inbox:
            if msg["from"] == agent_id:
                conversation.append({"direction": "received", **msg})
        for msg in self.sent:
            if msg["to"] == agent_id:
                conversation.append({"direction": "sent", **msg})
        return sorted(conversation, key=lambda x: x["timestamp"])

    def get_memory_summary(self, max_messages: int = 5) -> Dict[str, Any]:
        """Format memory for LLM context."""
        return {
            "recent_inbox": self.inbox[-max_messages:],
            "recent_sent": self.sent[-max_messages:],
            "deductions": self.deductions,
        }

    def add_deduction(self, key: str, value: Any) -> None:
        """Add a learned fact/constraint."""
        self.deductions[key] = value


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
        # NEW: For round-table peer messaging
        registry_url: Optional[str] = None,
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

        # NEW: For round-table peer messaging (autonomous A2A communication)
        self.registry_url = registry_url
        self.http_client = httpx.AsyncClient(timeout=120.0)

        # NEW: Agent memory for tracking sent/received messages
        self.memory = AgentMemory(self.agent_id)

        # NEW: Persistent conversation thread (AutoGen-style multi-turn)
        # Each round's reasoning is added as an assistant message so the
        # LLM builds on its own prior thinking rather than starting fresh.
        self.conversation: List[Dict[str, str]] = []

    def _initialize_llm(self) -> None:
        """Initialize LLM client based on provider."""
        if self.provider == "kaggle":
            # Kaggle backend: remote Ollama-compatible API via ngrok
            kaggle_url = os.getenv("KAGGLE_URL")
            if not kaggle_url:
                raise ValueError("KAGGLE_URL environment variable not set")
            self.llm = {"url": kaggle_url, "type": "kaggle"}
        elif self.provider == "groq":
            # Groq API — load all available keys for rotation
            keys = []
            # Support GROQ_API_KEY_1 … GROQ_API_KEY_6
            for i in range(1, 7):
                k = os.getenv(f"GROQ_API_KEY_{i}")
                if k:
                    keys.append(k)
            # Also accept a single GROQ_API_KEY
            single = os.getenv("GROQ_API_KEY")
            if single and single not in keys:
                keys.append(single)
            if not keys:
                raise ValueError("No Groq API keys found. Set GROQ_API_KEY_1 … GROQ_API_KEY_6")
            print(f"[{self.name}] Groq: {len(keys)} key(s) loaded for rotation")
            self.llm = {
                "keys": keys,
                "key_index": 0,         # current key pointer
                "type": "groq",
                "model": "qwen/qwen3-32b"  # Reasoning model with <think> tokens
            }
        elif self.provider == "deepseek":
            # DeepSeek direct API — OR — OpenRouter (free $1 credit)
            # Priority: OPENROUTER_API_KEY → DEEPSEEK_API_KEY
            or_key = os.getenv("OPENROUTER_API_KEY")
            ds_key = os.getenv("DEEPSEEK_API_KEY")
            if or_key:
                self.llm = {
                    "api_key": or_key,
                    "type": "deepseek",
                    "model": "deepseek/deepseek-r1",   # R1 via OpenRouter
                    "base_url": "https://openrouter.ai/api/v1",
                }
                print(f"[{self.name}] DeepSeek R1 via OpenRouter")
            elif ds_key:
                self.llm = {
                    "api_key": ds_key,
                    "type": "deepseek",
                    "model": "deepseek-reasoner",
                    "base_url": "https://api.deepseek.com",
                }
                print(f"[{self.name}] DeepSeek R1 via DeepSeek API")
            else:
                raise ValueError(
                    "No DeepSeek key found.\n"
                    "  Free option: sign up at openrouter.ai → set OPENROUTER_API_KEY\n"
                    "  Paid option: platform.deepseek.com → set DEEPSEEK_API_KEY"
                )
        elif self.provider == "openai":
            # OpenAI — o3-mini is #1 for Mastermind (MastermindEval 2025: ~100% solve rate)
            oai_key = os.getenv("OPENAI_API_KEY")
            if not oai_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.llm = {
                "api_key": oai_key,
                "type": "openai",
                "model": "o3-mini",
                "base_url": "https://api.openai.com/v1",
            }
            print(f"[{self.name}] OpenAI o3-mini ready")
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

    def call_llm_conversation(self, system_prompt: str, user_message: str) -> str:
        """Call LLM with full conversation history (AutoGen-style multi-turn).

        Each call appends to self.conversation so the model sees all its
        prior reasoning — it builds on its own thoughts across rounds
        instead of starting from scratch every time.

        Args:
            system_prompt: Role definition (stays fixed across all rounds)
            user_message:  Current round's input (just this round's info)

        Returns:
            LLM response as string
        """
        if self.provider not in ("groq", "deepseek", "openai"):
            # Fallback for other providers: flatten to single prompt
            history_text = ""
            for msg in self.conversation[-10:]:
                role = "You said" if msg["role"] == "assistant" else "Input"
                history_text += f"\n{role}: {msg['content'][:200]}"
            full_prompt = f"{system_prompt}\n\nPREVIOUS REASONING:{history_text}\n\nCURRENT INPUT:\n{user_message}"
            response = self.call_llm(full_prompt)
        else:
            # Groq / DeepSeek: true multi-turn — pass all prior messages
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation[-20:])  # last 20 messages max
            messages.append({"role": "user", "content": user_message})

            self.call_count += 1
            import requests as _req
            response = None

            if self.provider == "openai":
                import requests as _req
                for attempt in range(3):
                    try:
                        resp = _req.post(
                            f"{self.llm['base_url']}/chat/completions",
                            headers={"Authorization": f"Bearer {self.llm['api_key']}"},
                            json={
                                "model": self.llm["model"],
                                "messages": messages,
                                "reasoning_effort": "medium",
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            response = resp.json()["choices"][0]["message"]["content"]
                            break
                        elif resp.status_code == 429:
                            time.sleep(15 * (attempt + 1))
                        else:
                            resp.raise_for_status()
                    except Exception as e:
                        print(f"[{self.name}] OpenAI error: {e}")
                        time.sleep(5)
            elif self.provider == "deepseek":
                # DeepSeek single key, retry on failure
                for attempt in range(3):
                    try:
                        resp = _req.post(
                            f"{self.llm['base_url']}/chat/completions",
                            headers={"Authorization": f"Bearer {self.llm['api_key']}"},
                            json={
                                "model": self.llm["model"],
                                "messages": messages,
                                "max_tokens": 8000,
                                "temperature": 0.6,
                            },
                            timeout=180,
                        )
                        if resp.status_code == 200:
                            msg = resp.json()["choices"][0]["message"]
                            response = msg.get("content", "") or msg.get("reasoning_content", "")
                            break
                        elif resp.status_code == 429:
                            wait = 15 * (attempt + 1)
                            print(f"[{self.name}] DeepSeek rate-limited, waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            resp.raise_for_status()
                    except Exception as e:
                        print(f"[{self.name}] DeepSeek error: {e}")
                        time.sleep(5)
            else:
                # Groq: rotate through keys
                keys = self.llm["keys"]
                total_attempts = len(keys) * 2

                for attempt in range(total_attempts):
                    key_idx = self.llm["key_index"] % len(keys)
                    current_key = keys[key_idx]
                    try:
                        resp = _req.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {current_key}"},
                            json={
                                "model": self.llm["model"],
                                "messages": messages,
                                "max_tokens": 4096,
                                "temperature": 0.6,
                            },
                            timeout=60
                        )
                        if resp.status_code == 200:
                            response = resp.json()["choices"][0]["message"]["content"]
                            break
                        elif resp.status_code == 429:
                            self.llm["key_index"] = (key_idx + 1) % len(keys)
                            print(f"[{self.name}] Groq key {key_idx+1} rate-limited, rotating...")
                            time.sleep(2)
                        else:
                            resp.raise_for_status()
                    except Exception as e:
                        self.llm["key_index"] = (key_idx + 1) % len(keys)
                        time.sleep(1)
                        continue

            if response is None:
                raise RuntimeError(f"LLM call failed after all attempts")

        # Store in conversation thread
        self.conversation.append({"role": "user",      "content": user_message})
        self.conversation.append({"role": "assistant",  "content": response})

        return response

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

        # No artificial sleep needed — key rotation handles Groq rate limits

        try:
            if self.provider == "kaggle":
                # Kaggle backend: POST to remote Ollama API with retry on connection drops
                url = self.llm["url"]
                model = os.getenv("KAGGLE_MODEL", "llama3.1:8b")

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            f"{url}/api/generate",
                            json={"model": model, "prompt": prompt, "stream": False},
                            timeout=300
                        )
                        response.raise_for_status()
                        result = response.json()
                        return result.get("response", "")
                    except (requests.exceptions.ConnectionError,
                            requests.exceptions.ChunkedEncodingError) as e:
                        if attempt < max_retries - 1:
                            wait = 5 * (attempt + 1)
                            print(f"[{self.name}] Connection dropped, retrying in {wait}s (attempt {attempt+1}/{max_retries})...")
                            time.sleep(wait)
                        else:
                            raise
            elif self.provider == "groq":
                # Groq API — rotate through keys on rate-limit (429) or timeout
                keys = self.llm["keys"]
                total_attempts = len(keys) * 2  # try each key up to twice
                for attempt in range(total_attempts):
                    key_idx = self.llm["key_index"] % len(keys)
                    current_key = keys[key_idx]
                    try:
                        response = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {current_key}"},
                            json={
                                "model": self.llm["model"],
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 1024,
                                "temperature": 0.7
                            },
                            timeout=60
                        )
                        if response.status_code == 200:
                            result = response.json()
                            return result["choices"][0]["message"]["content"]
                        elif response.status_code == 429:
                            # Rate limited — rotate to next key
                            self.llm["key_index"] = (key_idx + 1) % len(keys)
                            print(f"[{self.name}] Groq key {key_idx+1} rate-limited, rotating to key {self.llm['key_index']+1}...")
                            time.sleep(2)
                            continue
                        else:
                            response.raise_for_status()
                    except requests.exceptions.Timeout:
                        self.llm["key_index"] = (key_idx + 1) % len(keys)
                        print(f"[{self.name}] Groq key {key_idx+1} timed out, rotating to key {self.llm['key_index']+1}...")
                        continue
                    except requests.exceptions.ConnectionError:
                        self.llm["key_index"] = (key_idx + 1) % len(keys)
                        print(f"[{self.name}] Groq key {key_idx+1} connection error, rotating to key {self.llm['key_index']+1}...")
                        time.sleep(2)
                        continue
                raise RuntimeError(f"All {len(keys)} Groq keys exhausted after {total_attempts} attempts")
            elif self.provider == "deepseek":
                # DeepSeek API — OpenAI-compatible, R1 reasons via reasoning_content
                for attempt in range(3):
                    try:
                        resp = requests.post(
                            f"{self.llm['base_url']}/chat/completions",
                            headers={"Authorization": f"Bearer {self.llm['api_key']}"},
                            json={
                                "model": self.llm["model"],
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 4096,
                                "temperature": 0.6,
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            msg = resp.json()["choices"][0]["message"]
                            # R1 returns reasoning in reasoning_content, answer in content
                            response = msg.get("content", "") or msg.get("reasoning_content", "")
                            break
                        elif resp.status_code == 429:
                            wait = 10 * (attempt + 1)
                            print(f"[{self.name}] DeepSeek rate-limited, waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            resp.raise_for_status()
                    except requests.exceptions.Timeout:
                        print(f"[{self.name}] DeepSeek timeout (attempt {attempt+1}/3)")
                        time.sleep(5)
                else:
                    raise RuntimeError("DeepSeek API failed after 3 attempts")
            elif self.provider == "openai":
                import requests as _req
                for attempt in range(3):
                    try:
                        resp = _req.post(
                            f"{self.llm['base_url']}/chat/completions",
                            headers={"Authorization": f"Bearer {self.llm['api_key']}"},
                            json={
                                "model": self.llm["model"],
                                "messages": [{"role": "user", "content": prompt}],
                                "reasoning_effort": "medium",  # low/medium/high
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            response = resp.json()["choices"][0]["message"]["content"]
                            break
                        elif resp.status_code == 429:
                            time.sleep(15 * (attempt + 1))
                        else:
                            resp.raise_for_status()
                    except requests.exceptions.Timeout:
                        time.sleep(5)
                else:
                    raise RuntimeError("OpenAI API failed after 3 attempts")
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
        # Strip Qwen3 / DeepSeek-R1 <think>...</think> reasoning blocks first
        import re as _re
        clean = _re.sub(r'<think>.*?</think>', '', response, flags=_re.DOTALL).strip()
        if not clean:
            clean = response  # fallback if entire response was thinking

        try:
            # Try direct parsing first
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        for fence in ["```json", "```"]:
            if fence in clean:
                try:
                    start = clean.index(fence) + len(fence)
                    end = clean.index("```", start)
                    json_str = clean[start:end].strip()
                    return json.loads(json_str)
                except (ValueError, json.JSONDecodeError):
                    pass

        # Try finding bare JSON object
        match = _re.search(r'\{.*\}', clean, _re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # If all parsing fails, return error
        return {
            "error": "Failed to parse JSON response",
            "raw_response": response[:200]
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

    # ── NEW: Autonomous Peer Messaging (Round-Table Paradigm) ──────────────────

    async def discover_peer(self, peer_type: str) -> str:
        """Discover peer agent URL via registry.

        Args:
            peer_type: Agent type to discover (e.g., "strategist", "analyzer")

        Returns:
            Peer agent URL (e.g., "http://localhost:8102")

        Raises:
            RuntimeError: If peer cannot be discovered
        """
        if not self.registry_url:
            raise RuntimeError("registry_url not set - cannot discover peers")

        try:
            resp = await self.http_client.get(
                f"{self.registry_url}/agents/type/{peer_type}",
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # Response may be wrapped in A2AMessage
            if "payload" in data:
                agents = data["payload"].get("agents", [])
            else:
                agents = data if isinstance(data, list) else data.get("agents", [])

            if agents:
                url = agents[0].get("url")
                if url:
                    return url

            raise RuntimeError(f"No {peer_type} agents found in registry")

        except Exception as e:
            raise RuntimeError(f"Failed to discover {peer_type}: {str(e)}")

    async def send_a2a_message(
        self,
        receiver_type: str,
        action: str,
        payload: Dict[str, Any],
        is_question: bool = False,
        retries: int = 2,
    ) -> Dict[str, Any]:
        """Send A2A message to peer agent.

        Supports both:
        - Unidirectional (fire-and-forget): is_question=False
        - Bidirectional (wait for reply): is_question=True

        Args:
            receiver_type: Type of receiver (e.g., "strategist")
            action: Action endpoint (e.g., "strategy", "propose")
            payload: Message payload
            is_question: If True, wait for direct reply (bidirectional)
            retries: Number of retry attempts on failure

        Returns:
            Response payload from receiver

        Raises:
            RuntimeError: If message send fails after retries
        """
        msg_id = str(uuid.uuid4())[:8]

        for attempt in range(retries):
            try:
                # Discover peer
                peer_url = await self.discover_peer(receiver_type)

                # Create A2A request message
                request_msg = A2AMessage.request(
                    sender_id=f"{self.agent_id}_round_table",
                    receiver_id=f"{receiver_type}_round_table",
                    action=action,
                    payload=payload,
                    is_question=is_question,
                )

                msg_type = "Q" if is_question else "→"
                print(
                    f"[{self.name}{msg_type}A2A] POST {peer_url}/{action} "
                    f"(msg_id={msg_id}, attempt {attempt+1})"
                )

                # Send HTTP POST with A2A envelope
                resp = await self.http_client.post(
                    f"{peer_url}/{action}",
                    json=request_msg.to_dict(),
                    timeout=30.0,
                )

                # Parse response
                if resp.status_code == 200:
                    response_data = resp.json()

                    # Handle A2AMessage response
                    if isinstance(response_data, dict) and "message_id" in response_data:
                        response_msg = A2AMessage.from_dict(response_data)
                        if response_msg.status == A2AStatus.OK:
                            # Log in memory
                            if is_question:
                                self.memory.receive_message(
                                    receiver_type,
                                    action,
                                    response_msg.payload,
                                    response_msg.message_id,
                                    is_reply=True
                                )
                                print(
                                    f"[{self.name}←REPLY] {action} ✓ "
                                    f"(msg_id={msg_id})"
                                )
                            else:
                                self.memory.send_message(
                                    receiver_type,
                                    action,
                                    payload,
                                    msg_id,
                                    is_question=False
                                )
                            return response_msg.payload
                        else:
                            error = response_msg.error_message or "Unknown error"
                            print(
                                f"[{self.name}←A2A] {action} ERROR: {error}"
                            )
                            if attempt < retries - 1:
                                await asyncio.sleep(0.5)
                            continue
                    else:
                        # Unwrapped response
                        self.memory.send_message(
                            receiver_type,
                            action,
                            payload,
                            msg_id,
                            is_question=is_question
                        )
                        print(
                            f"[{self.name}←A2A] {action} ✓ "
                            f"(msg_id={msg_id})"
                        )
                        return response_data

                else:
                    error_msg = resp.text or f"HTTP {resp.status_code}"
                    print(
                        f"[{self.name}←A2A] {action} HTTP {resp.status_code}: {error_msg[:50]}"
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(0.5)
                    continue

            except httpx.TimeoutException:
                print(
                    f"[{self.name}] Timeout calling {action} "
                    f"(attempt {attempt+1})"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                continue
            except Exception as e:
                print(
                    f"[{self.name}] Error calling {action}: {e} "
                    f"(attempt {attempt+1})"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(0.5)
                continue

        raise RuntimeError(
            f"[{self.name}] Failed to send to {receiver_type} after {retries} attempts"
        )

    async def decide_next_peer(
        self,
        my_work: Dict[str, Any],
        available_peers: List[str],
        game_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use LLM to decide which peer to send message to next.

        Args:
            my_work: Output from this agent's work
            available_peers: List of peers available to send to
            game_state: Current game state

        Returns:
            {"next_peer": str, "action": str, "reasoning": str, "confidence": float}
        """
        role_ctx = self.get_role_system_prompt()

        # Map peers to their action endpoints for clarity
        peer_actions = {
            "analyzer": "analyze",
            "strategist": "strategy",
            "proposer": "propose",
            "validator": "validate",
        }

        # Build clear peer options with descriptions
        peer_options = []
        for peer in available_peers:
            action = peer_actions.get(peer, peer)
            peer_options.append(f"- {peer} (POST /{action})")

        # Get memory for context
        memory_summary = self.memory.get_memory_summary(max_messages=10)
        recent_messages = ""
        if memory_summary["recent_inbox"] or memory_summary["recent_sent"]:
            recent_messages = "\n\nRECENT MESSAGES:"
            for msg in memory_summary["recent_sent"][-3:]:
                recent_messages += f"\n- YOU sent to {msg['to']}: {msg['action']}"
            for msg in memory_summary["recent_inbox"][-3:]:
                recent_messages += f"\n- YOU received from {msg['from']}: {msg['action']}"

        prompt = f"""{role_ctx}

## YOUR TASK — Autonomous Peer Routing (WITH MEMORY)

You just completed your work. Now decide which peer to send it to.
{recent_messages}

YOUR WORK OUTPUT:
{json.dumps(my_work, indent=2)}

AVAILABLE PEERS (you can ONLY send to one of these):
{chr(10).join(peer_options)}

PEER DESCRIPTIONS & EXPECTED MESSAGE FLOW:
- analyzer: Receives feedback, extracts constraints → should send to strategist
- strategist: Receives constraints from analyzer → should send to proposer
- proposer: Receives strategy from strategist → should send to validator
- validator: Receives guess from proposer → sends to orchestrator (NOT in available_peers)
- YOUR ROLE: {self.role.value.upper()}

CRITICAL RULES:
✓ Send forward in the normal flow (analyzer→strategist→proposer→validator)
✗ DO NOT send back to someone you just received from (avoid loops!)
✗ DO NOT send to yourself
✓ MUST choose from available_peers only

Current game state: {json.dumps(game_state, indent=2)}

DECIDE: Which ONE peer should receive your work?

OUTPUT (JSON ONLY - no markdown, no code blocks):
{{
  "next_peer": "ONE of: {' | '.join(available_peers)}",
  "action": "{' | '.join(peer_actions.get(p, p) for p in available_peers)}",
  "reasoning": "Why this peer (1 sentence)",
  "confidence": 0.9
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "next_peer" not in result:
            # Fallback to sequential routing if LLM fails
            if "strategist" in available_peers:
                result = {
                    "next_peer": "strategist",
                    "action": "strategy",
                    "reasoning": "Default fallback",
                    "confidence": 0.3,
                }
            elif "proposer" in available_peers:
                result = {
                    "next_peer": "proposer",
                    "action": "propose",
                    "reasoning": "Default fallback",
                    "confidence": 0.3,
                }
            elif "validator" in available_peers:
                result = {
                    "next_peer": "validator",
                    "action": "validate",
                    "reasoning": "Default fallback",
                    "confidence": 0.3,
                }
            else:
                result = {
                    "next_peer": available_peers[0] if available_peers else "analyzer",
                    "action": peer_actions.get(available_peers[0], "analyze") if available_peers else "analyze",
                    "reasoning": "Default fallback",
                    "confidence": 0.3,
                }

        return result

    def get_role_system_prompt(self) -> str:
        """Get role-aware system prompt for this agent.

        Returns:
            System prompt with explicit role context
        """
        return f"""You are the {self.role.value if self.role else 'Agent'} in a peer-to-peer team.

ROLE: {self.role.value if self.role else 'Unknown'}
PARADIGM: {self.paradigm.value if self.paradigm else 'Unknown'}
TEAM: {', '.join(self.team_members) if self.team_members else 'None'}
CAN_COMMUNICATE: {self.can_communicate}
YOUR_RESPONSIBILITY: {', '.join(self.constraints_owned) if self.constraints_owned else 'General contribution'}

You are an autonomous AI agent. Make decisions based on:
1. Your explicit role and responsibilities
2. Game state and feedback
3. What will help the team succeed
4. Clear reasoning for your choices

You can communicate with other team members via A2A messages.
All your responses must be valid JSON."""

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
