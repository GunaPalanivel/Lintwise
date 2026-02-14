"""Comprehensive tests for agents — base agent, specialized agents, and registry."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from lintwise.agents.base import ReviewAgent
from lintwise.agents.logic_agent import LogicAgent
from lintwise.agents.performance_agent import PerformanceAgent
from lintwise.agents.readability_agent import ReadabilityAgent
from lintwise.agents.registry import (
    AGENT_CLASSES,
    create_agents_by_name,
    create_all_agents,
    get_agent_names,
)
from lintwise.agents.security_agent import SecurityAgent
from lintwise.core.models import (
    FileChange,
    FileStatus,
    PRDiff,
    ReviewCategory,
    Severity,
)
from lintwise.llm.base import LLMProvider, LLMResponse


# ── Mock LLM Provider ──────────────────────────────────────────────────────


class MockLLM(LLMProvider):
    """Test LLM that returns a configurable response."""

    def __init__(self, findings: list[dict] | None = None, error: Exception | None = None):
        self._findings = findings or []
        self._error = error

    async def complete(self, messages, **kwargs) -> LLMResponse:
        if self._error:
            raise self._error
        content = json.dumps({"findings": self._findings})
        return LLMResponse(
            content=content,
            prompt_tokens=100,
            completion_tokens=50,
            model="mock-model",
        )

    async def count_tokens(self, text: str) -> int:
        return len(text.split())

    async def close(self) -> None:
        pass


# ── Sample Data ─────────────────────────────────────────────────────────────


SAMPLE_FILE = FileChange(
    filename="src/auth.py",
    status=FileStatus.MODIFIED,
    patch="@@ -10,5 +10,7 @@\n-    password = request.args['pw']\n+    password = request.form.get('password')\n",
    additions=1,
    deletions=1,
    language="python",
)

SAMPLE_PR = PRDiff(
    repo_owner="org",
    repo_name="repo",
    pr_number=42,
    title="Fix password handling",
    description="Safely access form data.",
    files=[SAMPLE_FILE],
)

SAMPLE_FINDINGS = [
    {
        "title": "Missing null check",
        "body": "The `password` variable might be None.",
        "line": 12,
        "severity": "warning",
        "confidence": 0.85,
        "suggestion": "if password is None:\n    raise ValueError('Password required')",
    },
    {
        "title": "Log sensitive data",
        "body": "Password is logged in debug mode.",
        "line": 15,
        "severity": "critical",
        "confidence": 0.95,
        "suggestion": None,
    },
]


# ── Base Agent ──────────────────────────────────────────────────────────────


class TestReviewAgentBase:
    @pytest.mark.asyncio
    async def test_analyze_success(self):
        llm = MockLLM(findings=SAMPLE_FINDINGS)
        agent = LogicAgent(llm)
        comments, metrics = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)

        assert len(comments) == 2
        assert comments[0].title == "Missing null check"
        assert comments[0].severity == Severity.WARNING
        assert comments[0].confidence == 0.85
        assert comments[0].agent_name == "logic_agent"
        assert comments[0].file == "src/auth.py"

        assert metrics.agent_name == "logic_agent"
        assert metrics.files_analyzed == 1
        assert metrics.comments_produced == 2
        assert metrics.prompt_tokens == 100
        assert metrics.error is None
        assert metrics.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_analyze_empty_findings(self):
        llm = MockLLM(findings=[])
        agent = LogicAgent(llm)
        comments, metrics = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)

        assert comments == []
        assert metrics.comments_produced == 0
        assert metrics.error is None

    @pytest.mark.asyncio
    async def test_analyze_llm_error(self):
        llm = MockLLM(error=Exception("API down"))
        agent = LogicAgent(llm)
        comments, metrics = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)

        assert comments == []
        assert metrics.error is not None
        assert "API down" in metrics.error

    @pytest.mark.asyncio
    async def test_parse_bare_array(self):
        """LLM returns a bare JSON array instead of {findings: [...]}."""
        mock = AsyncMock(spec=LLMProvider)
        mock.complete.return_value = LLMResponse(
            content=json.dumps([{"title": "Issue", "body": "Desc", "line": 5, "severity": "suggestion", "confidence": 0.7}]),
            prompt_tokens=50,
            completion_tokens=20,
        )
        agent = LogicAgent(mock)
        comments, _ = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)
        assert len(comments) == 1

    @pytest.mark.asyncio
    async def test_parse_malformed_item_skipped(self):
        """Malformed items in the array should be skipped, not crash."""
        llm = MockLLM(findings=[
            {"title": "Good", "body": "OK", "severity": "warning", "confidence": 0.8},
            "not a dict",  # Malformed
            {"title": "Also good", "body": "OK", "severity": "suggestion", "confidence": 0.5},
        ])
        agent = LogicAgent(llm)
        comments, _ = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)
        assert len(comments) == 2

    def test_system_prompt_content(self):
        llm = MockLLM()
        agent = LogicAgent(llm)
        prompt = agent.get_system_prompt()
        assert "logic" in prompt
        assert "JSON" in prompt
        assert "findings" in prompt.lower() or "array" in prompt.lower()


# ── Specialized Agents ──────────────────────────────────────────────────────


class TestSpecializedAgents:
    def test_logic_agent_properties(self):
        agent = LogicAgent(MockLLM())
        assert agent.name == "logic_agent"
        assert agent.category == "logic"

    def test_readability_agent_properties(self):
        agent = ReadabilityAgent(MockLLM())
        assert agent.name == "readability_agent"
        assert agent.category == "readability"

    def test_performance_agent_properties(self):
        agent = PerformanceAgent(MockLLM())
        assert agent.name == "performance_agent"
        assert agent.category == "performance"

    def test_security_agent_properties(self):
        agent = SecurityAgent(MockLLM())
        assert agent.name == "security_agent"
        assert agent.category == "security"

    def test_logic_prompt_contains_focus_areas(self):
        agent = LogicAgent(MockLLM())
        prompt = agent.build_prompt(SAMPLE_FILE, SAMPLE_PR)
        assert "null" in prompt.lower() or "dereference" in prompt.lower()
        assert SAMPLE_FILE.filename in prompt

    def test_readability_prompt_focus(self):
        agent = ReadabilityAgent(MockLLM())
        prompt = agent.build_prompt(SAMPLE_FILE, SAMPLE_PR)
        assert "readability" in prompt.lower()
        assert "naming" in prompt.lower() or "complexity" in prompt.lower()

    def test_performance_prompt_focus(self):
        agent = PerformanceAgent(MockLLM())
        prompt = agent.build_prompt(SAMPLE_FILE, SAMPLE_PR)
        assert "performance" in prompt.lower()

    def test_security_prompt_focus(self):
        agent = SecurityAgent(MockLLM())
        prompt = agent.build_prompt(SAMPLE_FILE, SAMPLE_PR)
        assert "security" in prompt.lower() or "vulnerabilit" in prompt.lower()

    def test_prompts_include_pr_context(self):
        """All agents should include PR title and file info in their prompts."""
        agents = [
            LogicAgent(MockLLM()),
            ReadabilityAgent(MockLLM()),
            PerformanceAgent(MockLLM()),
            SecurityAgent(MockLLM()),
        ]
        for agent in agents:
            prompt = agent.build_prompt(SAMPLE_FILE, SAMPLE_PR)
            assert SAMPLE_PR.title in prompt
            assert SAMPLE_FILE.filename in prompt

    @pytest.mark.asyncio
    async def test_all_agents_produce_correct_category(self):
        """Each agent should tag its comments with the right category."""
        findings = [{"title": "T", "body": "B", "severity": "suggestion", "confidence": 0.5}]
        agents = [
            (LogicAgent(MockLLM(findings)), ReviewCategory.LOGIC),
            (ReadabilityAgent(MockLLM(findings)), ReviewCategory.READABILITY),
            (PerformanceAgent(MockLLM(findings)), ReviewCategory.PERFORMANCE),
            (SecurityAgent(MockLLM(findings)), ReviewCategory.SECURITY),
        ]
        for agent, expected_cat in agents:
            comments, _ = await agent.analyze(SAMPLE_FILE, SAMPLE_PR)
            assert len(comments) == 1
            assert comments[0].category == expected_cat


# ── Agent Registry ──────────────────────────────────────────────────────────


class TestAgentRegistry:
    def test_all_agents_registered(self):
        assert len(AGENT_CLASSES) == 4
        names = {cls.name for cls in AGENT_CLASSES}
        assert names == {"logic_agent", "readability_agent", "performance_agent", "security_agent"}

    def test_create_all_agents(self):
        llm = MockLLM()
        agents = create_all_agents(llm)
        assert len(agents) == 4
        assert all(isinstance(a, ReviewAgent) for a in agents)

    def test_create_agents_by_name(self):
        llm = MockLLM()
        agents = create_agents_by_name(llm, names=["logic_agent", "security_agent"])
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"logic_agent", "security_agent"}

    def test_create_agents_by_name_none(self):
        llm = MockLLM()
        agents = create_agents_by_name(llm, names=None)
        assert len(agents) == 4

    def test_create_agents_by_name_empty(self):
        llm = MockLLM()
        agents = create_agents_by_name(llm, names=[])
        assert len(agents) == 0

    def test_create_agents_unknown_name(self):
        llm = MockLLM()
        agents = create_agents_by_name(llm, names=["unknown_agent"])
        assert len(agents) == 0

    def test_get_agent_names(self):
        names = get_agent_names()
        assert len(names) == 4
        assert "logic_agent" in names
        assert "security_agent" in names
