"""Metrics collection and reporting for Saotri Bench."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import (
    Feedback,
    MetricsReport,
    OverallResult,
    PhaseResult,
    PhaseStatus,
    Status,
    TaskStatus,
)


@dataclass
class PhaseMetrics:
    """Metrics for a single phase."""

    phase_id: int
    attempts: int = 0
    final_coverage: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: PhaseStatus = PhaseStatus.IN_PROGRESS

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time


class MetricsCollector:
    """Collects metrics during task execution."""

    def __init__(self, task_id: str, agent_id: str):
        """Initialize the metrics collector.

        Args:
            task_id: ID of the task being run
            agent_id: ID of the agent being tested
        """
        self.task_id = task_id
        self.agent_id = agent_id
        self.start_time = time.time()
        self.phases: dict[int, PhaseMetrics] = {}
        self.total_attempts = 0

    def _ensure_phase(self, phase_id: int) -> PhaseMetrics:
        """Ensure phase metrics exist."""
        if phase_id not in self.phases:
            self.phases[phase_id] = PhaseMetrics(phase_id=phase_id)
        return self.phases[phase_id]

    def record_attempt(
        self,
        phase_id: int,
        feedback: Feedback,
        duration: float,
    ) -> None:
        """Record an attempt.

        Args:
            phase_id: ID of the current phase
            feedback: Feedback from the evaluation
            duration: Duration of the attempt in seconds
        """
        phase = self._ensure_phase(phase_id)
        phase.attempts += 1
        phase.final_coverage = feedback.summary.coverage
        self.total_attempts += 1

    def complete_phase(self, phase_id: int) -> None:
        """Mark a phase as completed.

        Args:
            phase_id: ID of the completed phase
        """
        phase = self._ensure_phase(phase_id)
        phase.status = PhaseStatus.VALID
        phase.end_time = time.time()
        phase.final_coverage = 1.0

    def fail_phase(self, phase_id: int) -> None:
        """Mark a phase as failed.

        Args:
            phase_id: ID of the failed phase
        """
        phase = self._ensure_phase(phase_id)
        phase.status = PhaseStatus.FAILED
        phase.end_time = time.time()

    def generate_report(self) -> MetricsReport:
        """Generate the final metrics report.

        Returns:
            Complete MetricsReport
        """
        end_time = time.time()
        total_duration = end_time - self.start_time

        # Convert phase metrics to PhaseResult
        phase_results = []
        phases_completed = 0

        for phase_id in sorted(self.phases.keys()):
            phase = self.phases[phase_id]
            phase_results.append(
                PhaseResult(
                    phase_id=phase.phase_id,
                    status=phase.status,
                    attempts=phase.attempts,
                    final_coverage=phase.final_coverage,
                    duration_seconds=phase.duration_seconds,
                )
            )
            if phase.status == PhaseStatus.VALID:
                phases_completed += 1

        # Determine overall status
        total_phases = len(self.phases)
        if phases_completed == total_phases and total_phases > 0:
            overall_status = TaskStatus.COMPLETED
        elif any(p.status == PhaseStatus.FAILED for p in self.phases.values()):
            overall_status = TaskStatus.FAILED
        else:
            overall_status = TaskStatus.IN_PROGRESS

        overall = OverallResult(
            status=overall_status,
            total_attempts=self.total_attempts,
            total_phases=total_phases,
            phases_completed=phases_completed,
            total_duration_seconds=total_duration,
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        return MetricsReport(
            task_id=self.task_id,
            agent_id=self.agent_id,
            timestamp=timestamp,
            phases=phase_results,
            overall=overall,
        )
