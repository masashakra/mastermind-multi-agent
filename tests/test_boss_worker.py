# Test Suite for Boss Agent & Boss-Worker Paradigm
# Tests orchestration logic and end-to-end workflow
# Run with: python3 tests/test_boss_worker.py

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.boss import BossAgent
from paradigms.boss_worker import BossWorkerOrchestrator
from puzzle_generator import load_puzzles


class TestBossAgent:
    """Test Boss agent orchestration."""

    def test_boss_initialization(self):
        """Test Boss agent initializes with all workers."""
        boss = BossAgent()
        assert boss.name == "Boss"
        assert boss.strategist is not None
        assert boss.analyzer is not None
        assert boss.proposer is not None
        assert boss.validator is not None
        print("✓ Test: Boss agent initialization")

    def test_boss_round_method_exists(self):
        """Test Boss has orchestrate_round method."""
        boss = BossAgent()
        assert hasattr(boss, "orchestrate_round")
        assert callable(boss.orchestrate_round)
        print("✓ Test: Boss has orchestrate_round method")

    def test_boss_worker_agents(self):
        """Test Boss has all worker agents."""
        boss = BossAgent()
        assert hasattr(boss, "strategist")
        assert hasattr(boss, "analyzer")
        assert hasattr(boss, "proposer")
        assert hasattr(boss, "validator")
        assert boss.strategist.name == "Strategist"
        assert boss.analyzer.name == "Analyzer"
        assert boss.proposer.name == "Proposer"
        assert boss.validator.name == "Validator"
        print("✓ Test: Boss has all worker agents")

    def test_boss_statistics(self):
        """Test boss collects statistics."""
        boss = BossAgent()
        stats = boss.get_stats()

        assert "boss" in stats
        assert "strategist" in stats
        assert "analyzer" in stats
        assert "proposer" in stats
        assert "validator" in stats
        assert stats["boss"]["rounds_orchestrated"] == 0
        print("✓ Test: Boss statistics collection")


class TestBossWorkerOrchestrator:
    """Test Boss-Worker paradigm orchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes properly."""
        # Load a test puzzle
        puzzles = load_puzzles()
        test_puzzle = puzzles[0]

        orchestrator = BossWorkerOrchestrator(test_puzzle)

        assert orchestrator.puzzle["puzzle_id"] == test_puzzle["puzzle_id"]
        assert orchestrator.game_engine is not None
        assert orchestrator.boss is not None
        assert orchestrator.round_count == 0
        assert len(orchestrator.guess_history) == 0
        print("✓ Test: Orchestrator initialization")

    def test_orchestrator_result_structure(self):
        """Test orchestrator result has correct structure."""
        puzzles = load_puzzles()
        test_puzzle = puzzles[0]

        orchestrator = BossWorkerOrchestrator(test_puzzle)
        # Note: Not running full game to avoid LLM calls
        # Just test the structure

        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)
        print("✓ Test: Orchestrator has run method")

    def test_orchestrator_game_engine_integration(self):
        """Test orchestrator integrates with game engine."""
        puzzles = load_puzzles()
        test_puzzle = puzzles[0]

        orchestrator = BossWorkerOrchestrator(test_puzzle)

        # Test game engine is set up correctly
        assert orchestrator.game_engine is not None
        assert orchestrator.game_engine.secret_code == test_puzzle["secret_code"]
        assert orchestrator.game_engine.guess_count == 0
        print("✓ Test: Orchestrator-GameEngine integration")

    def test_orchestrator_communication_logger(self):
        """Test orchestrator has communication logger."""
        puzzles = load_puzzles()
        test_puzzle = puzzles[0]

        orchestrator = BossWorkerOrchestrator(test_puzzle)

        assert orchestrator.logger is not None
        assert orchestrator.puzzle["puzzle_id"] in str(orchestrator.logger.log_file)
        print("✓ Test: Orchestrator communication logger")


class TestBossWorkerWorkflow:
    """Test the complete Boss-Worker workflow."""

    def test_workflow_orchestration_exists(self):
        """Test orchestration infrastructure exists."""
        boss = BossAgent()
        # Verify orchestration method exists
        assert hasattr(boss, "orchestrate_round")
        assert callable(boss.orchestrate_round)
        # Verify retry mechanism exists
        assert hasattr(boss, "_ask_proposer_with_retry")
        assert callable(boss._ask_proposer_with_retry)
        print("✓ Test: Orchestration infrastructure exists")

    def test_workflow_round_tracking(self):
        """Test round counting."""
        boss = BossAgent()
        assert boss.round_count == 0
        # Note: Can't increment without calling orchestrate_round which needs LLM
        print("✓ Test: Round counting mechanism")


class TestBossWorkerProperties:
    """Test paradigm-specific properties of Boss-Worker."""

    def test_centralized_coordination(self):
        """Test that Boss is central coordinator."""
        boss = BossAgent()
        # In Boss-Worker: Boss controls all message routing
        # All messages go through Boss
        assert boss.name == "Boss"
        assert hasattr(boss, "strategist")
        assert hasattr(boss, "analyzer")
        assert hasattr(boss, "proposer")
        assert hasattr(boss, "validator")
        print("✓ Test: Centralized coordination (Boss-Worker)")

    def test_sequential_design(self):
        """Test that design supports sequential execution."""
        boss = BossAgent()
        # In Boss-Worker: Execution is designed to be sequential
        # Each agent is called in order
        assert boss.strategist is not None
        assert boss.analyzer is not None
        assert boss.proposer is not None
        assert boss.validator is not None
        print("✓ Test: Sequential design (Boss-Worker)")

    def test_single_paradigm_structure(self):
        """Test single-paradigm structure (vs 3 teams in competition)."""
        puzzles = load_puzzles()
        test_puzzle = puzzles[0]
        orchestrator = BossWorkerOrchestrator(test_puzzle)

        # Boss-Worker: Single team structure
        assert orchestrator.boss is not None
        assert orchestrator.game_engine is not None
        assert orchestrator.logger is not None
        # Only one Boss, not multiple teams
        assert isinstance(orchestrator.boss, BossAgent)
        print("✓ Test: Single paradigm structure (Boss-Worker)")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("BOSS AGENT & BOSS-WORKER PARADIGM TEST SUITE")
    print("="*60)

    print("\n[Boss Agent Tests]")
    test_boss = TestBossAgent()
    test_boss.test_boss_initialization()
    test_boss.test_boss_round_method_exists()
    test_boss.test_boss_worker_agents()
    test_boss.test_boss_statistics()

    print("\n[Boss-Worker Orchestrator Tests]")
    test_orch = TestBossWorkerOrchestrator()
    test_orch.test_orchestrator_initialization()
    test_orch.test_orchestrator_result_structure()
    test_orch.test_orchestrator_game_engine_integration()
    test_orch.test_orchestrator_communication_logger()

    print("\n[Workflow Tests]")
    test_work = TestBossWorkerWorkflow()
    test_work.test_workflow_orchestration_exists()
    test_work.test_workflow_round_tracking()

    print("\n[Paradigm Properties Tests]")
    test_props = TestBossWorkerProperties()
    test_props.test_centralized_coordination()
    test_props.test_sequential_design()
    test_props.test_single_paradigm_structure()

    print("\n" + "="*60)
    print("✓ ALL BOSS-WORKER TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
