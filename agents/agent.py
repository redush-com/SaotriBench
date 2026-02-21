"""LLM-based coding agent for Saotri Bench."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .config import ModelConfig
from .llm_client import OpenRouterClient


SYSTEM_PROMPT = """\
You are a Python coding agent solving programming tasks iteratively.
You receive a problem and must write a Python function. After each attempt you get evaluation feedback with violation details.

CRITICAL OUTPUT RULES:
1. Output EXACTLY ONE ```python block containing the COMPLETE function. Nothing else.
2. No test code, no print statements, no example usage, no explanations outside the code block.
3. Do NOT use imports unless explicitly listed as allowed.
4. The function signature MUST match exactly what is specified.
5. VERIFY your code has no syntax errors (matching brackets, quotes, colons) before outputting.
6. Never output a partial function or empty code block.

ITERATION STRATEGY:
1. When fixing violations, do NOT break previously passing scopes. Keep working logic intact.
2. Each scope name in violations is a hint about what the test checks. Reason about its meaning.
3. On phase transitions: new rules are ADDED to existing ones. Your solution must satisfy ALL rules from ALL phases so far.
4. If you get a syntax error, carefully check brackets, quotes, colons, and indentation. You may fix just the syntax or rewrite if needed — but ensure the output is valid Python.
5. Before outputting, mentally trace through your code to check for regressions on earlier scopes.
"""


@dataclass
class AgentAttempt:
    """Record of a single agent attempt."""

    phase_id: int
    attempt_id: int
    code: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0


class CodingAgent:
    """LLM agent that reads workspace files and generates solutions."""

    def __init__(
        self,
        model: ModelConfig,
        client: OpenRouterClient,
        workspace_dir: Path,
    ):
        self.model = model
        self.client = client
        self.workspace_dir = Path(workspace_dir)
        self.attempts: list[AgentAttempt] = []
        self.conversation_history: list[dict[str, str]] = []

    def _read_file(self, filename: str) -> str:
        """Read a workspace file, return empty string if missing."""
        path = self.workspace_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _read_json(self, filename: str) -> dict[str, Any]:
        """Read a JSON workspace file."""
        content = self._read_file(filename)
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _summarize_middle_turns(messages: list[dict[str, str]]) -> str:
        """Compress discarded middle turns into a concise summary.

        Extracts key signals (violations, scopes, errors) from user feedback
        messages so the model retains awareness of past failures without the
        full conversation weight.
        """
        if not messages:
            return ""

        violations_seen: dict[str, set[str]] = {}  # rule_id -> {scopes}
        errors_seen: list[str] = []
        phases_seen: set[str] = set()
        attempt_count = 0

        for msg in messages:
            if msg["role"] != "user":
                continue
            content = msg["content"]
            attempt_count += 1

            # Extract phase references
            for line in content.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("## Current Phase:"):
                    phases_seen.add(line_stripped.split(":", 1)[1].strip())
                elif line_stripped.startswith("- Rule '"):
                    # Parse: "- Rule 'rule_id' failed on scope 'scope' (N times)"
                    parts = line_stripped.split("'")
                    if len(parts) >= 4:
                        rule_id = parts[1]
                        scope = parts[3]
                        violations_seen.setdefault(rule_id, set()).add(scope)
                elif line_stripped.startswith("## ERROR:"):
                    errors_seen.append(line_stripped.replace("## ERROR: ", ""))

        if not violations_seen and not errors_seen:
            return ""

        summary_parts = [
            f"[Context from {attempt_count} earlier attempts, "
            f"phases {', '.join(sorted(phases_seen)) if phases_seen else 'unknown'}]"
        ]

        if violations_seen:
            summary_parts.append("Previously encountered violations:")
            for rule_id, scopes in violations_seen.items():
                summary_parts.append(f"  - Rule '{rule_id}' on scopes: {', '.join(sorted(scopes))}")

        if errors_seen:
            summary_parts.append("Errors encountered: " + "; ".join(errors_seen[:5]))

        return "\n".join(summary_parts)

    def _build_initial_prompt(self) -> str:
        """Build the initial prompt from workspace files."""
        problem = self._read_file("problem.md")
        task_info = self._read_json("task.json")
        phase_info = self._read_json("phase.json")

        interface = task_info.get("interface", {})
        signature = interface.get("signature", "")
        allowed_imports = interface.get("allowed_imports", [])

        rules = phase_info.get("rules", [])
        rules_text = "\n".join(
            f"  - {r['id']}: {r['description']}" for r in rules
        )

        prompt = f"""## Problem
{problem}

## Function Signature
{signature}

## Allowed Imports
{', '.join(allowed_imports) if allowed_imports else 'None'}

## Current Phase: {phase_info.get('phase_id', 0)}
## Rules to satisfy:
{rules_text}

Write the complete function implementation. Output ONLY the code in a ```python block.
"""
        return prompt

    def _build_refinement_prompt(self, feedback: dict[str, Any]) -> str:
        """Build a refinement prompt from feedback."""
        status = feedback.get("status", "unknown")
        status_reason = feedback.get("status_reason", "")
        violations = feedback.get("violations", [])
        summary = feedback.get("summary", {})
        coverage = summary.get("coverage", 0)
        error = feedback.get("error")

        # Read current phase info (may have changed due to phase transition)
        phase_info = self._read_json("phase.json")
        phase_transition = phase_info.get("phase_transition", False)
        rules = phase_info.get("rules", [])

        parts = []

        if phase_transition:
            parts.append("## PHASE TRANSITION — New rules have been added!")
            implicit_eval = phase_info.get("implicit_evaluation")
            if implicit_eval:
                impl_violations = implicit_eval.get("violations", [])
                if impl_violations:
                    parts.append("Your current solution has these issues in the new phase:")
                    for v in impl_violations:
                        parts.append(f"  - Rule '{v['rule_id']}' failed on scope '{v['scope']}' ({v['count']} times)")

        parts.append(f"\n## Evaluation Result: {status}")
        parts.append(f"Reason: {status_reason}")
        parts.append(f"Coverage: {coverage:.1%}")

        if error:
            parts.append(f"\n## ERROR: {error.get('type', 'Unknown')}")
            parts.append(f"Message: {error.get('message', '')}")
            if "syntax" in error.get("type", "").lower() or "syntax" in error.get("message", "").lower():
                parts.append(
                    "NOTE: This is a syntax error. Double-check brackets, quotes, colons, "
                    "and indentation. If the overall approach is sound, a minimal fix is enough. "
                    "If you think the approach itself needs changing, you may rewrite — "
                    "but make sure the output is syntactically valid."
                )

        if violations:
            parts.append("\n## Violations:")
            for v in violations:
                parts.append(f"  - Rule '{v['rule_id']}' failed on scope '{v['scope']}' ({v['count']} times)")

        rules_text = "\n".join(f"  - {r['id']}: {r['description']}" for r in rules)
        parts.append(f"\n## Current rules to satisfy:\n{rules_text}")

        # Include current solution so model always sees what it's fixing
        current_code = self._read_file("solution.py")
        if current_code:
            parts.append(f"\n## Your current solution:\n```python\n{current_code}\n```")

        parts.append(
            "\nAnalyze the violations carefully. Think about what each scope name implies. "
            "Fix ALL issues while keeping previously passing scopes intact. "
            "Output the COMPLETE updated function in a ```python block."
        )

        return "\n".join(parts)

    def _extract_and_log(self, raw_content: str) -> str:
        """Extract code from LLM response, logging diagnostics on empty result."""
        code = OpenRouterClient._extract_code(raw_content)
        if not code.strip():
            preview = raw_content[:500] if raw_content else "<None>"
            logger.warning(
                "Code extraction returned empty. "
                "Model: %s | Raw response length: %d | Preview: %s",
                self.model.label,
                len(raw_content) if raw_content else 0,
                preview,
            )
            print(f"  [warn] empty code extracted from {self.model.label} "
                  f"(raw response: {len(raw_content) if raw_content else 0} chars)")
        return code

    def generate_solution(self) -> str:
        """Generate initial solution.

        Returns:
            Generated Python code
        """
        user_prompt = self._build_initial_prompt()

        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        start = time.time()
        response = self.client.chat(self.model, self.conversation_history)
        duration = time.time() - start

        code = self._extract_and_log(response.content)

        # Track assistant response in conversation
        self.conversation_history.append(
            {"role": "assistant", "content": response.content}
        )

        attempt = AgentAttempt(
            phase_id=0,
            attempt_id=len(self.attempts),
            code=code,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            duration_seconds=duration,
        )
        self.attempts.append(attempt)

        return code

    def refine_solution(self, feedback: dict[str, Any]) -> str:
        """Refine solution based on feedback.

        Args:
            feedback: Parsed feedback.json content

        Returns:
            Updated Python code
        """
        user_prompt = self._build_refinement_prompt(feedback)

        # Keep conversation context but limit to avoid token overflow.
        # Strategy: keep system + first exchange + a compact summary of
        # discarded middle turns + the most recent turns.
        max_history = 20
        recent_keep = 6  # last 3 user/assistant pairs
        prefix_keep = 3  # system + first user + first assistant
        if len(self.conversation_history) > max_history:
            middle = self.conversation_history[prefix_keep:-recent_keep]
            summary = self._summarize_middle_turns(middle)
            self.conversation_history = (
                self.conversation_history[:prefix_keep]
                + ([{"role": "user", "content": summary},
                    {"role": "assistant", "content": "Understood, I'll keep this context in mind."}]
                   if summary else [])
                + self.conversation_history[-recent_keep:]
            )

        self.conversation_history.append({"role": "user", "content": user_prompt})

        start = time.time()
        response = self.client.chat(self.model, self.conversation_history)
        duration = time.time() - start

        code = self._extract_and_log(response.content)

        self.conversation_history.append(
            {"role": "assistant", "content": response.content}
        )

        phase_id = feedback.get("phase_id", 0)
        attempt = AgentAttempt(
            phase_id=phase_id,
            attempt_id=len(self.attempts),
            code=code,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            duration_seconds=duration,
        )
        self.attempts.append(attempt)

        return code

    def write_solution(self, code: str) -> None:
        """Write code to the solution file in workspace."""
        solution_path = self.workspace_dir / "solution.py"
        solution_path.write_text(code, encoding="utf-8")

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage across all attempts."""
        prompt = sum(a.prompt_tokens for a in self.attempts)
        completion = sum(a.completion_tokens for a in self.attempts)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        }
