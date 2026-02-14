"""Performance analysis agent."""

from __future__ import annotations

from lintwise.agents.base import ReviewAgent
from lintwise.core.models import FileChange, PRDiff


class PerformanceAgent(ReviewAgent):
    """Detects performance anti-patterns: N+1 queries, unnecessary allocations,
    inefficient algorithms, missing caching, blocking I/O in async code."""

    name = "performance_agent"
    category = "performance"

    def build_prompt(self, file_change: FileChange, context: PRDiff) -> str:
        return f"""Analyze this code diff for **performance issues**.

## PR Context
- **Title**: {context.title}
- **Description**: {context.description or 'N/A'}
- **File**: `{file_change.filename}` ({file_change.language or 'unknown'})
- **Changes**: +{file_change.additions} / -{file_change.deletions}

## Focus Areas
- N+1 query patterns (database calls in loops)
- Unnecessary object/list allocations
- Inefficient algorithms (O(n²) when O(n) is possible)
- Missing caching opportunities
- Blocking I/O in async code (sync calls in async functions)
- Unnecessary re-computation
- Large data structures loaded entirely into memory
- Inefficient string concatenation in loops
- Missing pagination for large data sets

## Diff
```{file_change.language or 'diff'}
{file_change.patch}
```

Return your findings as a JSON object with a "findings" key containing an array."""
