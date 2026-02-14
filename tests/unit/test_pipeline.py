"""Comprehensive tests for lintwise.orchestrator.pipeline."""

from __future__ import annotations

import asyncio
import json

import pytest

from lintwise.agents.base import ReviewAgent
from lintwise.core.models import (
    FileChange,
    FileStatus,
    PRDiff,
    ReviewCategory,
    ReviewComment,
    RiskScore,
    Severity,
)
from lintwise.llm.base import LLMProvider, LLMResponse
from lintwise.orchestrator.pipeline import run_review


# ── Mock LLM ────────────────────────────────────────────────────────────────


class MockLLM(LLMProvider):
    def __init__(self, findings=None, delay: float = 0.0):
        self._findings = findings or []
        self._delay = delay

    async def complete(self, messages, **kwargs) -> LLMResponse:
        if self._delay:
            await asyncio.sleep(self._delay)
        return LLMResponse(
            content=json.dumps({"findings": self._findings}),
            prompt_tokens=50,
            completion_tokens=25,
        )

    async def count_tokens(self, text: str) -> int:
        return len(text.split())

    async def close(self) -> None:
        pass


class SlowMockLLM(LLMProvider):
    """LLM that takes too long — for timeout testing."""

    async def complete(self, messages, **kwargs) -> LLMResponse:
        await asyncio.sleep(100)  # Way longer than any timeout
        return LLMResponse(content="[]")

    async def count_tokens(self, text: str) -> int:
        return 0

    async def close(self) -> None:
        pass


# ── Sample Data ─────────────────────────────────────────────────────────────


def _pr_diff(n_files: int = 1) -> PRDiff:
    files = [
        FileChange(
            filename=f"file_{i}.py",
            status=FileStatus.MODIFIED,
            patch=f"@@ -1,3 +1,4 @@\n+new_line_{i}\n",
            additions=1,
            language="python",
        )
        for i in range(n_files)
    ]
    return PRDiff(
        repo_owner="org",
        repo_name="repo",
        pr_number=1,
        title="Test PR",
        files=files,
    )


SAMPLE_FINDINGS = [
    {"title": "Issue", "body": "Desc", "severity": "warning", "confidence": 0.8, "line": 2},
]


# ── Pipeline Tests ──────────────────────────────────────────────────────────


class TestRunReview:
    @pytest.mark.asyncio
    async def test_basic_review(self):
        llm = MockLLM(findings=SAMPLE_FINDINGS)
        result = await run_review(_pr_diff(1), llm)

        assert result.pr_diff.pr_number == 1
        assert len(result.comments) > 0
        assert result.risk_score in list(RiskScore)
        assert result.total_duration_ms >= 0
        assert len(result.agent_metrics) > 0

    @pytest.mark.asyncio
    async def test_multiple_files(self):
        llm = MockLLM(findings=SAMPLE_FINDINGS)
        result = await run_review(_pr_diff(3), llm)

        # 3 files × 4 agents = 12 tasks, each producing 1 finding
        assert len(result.agent_metrics) == 12
        # After dedup, results may vary
        assert len(result.comments) >= 1

    @pytest.mark.asyncio
    async def test_empty_pr(self):
        llm = MockLLM()
        pr = PRDiff(repo_owner="o", repo_name="r", pr_number=1, files=[])
        result = await run_review(pr, llm)

        assert result.comments == []
        assert result.risk_score == RiskScore.LOW
        assert result.agent_metrics == []

    @pytest.mark.asyncio
    async def test_no_findings(self):
        llm = MockLLM(findings=[])
        result = await run_review(_pr_diff(1), llm)

        assert result.comments == []
        assert result.risk_score == RiskScore.LOW

    @pytest.mark.asyncio
    async def test_custom_agents(self):
        """Only run specific agents."""
        from lintwise.agents.logic_agent import LogicAgent

        llm = MockLLM(findings=SAMPLE_FINDINGS)
        agent = LogicAgent(llm)
        result = await run_review(_pr_diff(1), llm, agents=[agent])

        assert len(result.agent_metrics) == 1
        assert result.agent_metrics[0].agent_name == "logic_agent"

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Pipeline should respect the max_concurrent parameter."""
        llm = MockLLM(findings=SAMPLE_FINDINGS, delay=0.01)
        result = await run_review(
            _pr_diff(2), llm, max_concurrent=1, timeout_per_agent=5.0
        )
        # Should still complete even with concurrency=1
        assert len(result.agent_metrics) > 0

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Agents that timeout should produce error metrics, not crash the pipeline."""
        slow_llm = SlowMockLLM()
        result = await run_review(
            _pr_diff(1), slow_llm, timeout_per_agent=0.1
        )

        # All agents should have timed out but pipeline should complete
        assert result is not None
        errored = [m for m in result.agent_metrics if m.error]
        assert len(errored) > 0
        assert "Timeout" in errored[0].error

    @pytest.mark.asyncio
    async def test_result_has_correct_pr_ref(self):
        llm = MockLLM(findings=[])
        pr = _pr_diff(1)
        result = await run_review(pr, llm)
        assert result.pr_diff.repo_owner == "org"
        assert result.pr_diff.repo_name == "repo"
