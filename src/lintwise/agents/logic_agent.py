"""Logic & correctness analysis agent."""

from __future__ import annotations

from lintwise.agents.base import ReviewAgent
from lintwise.core.models import FileChange, PRDiff


class LogicAgent(ReviewAgent):
    """Detects logic errors: null dereferences, unreachable code, off-by-one,
    missing edge cases, faulty conditions, incorrect return values."""

    name = "logic_agent"
    category = "logic"

    def build_prompt(self, file_change: FileChange, context: PRDiff) -> str:
        return f"""Analyze this code diff for **logic and correctness issues**.

## PR Context
- **Title**: {context.title}
- **Description**: {context.description or 'N/A'}
- **File**: `{file_change.filename}` ({file_change.language or 'unknown'})
- **Changes**: +{file_change.additions} / -{file_change.deletions}

## Focus Areas
- Null/None dereferences and missing null checks
- Off-by-one errors in loops and array indexing
- Unreachable code after return/break/continue
- Faulty conditional logic (wrong operator, missing cases)
- Missing edge case handling (empty input, boundary values)
- Incorrect return types or values
- Variable shadowing or incorrect scope
- Race conditions in concurrent code

## Diff
```{file_change.language or 'diff'}
{file_change.patch}
```

Return your findings as a JSON object with a "findings" key containing an array."""
