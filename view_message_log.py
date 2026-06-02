#!/usr/bin/env python3
"""View and analyze A2A message logs from puzzle runs.

Usage:
    python3 view_message_log.py puzzle_run.log           # Show summary
    python3 view_message_log.py puzzle_run.log --full    # Show all entries
    python3 view_message_log.py puzzle_run.log --agent Analyzer  # Filter by agent
    python3 view_message_log.py puzzle_run.log --type conversation  # Filter by type
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse


def load_log(log_file: str) -> Dict[str, Any]:
    """Load JSON log file."""
    try:
        with open(log_file) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{log_file}': {e}")
        sys.exit(1)


def print_summary(data: Dict[str, Any]):
    """Print summary statistics."""
    puzzle_log = data.get("puzzle_run_log", {})
    entries = puzzle_log.get("entries", [])

    print("\n" + "=" * 80)
    print("A2A MESSAGE LOG SUMMARY")
    print("=" * 80)
    print(f"Total entries: {len(entries)}")
    print(f"Duration: {puzzle_log.get('start_datetime', 'N/A')}")

    # Count by type
    by_type = {}
    by_agent = {}
    for entry in entries:
        event_type = entry.get("event_type", "unknown")
        agent = entry.get("agent_name", "unknown")
        by_type[event_type] = by_type.get(event_type, 0) + 1
        by_agent[agent] = by_agent.get(agent, 0) + 1

    print("\n📊 By Event Type:")
    for event_type in sorted(by_type.keys()):
        print(f"  {event_type}: {by_type[event_type]}")

    print("\n👤 By Agent:")
    for agent in sorted(by_agent.keys()):
        print(f"  {agent}: {by_agent[agent]}")

    print("=" * 80 + "\n")


def print_full_log(data: Dict[str, Any]):
    """Print all log entries in readable format."""
    puzzle_log = data.get("puzzle_run_log", {})
    entries = puzzle_log.get("entries", [])

    print("\n" + "=" * 80)
    print("FULL MESSAGE LOG")
    print("=" * 80 + "\n")

    for i, entry in enumerate(entries, 1):
        event_type = entry.get("event_type", "?")
        agent = entry.get("agent_name", "?")
        timestamp = entry.get("datetime_str", "?")

        print(f"{i}. [{timestamp}] {agent} - {event_type}")

        # Print event-specific details
        if event_type == "a2a_send":
            print(f"   → Send to {entry.get('receiver_id', '?')} / {entry.get('action', '?')}")
            if entry.get("routing_decision"):
                print(f"     Routing: {entry['routing_decision']}")
            if entry.get("payload"):
                payload = entry["payload"]
                # Show key fields of payload
                if isinstance(payload, dict):
                    keys = list(payload.keys())[:3]
                    print(f"     Payload keys: {', '.join(keys)}")

        elif event_type == "a2a_receive":
            print(f"   ← Received from {entry.get('sender_id', '?')} / {entry.get('action', '?')}")

        elif event_type == "conversation":
            role = entry.get("role", "?").upper()
            content = entry.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"   [{role}] {content}")

        elif event_type == "routing":
            routing = entry.get("routing_decision", "?")
            print(f"   🔀 {routing}")
            if entry.get("metadata", {}).get("reasoning"):
                print(
                    f"   Reason: {entry['metadata']['reasoning'][:100]}..."
                )

        elif event_type == "error":
            print(f"   ❌ {entry.get('error', '?')}")

        print()

    print("=" * 80 + "\n")


def filter_by_agent(data: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
    """Filter entries by agent name."""
    puzzle_log = data.get("puzzle_run_log", {})
    entries = puzzle_log.get("entries", [])
    filtered = [e for e in entries if agent_name.lower() in e.get("agent_name", "").lower()]
    puzzle_log["entries"] = filtered
    return {"puzzle_run_log": puzzle_log}


def filter_by_type(data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    """Filter entries by event type."""
    puzzle_log = data.get("puzzle_run_log", {})
    entries = puzzle_log.get("entries", [])
    filtered = [e for e in entries if e.get("event_type") == event_type]
    puzzle_log["entries"] = filtered
    return {"puzzle_run_log": puzzle_log}


def main():
    parser = argparse.ArgumentParser(
        description="View and analyze A2A message logs"
    )
    parser.add_argument("log_file", help="Path to puzzle_run.log file")
    parser.add_argument(
        "--full", action="store_true", help="Show full log (not just summary)"
    )
    parser.add_argument(
        "--agent", help="Filter by agent name (e.g., 'Analyzer')"
    )
    parser.add_argument(
        "--type", dest="event_type", help="Filter by event type (e.g., 'conversation')"
    )

    args = parser.parse_args()

    # Load log
    data = load_log(args.log_file)

    # Apply filters
    if args.agent:
        data = filter_by_agent(data, args.agent)
    if args.event_type:
        data = filter_by_type(data, args.event_type)

    # Print output
    if args.full:
        print_full_log(data)
    else:
        print_summary(data)

    # Show filtered entries count
    entries = data.get("puzzle_run_log", {}).get("entries", [])
    if args.agent or args.event_type:
        print(f"Filtered to {len(entries)} entries\n")


if __name__ == "__main__":
    main()
