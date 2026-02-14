"""Pipeline orchestrator — parallel agent execution with fault tolerance."""

from __future__ import annotations

import asyncio
import time

from lintwise.agents.base import ReviewAgent
from lintwise.agents.registry import create_all_agents
from lintwise.core.logging import get_logger
from lintwise.core.models import (
    AgentMetrics,
    FileChange,
    PRDiff,
    ReviewComment,
    ReviewResult,
)
from lintwise.llm.base import LLMProvider
from lintwise.orchestrator.aggregator import aggregate_comments

logger = get_logger(__name__)


async def _run_agent_on_file(
    agent: ReviewAgent,
    file_change: FileChange,
    context: PRDiff,
    timeout: float,
) -> tuple[list[ReviewComment], AgentMetrics]:
    """Run a single agent on a single file with a timeout."""
    try:
        return await asyncio.wait_for(
            agent.analyze(file_change, context),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "agent_timeout",
            agent=agent.name,
            file=file_change.filename,
            timeout=timeout,
        )
        return [], AgentMetrics(
            agent_name=agent.name,
            files_analyzed=1,
            error=f"Timeout after {timeout}s",
        )


async def run_review(
    pr_diff: PRDiff,
    llm: LLMProvider,
    agents: list[ReviewAgent] | None = None,
    max_concurrent: int = 4,
    timeout_per_agent: float = 60.0,
) -> ReviewResult:
    """Execute the full review pipeline.

    1. For each file, fan out to all agents in parallel
    2. Collect results with fault tolerance (partial results on failure)
    3. Aggregate: deduplicate, rank, compute risk score
    4. Return the final ReviewResult

    Args:
        pr_diff: The PR to review.
        llm: LLM provider for agents.
        agents: Optional list of pre-created agents. Creates all if None.
        max_concurrent: Maximum concurrent agent tasks.
        timeout_per_agent: Per-agent per-file timeout in seconds.

    Returns:
        Aggregated ReviewResult.
    """
    start_ms = time.perf_counter_ns() // 1_000_000

    if agents is None:
        agents = create_all_agents(llm)

    semaphore = asyncio.Semaphore(max_concurrent)
    all_comments: list[ReviewComment] = []
    all_metrics: list[AgentMetrics] = []

    async def _bounded_analysis(
        agent: ReviewAgent, file_change, context: PRDiff
    ) -> tuple[list[ReviewComment], AgentMetrics]:
        async with semaphore:
            return await _run_agent_on_file(agent, file_change, context, timeout_per_agent)

    # Build all tasks: agents × files
    tasks = []
    for file in pr_diff.files:
        for agent in agents:
            tasks.append(_bounded_analysis(agent, file, pr_diff))

    logger.info(
        "pipeline_started",
        files=len(pr_diff.files),
        agents=len(agents),
        total_tasks=len(tasks),
    )

    # Execute all with return_exceptions for fault tolerance
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error("task_exception", error=str(result))
            continue
        comments, metrics = result
        all_comments.extend(comments)
        all_metrics.append(metrics)

    # Aggregate
    ranked_comments, risk_score = aggregate_comments(all_comments)

    total_ms = (time.perf_counter_ns() // 1_000_000) - start_ms

    logger.info(
        "pipeline_complete",
        total_comments=len(ranked_comments),
        risk_score=risk_score.value,
        duration_ms=total_ms,
    )

    return ReviewResult(
        pr_diff=pr_diff,
        comments=ranked_comments,
        risk_score=risk_score,
        agent_metrics=all_metrics,
        total_duration_ms=total_ms,
    )
