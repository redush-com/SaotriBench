"""Data models for Saotri Bench."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Difficulty(str, Enum):
    """Task difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class Status(str, Enum):
    """Attempt status values."""

    VALID = "valid"
    PARTIALLY_VALID = "partially_valid"
    INVALID = "invalid"
    ERROR = "error"


class PhaseStatus(str, Enum):
    """Phase completion status."""

    VALID = "valid"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class TaskStatus(str, Enum):
    """Overall task completion status."""

    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


@dataclass
class Rule:
    """A correctness constraint for a phase."""

    id: str
    description: str
    scopes: list[str] = field(default_factory=list)


@dataclass
class Phase:
    """A stage of a task with a fixed set of rules."""

    id: int
    description: str
    rules: list[Rule] = field(default_factory=list)


@dataclass
class Interface:
    """Function interface specification."""

    function_name: str
    signature: str
    allowed_imports: list[str] = field(default_factory=list)


@dataclass
class Execution:
    """Execution configuration."""

    timeout_seconds: int = 30


@dataclass
class Limits:
    """Attempt limits for a task."""

    max_attempts_per_phase: int = 10
    max_total_attempts: int = 50


@dataclass
class TaskConfig:
    """Complete task configuration from task.yaml."""

    id: str
    name: str
    description: str
    difficulty: Difficulty
    interface: Interface
    phases: list[Phase]
    limits: Limits = field(default_factory=Limits)
    execution: Execution = field(default_factory=Execution)


@dataclass
class TestCase:
    """A single test case for evaluation."""

    input: Any
    expected: Any
    phase: int
    tags: list[str] = field(default_factory=list)


@dataclass
class RuleResult:
    """Result of checking a single rule on a single test case."""

    passed: bool
    scope: str | None = None

    @staticmethod
    def success() -> RuleResult:
        """Create a passed result."""
        return RuleResult(passed=True)

    @staticmethod
    def failed(scope: str) -> RuleResult:
        """Create a failed result with scope."""
        return RuleResult(passed=False, scope=scope)


@dataclass
class Violation:
    """A rule violation with count."""

    rule_id: str
    scope: str
    count: int


@dataclass
class Summary:
    """Summary statistics for an attempt."""

    rules_total: int
    rules_passed: int
    rules_failed: int
    coverage: float


@dataclass
class Delta:
    """Change from previous attempt."""

    coverage_change: float | None
    new_failures: list[str]
    fixed_failures: list[str]


@dataclass
class ErrorInfo:
    """Error information when code fails to execute."""

    type: str
    message: str
    phase: str = "execution"


@dataclass
class Feedback:
    """Structured feedback for an attempt."""

    phase_id: int
    attempt_id: int
    status: Status
    status_reason: str
    violations: list[Violation]
    summary: Summary
    delta: Delta | None = None
    error: ErrorInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "phase_id": self.phase_id,
            "attempt_id": self.attempt_id,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "violations": [
                {"rule_id": v.rule_id, "scope": v.scope, "count": v.count}
                for v in self.violations
            ],
            "summary": {
                "rules_total": self.summary.rules_total,
                "rules_passed": self.summary.rules_passed,
                "rules_failed": self.summary.rules_failed,
                "coverage": self.summary.coverage,
            },
        }
        if self.delta:
            result["delta"] = {
                "coverage_change": self.delta.coverage_change,
                "new_failures": self.delta.new_failures,
                "fixed_failures": self.delta.fixed_failures,
            }
        else:
            result["delta"] = None
        if self.error:
            result["error"] = {
                "type": self.error.type,
                "message": self.error.message,
                "phase": self.error.phase,
            }
        return result


@dataclass
class PhaseResult:
    """Result of completing a phase."""

    phase_id: int
    status: PhaseStatus
    attempts: int
    final_coverage: float
    duration_seconds: float


@dataclass
class OverallResult:
    """Overall task completion result."""

    status: TaskStatus
    total_attempts: int
    total_phases: int
    phases_completed: int
    total_duration_seconds: float


@dataclass
class MetricsReport:
    """Complete metrics report for a task run."""

    task_id: str
    agent_id: str
    timestamp: str
    phases: list[PhaseResult]
    overall: OverallResult

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "status": p.status.value,
                    "attempts": p.attempts,
                    "final_coverage": p.final_coverage,
                    "duration_seconds": p.duration_seconds,
                }
                for p in self.phases
            ],
            "overall": {
                "status": self.overall.status.value,
                "total_attempts": self.overall.total_attempts,
                "total_phases": self.overall.total_phases,
                "phases_completed": self.overall.phases_completed,
                "total_duration_seconds": self.overall.total_duration_seconds,
            },
        }


@dataclass
class InitialTaskMessage:
    """Initial message sent to agent at task start."""

    task_id: str
    problem: str
    interface: Interface
    limits: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "problem": self.problem,
            "interface": {
                "function_name": self.interface.function_name,
                "signature": self.interface.signature,
                "allowed_imports": self.interface.allowed_imports,
            },
            "limits": self.limits,
        }


@dataclass
class PhaseMessage:
    """Per-attempt message sent to agent."""

    task_id: str
    phase_id: int
    phase_transition: bool
    rules: list[dict[str, str]]
    previous_feedback: dict[str, Any] | None = None
    implicit_evaluation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "phase_transition": self.phase_transition,
            "rules": self.rules,
            "previous_feedback": self.previous_feedback,
        }
        if self.implicit_evaluation:
            result["implicit_evaluation"] = self.implicit_evaluation
        return result
