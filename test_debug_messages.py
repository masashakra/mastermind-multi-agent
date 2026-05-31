#!/usr/bin/env python3
"""Debug: Print exact payloads being sent between agents."""
import sys
sys.path.insert(0, 'src')

# Patch the agent_server to print payloads
import os
agent_server_path = 'src/paradigms/round_table/agents/agent_server.py'

with open(agent_server_path, 'r') as f:
    content = f.read()

# Find the send_a2a_message calls and add logging
if 'payload=result' in content:
    print("Found 'payload=result' sends")
    print("\nThis means agents send only their result, not the full incoming payload")
    print("\nBut proposer still receives available_colors...")
    print("\n=== MYSTERY ===")
    print("If Strategist sends payload=result (which doesn't have available_colors)")
    print("How does Proposer receive available_colors in msg.payload?")
    print("\nTheory 1: The orchestrator KEEPS sending to all agents")
    print("Theory 2: available_colors is being merged somewhere")
    print("Theory 3: The agents are passing game_state instead of result")

    # Check if game_state is being sent instead
    if 'payload=game_state' in content:
        print("\n✓ FOUND IT: Agents are sending game_state (full incoming payload)!")
    elif 'payload=msg.payload' in content:
        print("\n✓ FOUND IT: Agents are sending msg.payload directly!")
    else:
        print("\nMust check if game_state = msg.payload is being used...")
