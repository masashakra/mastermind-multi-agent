#!/usr/bin/env python3
"""Debug script: Dump all agent conversations from a completed puzzle run.

Run this during or after a puzzle to see what agents were thinking.

Usage:
    # During a run, in another terminal:
    python3 debug_agent_conversations.py

    # Or with environment variable for verbose payloads:
    VERBOSE_A2A=1 python3 test_puzzle.py MM_002 openai
"""
import sys
import os
sys.path.insert(0, 'src')

import asyncio
import httpx
import json

# Agent servers to query
AGENTS = [
    ("Analyzer", "http://localhost:8101"),
    ("Strategist", "http://localhost:8102"),
    ("Proposer", "http://localhost:8103"),
    ("Validator", "http://localhost:8104"),
]

async def get_agent_conversation(name: str, url: str) -> str:
    """Query an agent's conversation history."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Hit the health endpoint to get agent info
            # (We'll need to add an endpoint that returns conversation)
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                return f"[{name}] Agent is running"
            else:
                return f"[{name}] Agent returned {resp.status_code}"
    except Exception as e:
        return f"[{name}] Error: {e}"

async def main():
    print("\n" + "="*70)
    print("AGENT CONVERSATION DUMP")
    print("="*70)

    for name, url in AGENTS:
        result = await get_agent_conversation(name, url)
        print(f"{result}")

    print("\n" + "="*70)
    print("NOTE: To see full conversations, agents need to expose a /conversations endpoint")
    print("Currently, conversations are stored in-memory only during puzzle execution.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
