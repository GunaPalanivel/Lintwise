"""Abstract base class for all review agents."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod

from lintwise.core.exceptions import LLMResponseParseError
from lintwise.core.logging import get_logger
from lintwise.core.models import (
    AgentMetrics,
    FileChange,
    PRDiff,
    ReviewComment,
)
from lintwise.llm.base import LLMProvider

logger = get_logger(__name__)


class ReviewAgent(ABC):
    """Abstract base for specialized code review agents.

    Each agent:
    1. Builds a prompt from the file change + PR context
    2. Sends it to the LLM
    3. Parses the structured JSON response into ReviewComment objects
    """

    name: str = "base_agent"
    category: str = "logic"  # Must match ReviewCategory values

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @abstractmethod
    def build_prompt(self, file_change: FileChange, context: PRDiff) -> str:
        """Build the analysis prompt for this agent's specialty.

        Args:
            file_change: The file diff to analyze.
            context: Full PR context (title, description, other files).

        Returns:
            Complete prompt string ready for the LLM.
        """
        ...

    def get_system_prompt(self) -> str:
        """System message defining the agent's role and output format."""
        return (
            f"You are an expert code reviewer specializing in {self.category} analysis. "
            "Analyze the provided code diff and identify issues.\n\n"
            "Respond ONLY with a JSON array of findings. Each finding must have:\n"
            '- "title": Short descriptive title\n'
            '- "body": Detailed explanation in Markdown\n'
            '- "line": Line number in the new file (null if general)\n'
            '- "severity": One of "critical", "warning", "suggestion", "nitpick"\n'
            '- "confidence": Float 0.0-1.0\n'
            '- "suggestion": Optional code fix suggestion (null if none)\n\n'
            "Rules:\n"
            "- ONLY flag issues visible in the diff, not imagined problems\n"
            "- Be specific about WHY something is an issue\n"
            "- Provide actionable suggestions when possible\n"
            "- If no issues found, return an empty array: []\n"
        )

    async def analyze(
        self, file_change: FileChange, context: PRDiff
    ) -> tuple[list[ReviewComment], AgentMetrics]:
        """Analyze a file change and return findings + metrics.

        This is the main entry point. It:
        1. Builds the prompt
        2. Calls the LLM
        3. Parses the response
        4. Returns structured comments + telemetry
        """
        start_ms = time.perf_counter_ns() // 1_000_000

        try:
            prompt = self.build_prompt(file_change, context)
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            comments = self._parse_response(response.content, file_change.filename)
            duration_ms = (time.perf_counter_ns() // 1_000_000) - start_ms

            metrics = AgentMetrics(
                agent_name=self.name,
                duration_ms=duration_ms,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                files_analyzed=1,
                comments_produced=len(comments),
            )

            logger.info(
                "agent_analysis_complete",
                agent=self.name,
                file=file_change.filename,
                comments=len(comments),
                duration_ms=duration_ms,
            )

            return comments, metrics

        except Exception as e:
            duration_ms = (time.perf_counter_ns() // 1_000_000) - start_ms
            logger.error("agent_analysis_failed", agent=self.name, error=str(e))

            metrics = AgentMetrics(
                agent_name=self.name,
                duration_ms=duration_ms,
                files_analyzed=1,
                error=str(e),
            )
            return [], metrics

    def _parse_response(self, content: str, filename: str) -> list[ReviewComment]:
        """Parse LLM JSON response into ReviewComment objects."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseParseError(f"Invalid JSON from {self.name}: {e}") from e

        # Handle both {"findings": [...]} and bare [...]
        if isinstance(data, dict):
            findings = data.get("findings", data.get("issues", data.get("comments", [])))
        elif isinstance(data, list):
            findings = data
        else:
            return []

        comments: list[ReviewComment] = []
        for item in findings:
            if not isinstance(item, dict):
                continue
            try:
                comments.append(
                    ReviewComment(
                        file=filename,
                        line=item.get("line"),
                        severity=item.get("severity", "suggestion"),
                        category=self.category,
                        title=item.get("title", "Untitled finding"),
                        body=item.get("body", ""),
                        suggestion=item.get("suggestion"),
                        confidence=float(item.get("confidence", 0.7)),
                        agent_name=self.name,
                    )
                )
            except Exception as e:
                logger.warning("skipping_malformed_finding", agent=self.name, error=str(e))
                continue

        return comments
