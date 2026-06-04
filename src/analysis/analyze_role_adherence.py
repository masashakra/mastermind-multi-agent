"""
Main analyzer for evaluating agent role adherence from puzzle run logs.
"""

import json
from typing import Dict, List
from pathlib import Path

from .message_log_parser import MessageLogParser, extract_message_text_for_analysis
from .role_adherence_judge import RoleAdherenceJudge, print_role_adherence_report


class RoleAdherenceAnalyzer:
    """Analyzes agent role adherence from puzzle run logs."""

    def __init__(self, log_file: str):
        """Initialize analyzer with log file."""
        self.log_file = log_file
        self.parser = MessageLogParser(log_file)
        self.judge = RoleAdherenceJudge()

    def analyze(self) -> Dict:
        """
        Perform full role adherence analysis.

        Returns:
            Dict with:
                - evaluation_results: from judge
                - message_details: detailed message analysis
                - summary: text summary
        """
        # Parse messages
        print(f"📖 Parsing log file: {self.log_file}")
        messages = self.parser.parse()
        print(f"✅ Found {len(messages)} A2A messages")

        # Display summary
        self.parser.print_summary()

        # Extract messages by agent for analysis
        print("\n🔍 Extracting messages for role adherence analysis...")

        messages_text_by_agent: Dict[str, List[str]] = self.parser.get_messages_by_agent()

        for agent_name, agent_messages in messages_text_by_agent.items():
            print(f"  {agent_name.upper()}: {len(agent_messages)} messages to evaluate")

        # Evaluate role adherence
        print("\n⚖️  Evaluating role adherence with LLM judge...")
        evaluation_results = self.judge.evaluate_message_log(messages_text_by_agent)

        # Print report
        report = print_role_adherence_report(evaluation_results)
        print(report)

        # Save results
        return {
            "evaluation_results": evaluation_results,
            "messages_by_agent": messages_text_by_agent,
            "summary": report,
        }

    def analyze_and_save(
        self, output_file: str = None
    ) -> Dict:
        """
        Analyze and save results to file.

        Args:
            output_file: Optional output file path. Defaults to ./role_adherence_report.json

        Returns:
            Dictionary with results
        """
        if output_file is None:
            output_file = Path(self.log_file).parent / "role_adherence_report.json"

        print(f"\n💾 Saving detailed results to: {output_file}")

        results = self.analyze()

        # Prepare data for JSON serialization
        json_results = {
            "evaluation_results": {
                "overall_adherence_pct": results["evaluation_results"]["overall_adherence_pct"],
                "total_messages": results["evaluation_results"]["total_messages"],
                "results_by_agent": {}
            },
            "analysis_summary": results["summary"],
        }

        # Process agent results
        for agent_name, agent_data in results["evaluation_results"]["results_by_agent"].items():
            json_results["evaluation_results"]["results_by_agent"][agent_name] = {
                "role_adherence_pct": agent_data["role_adherence_pct"],
                "total_messages": agent_data["total_messages"],
                "role_specific_count": agent_data["role_specific_count"],
                "avg_confidence": float(agent_data["avg_confidence"]),
            }

        # Add detailed message analysis
        detailed_messages = {}
        for agent_name, messages in results["messages_by_agent"].items():
            detailed_messages[agent_name] = [
                {
                    "content": msg[:100] + "..." if len(msg) > 100 else msg,
                    "full_length": len(msg),
                }
                for msg in messages
            ]

        json_results["detailed_messages"] = detailed_messages

        # Save to file
        with open(output_file, "w") as f:
            json.dump(json_results, f, indent=2)

        print(f"✅ Report saved: {output_file}")
        return results


def main():
    """Main entry point for role adherence analysis."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_role_adherence.py <log_file> [output_file]")
        print("\nExample:")
        print("  python analyze_role_adherence.py puzzle_run.log")
        print("  python analyze_role_adherence.py puzzle_run.log results.json")
        sys.exit(1)

    log_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    analyzer = RoleAdherenceAnalyzer(log_file)
    analyzer.analyze_and_save(output_file)


if __name__ == "__main__":
    main()
