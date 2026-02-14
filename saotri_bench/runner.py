"""Main runner for Saotri Bench tasks."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .evaluator import BaseEvaluator
from .loader import load_evaluator, load_problem, load_task, load_tests
from .metrics import MetricsCollector
from .models import (
    Delta,
    ErrorInfo,
    Feedback,
    InitialTaskMessage,
    MetricsReport,
    Phase,
    PhaseMessage,
    Status,
    Summary,
    TaskConfig,
    TestCase,
    Violation,
)
from .sandbox import (
    ExecutionError,
    ImportViolationError,
    SandboxError,
    TimeoutError,
    execute_code,
)


class Runner:
    """Main Saotri Bench runner."""

    def __init__(
        self,
        task_dir: Path,
        workspace_dir: Path,
        agent_id: str = "unknown",
        poll_interval: float = 1.0,
    ):
        """Initialize the runner.

        Args:
            task_dir: Path to the task directory
            workspace_dir: Path to the workspace directory for file-based communication
            agent_id: Identifier for the agent being tested
            poll_interval: Interval in seconds to poll for solution changes
        """
        self.task_dir = Path(task_dir)
        self.workspace_dir = Path(workspace_dir)
        self.agent_id = agent_id
        self.poll_interval = poll_interval

        # Load task components
        self.task_config: TaskConfig = load_task(self.task_dir)
        self.problem: str = load_problem(self.task_dir)
        self.evaluator: BaseEvaluator = load_evaluator(self.task_dir)
        self.test_cases: list[TestCase] = load_tests(self.task_dir)

        # State
        self.current_phase_idx: int = 0
        self.total_attempts: int = 0
        self.phase_attempts: int = 0
        self.previous_feedback: Feedback | None = None
        self.previous_violations: set[str] = set()

        # Metrics
        self.metrics = MetricsCollector(self.task_config.id, self.agent_id)

        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_phase(self) -> Phase:
        """Get the current phase."""
        return self.task_config.phases[self.current_phase_idx]

    @property
    def solution_file(self) -> Path:
        """Path to the solution file in workspace."""
        return self.workspace_dir / "solution.py"

    @property
    def feedback_file(self) -> Path:
        """Path to the feedback file in workspace."""
        return self.workspace_dir / "feedback.json"

    @property
    def task_file(self) -> Path:
        """Path to the task info file in workspace."""
        return self.workspace_dir / "task.json"

    @property
    def phase_file(self) -> Path:
        """Path to the phase info file in workspace."""
        return self.workspace_dir / "phase.json"

    def setup_workspace(self) -> None:
        """Set up the workspace with initial files."""
        # Write problem.md
        problem_file = self.workspace_dir / "problem.md"
        problem_file.write_text(self.problem, encoding="utf-8")

        # Write initial task info
        initial_message = InitialTaskMessage(
            task_id=self.task_config.id,
            problem=self.problem,
            interface=self.task_config.interface,
            limits={
                "total_phases": len(self.task_config.phases),
                "max_attempts_per_phase": self.task_config.limits.max_attempts_per_phase,
                "max_total_attempts": self.task_config.limits.max_total_attempts,
            },
        )
        self.task_file.write_text(
            json.dumps(initial_message.to_dict(), indent=2), encoding="utf-8"
        )

        # Write initial phase info
        self._write_phase_info(phase_transition=False)

        # Create empty solution file if it doesn't exist
        if not self.solution_file.exists():
            self.solution_file.write_text("", encoding="utf-8")

    def _write_phase_info(
        self,
        phase_transition: bool,
        implicit_feedback: dict[str, Any] | None = None,
    ) -> None:
        """Write current phase information to workspace."""
        phase_message = PhaseMessage(
            task_id=self.task_config.id,
            phase_id=self.current_phase.id,
            phase_transition=phase_transition,
            rules=[
                {"id": rule.id, "description": rule.description}
                for rule in self.current_phase.rules
            ],
            previous_feedback=(
                self.previous_feedback.to_dict() if self.previous_feedback else None
            ),
            implicit_evaluation=implicit_feedback,
        )
        self.phase_file.write_text(
            json.dumps(phase_message.to_dict(), indent=2), encoding="utf-8"
        )

    def _write_feedback(self, feedback: Feedback) -> None:
        """Write feedback to workspace."""
        self.feedback_file.write_text(
            json.dumps(feedback.to_dict(), indent=2), encoding="utf-8"
        )

    def _read_solution(self) -> str:
        """Read the current solution from workspace."""
        if not self.solution_file.exists():
            return ""
        return self.solution_file.read_text(encoding="utf-8")

    def _get_solution_mtime(self) -> float:
        """Get modification time of solution file."""
        if not self.solution_file.exists():
            return 0.0
        return self.solution_file.stat().st_mtime

    def _evaluate_solution(self, code: str) -> Feedback:
        """Evaluate a solution and return feedback."""
        phase = self.current_phase
        attempt_id = self.total_attempts

        # Try to execute the code
        try:
            solution_fn = execute_code(
                code,
                self.task_config.interface.function_name,
                self.task_config.interface.allowed_imports,
                self.task_config.execution.timeout_seconds,
            )
        except ImportViolationError as e:
            return self._create_error_feedback(
                attempt_id, "ImportViolationError", str(e)
            )
        except ExecutionError as e:
            return self._create_error_feedback(attempt_id, "ExecutionError", str(e))
        except SandboxError as e:
            return self._create_error_feedback(attempt_id, "SandboxError", str(e))

        # Run evaluation
        try:
            violations, coverage = self.evaluator.evaluate(
                solution_fn, self.test_cases, phase
            )
        except Exception as e:
            return self._create_error_feedback(
                attempt_id, type(e).__name__, str(e), phase="evaluation"
            )

        # Determine status
        if not violations:
            status = Status.VALID
            status_reason = "All rules pass"
        else:
            # Check if any critical failures
            status = Status.PARTIALLY_VALID
            failed_rules = set(v.rule_id for v in violations)
            status_reason = f"Fails checks: {', '.join(sorted(failed_rules))}"

        # Get summary
        total, passed, failed = self.evaluator.get_rules_summary(violations, phase)
        summary = Summary(
            rules_total=total,
            rules_passed=passed,
            rules_failed=failed,
            coverage=coverage,
        )

        # Calculate delta
        delta = self._calculate_delta(violations, coverage)

        return Feedback(
            phase_id=phase.id,
            attempt_id=attempt_id,
            status=status,
            status_reason=status_reason,
            violations=violations,
            summary=summary,
            delta=delta,
        )

    def _create_error_feedback(
        self,
        attempt_id: int,
        error_type: str,
        error_message: str,
        phase: str = "execution",
    ) -> Feedback:
        """Create feedback for an error condition."""
        current_phase = self.current_phase
        return Feedback(
            phase_id=current_phase.id,
            attempt_id=attempt_id,
            status=Status.ERROR,
            status_reason=f"Runtime error: {error_message}",
            violations=[],
            summary=Summary(
                rules_total=len(current_phase.rules),
                rules_passed=0,
                rules_failed=0,
                coverage=0.0,
            ),
            delta=None,
            error=ErrorInfo(type=error_type, message=error_message, phase=phase),
        )

    def _calculate_delta(
        self, violations: list[Violation], coverage: float
    ) -> Delta | None:
        """Calculate delta from previous attempt."""
        if self.previous_feedback is None:
            return None

        current_failures = set(v.rule_id for v in violations)
        new_failures = list(current_failures - self.previous_violations)
        fixed_failures = list(self.previous_violations - current_failures)
        coverage_change = coverage - self.previous_feedback.summary.coverage

        return Delta(
            coverage_change=coverage_change,
            new_failures=new_failures,
            fixed_failures=fixed_failures,
        )

    def _advance_phase(self) -> bool:
        """Advance to the next phase if possible.

        Returns:
            True if advanced, False if no more phases
        """
        if self.current_phase_idx >= len(self.task_config.phases) - 1:
            return False

        self.current_phase_idx += 1
        self.phase_attempts = 0
        return True

    def run_single_attempt(self) -> Feedback:
        """Run a single evaluation attempt.

        Returns:
            Feedback from the evaluation
        """
        code = self._read_solution()

        start_time = time.time()

        if not code.strip():
            feedback = self._create_error_feedback(
                self.total_attempts, "EmptyCode", "Solution file is empty"
            )
        else:
            feedback = self._evaluate_solution(code)

        duration = time.time() - start_time

        # Update state (always increment, even for empty solutions,
        # so max-attempts safeguard can trigger and prevent infinite loops)
        self.total_attempts += 1
        self.phase_attempts += 1
        self.previous_feedback = feedback
        self.previous_violations = set(v.rule_id for v in feedback.violations)

        # Record metrics
        self.metrics.record_attempt(
            phase_id=self.current_phase.id,
            feedback=feedback,
            duration=duration,
        )

        # Write feedback
        self._write_feedback(feedback)

        return feedback

    def run_implicit_evaluation(self) -> Feedback:
        """Run implicit evaluation for phase transition (doesn't count as attempt)."""
        code = self._read_solution()

        if not code.strip():
            return self._create_error_feedback(
                self.total_attempts, "EmptyCode", "Solution file is empty"
            )

        return self._evaluate_solution(code)

    def run_interactive(self) -> MetricsReport:
        """Run the task interactively, waiting for solution updates.

        Returns:
            MetricsReport after task completion
        """
        self.setup_workspace()

        print(f"Starting task: {self.task_config.name}")
        print(f"Workspace: {self.workspace_dir}")
        print(f"Total phases: {len(self.task_config.phases)}")
        print(f"Waiting for solution in: {self.solution_file}")
        print(f"Type 'q' + Enter or press Ctrl+C to quit")
        print()

        # Start from current mtime so we don't evaluate the empty initial file
        last_mtime = self._get_solution_mtime()

        # Background thread to listen for 'q' on stdin
        quit_event = threading.Event()

        def _stdin_listener() -> None:
            try:
                for line in sys.stdin:
                    if line.strip().lower() == "q":
                        quit_event.set()
                        return
            except (EOFError, OSError):
                pass

        stdin_thread = threading.Thread(target=_stdin_listener, daemon=True)
        stdin_thread.start()

        try:
            while True:
                # Check for quit from stdin
                if quit_event.is_set():
                    print("\nQuit requested. Stopping session.")
                    break

                # Check limits
                if self.total_attempts >= self.task_config.limits.max_total_attempts:
                    print("Max total attempts reached. Task failed.")
                    break

                if (
                    self.phase_attempts
                    >= self.task_config.limits.max_attempts_per_phase
                ):
                    print(
                        f"Max attempts for phase {self.current_phase.id} reached. Task failed."
                    )
                    break

                # Wait for solution update
                current_mtime = self._get_solution_mtime()
                if current_mtime <= last_mtime:
                    time.sleep(self.poll_interval)
                    continue

                last_mtime = current_mtime

                # Run evaluation
                print(
                    f"Phase {self.current_phase.id}, "
                    f"Attempt {self.phase_attempts + 1}..."
                )

                feedback = self.run_single_attempt()

                print(f"  Status: {feedback.status.value}")
                print(f"  Coverage: {feedback.summary.coverage:.1%}")

                if feedback.violations:
                    print(f"  Violations: {len(feedback.violations)}")
                    for v in feedback.violations:
                        print(f"    - {v.rule_id} ({v.scope}): {v.count}")

                # Check if phase is complete
                if feedback.status == Status.VALID:
                    print(f"Phase {self.current_phase.id} completed!")
                    self.metrics.complete_phase(self.current_phase.id)

                    # Try to advance to next phase
                    if self._advance_phase():
                        print(f"Advancing to phase {self.current_phase.id}...")

                        # Run implicit evaluation
                        implicit_feedback = self.run_implicit_evaluation()
                        self._write_phase_info(
                            phase_transition=True,
                            implicit_feedback=implicit_feedback.to_dict(),
                        )

                        print(
                            f"  Implicit evaluation: {implicit_feedback.status.value}"
                        )
                        print(
                            f"  Coverage: {implicit_feedback.summary.coverage:.1%}"
                        )
                    else:
                        print("All phases completed! Task successful.")
                        break

                print()

        except KeyboardInterrupt:
            print("\n\nSession interrupted (Ctrl+C).")

        return self.metrics.generate_report()

    def run_single_pass(self) -> Feedback:
        """Run a single evaluation pass (for non-interactive use).

        Returns:
            Feedback from the evaluation
        """
        self.setup_workspace()
        return self.run_single_attempt()
