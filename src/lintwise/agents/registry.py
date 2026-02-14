"""Agent registry — discovery and instantiation of review agents."""

from __future__ import annotations

from lintwise.agents.base import ReviewAgent
from lintwise.agents.logic_agent import LogicAgent
from lintwise.agents.performance_agent import PerformanceAgent
from lintwise.agents.readability_agent import ReadabilityAgent
from lintwise.agents.security_agent import SecurityAgent
from lintwise.llm.base import LLMProvider

# All available agent classes
AGENT_CLASSES: list[type[ReviewAgent]] = [
    LogicAgent,
    ReadabilityAgent,
    PerformanceAgent,
    SecurityAgent,
]


def create_all_agents(llm: LLMProvider) -> list[ReviewAgent]:
    """Instantiate all registered agents with the given LLM provider."""
    return [cls(llm) for cls in AGENT_CLASSES]


def create_agents_by_name(
    llm: LLMProvider,
    names: list[str] | None = None,
) -> list[ReviewAgent]:
    """Create agents filtered by name. If names is None, create all.

    Args:
        llm: The LLM provider to inject.
        names: Optional list of agent names to include (e.g. ["logic_agent", "security_agent"]).

    Returns:
        List of instantiated agents.
    """
    if names is None:
        return create_all_agents(llm)

    name_set = set(names)
    return [cls(llm) for cls in AGENT_CLASSES if cls.name in name_set]


def get_agent_names() -> list[str]:
    """Get the names of all registered agents."""
    return [cls.name for cls in AGENT_CLASSES]
