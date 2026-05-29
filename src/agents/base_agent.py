# Base Agent Class
# Abstract base for all agents (Strategist, Analyzer, Proposer, Validator)
# Handles LLM calls, error handling, response parsing
# Supports Kaggle (primary), Ollama (local), or Claude API

import json
import os
import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import requests


class BaseAgent(ABC):
    """Base class for all worker agents.

    Provides:
    - LLM interface (Ollama or Claude)
    - Response parsing (JSON)
    - Error handling
    - Token tracking (optional)

    Subclasses implement specific agent roles.
    """

    def __init__(self, name: str, model: str = "mistral-7b", provider: str = "ollama"):
        """Initialize base agent.

        Args:
            name: Agent name (e.g., "Strategist", "Analyzer")
            model: Model identifier (e.g., "mistral-7b" for Ollama, "claude-3-sonnet" for Claude)
            provider: "ollama" (dev) or "claude" (final)
        """
        self.name = name
        self.model = model
        self.provider = provider
        self.llm = None
        self._initialize_llm()
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

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

        # Rate limiting for Groq API (free tier is strict: ~30 req/min = 2 sec per request)
        if self.provider == "groq":
            time.sleep(2.0)

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
                # Groq API - OpenAI compatible
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

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary with call count and token usage
        """
        return {
            "agent_name": self.name,
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
