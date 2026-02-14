"""Readability & style analysis agent."""

from __future__ import annotations

from lintwise.agents.base import ReviewAgent
from lintwise.core.models import FileChange, PRDiff


class ReadabilityAgent(ReviewAgent):
    """Detects readability issues: poor naming, excessive complexity,
    missing docstrings, inconsistent style, magic numbers."""

    name = "readability_agent"
    category = "readability"

    def build_prompt(self, file_change: FileChange, context: PRDiff) -> str:
        return f"""Analyze this code diff for **readability and style issues**.

## PR Context
- **Title**: {context.title}
- **Description**: {context.description or 'N/A'}
- **File**: `{file_change.filename}` ({file_change.language or 'unknown'})
- **Changes**: +{file_change.additions} / -{file_change.deletions}

## Focus Areas
- Poor or misleading variable/function names
- Excessive function length or cyclomatic complexity
- Missing or outdated docstrings/comments
- Magic numbers/strings that should be constants
- Deep nesting that could be simplified
- Dead or commented-out code
- Inconsistent formatting or style
- Functions doing too many things (SRP violations)

## Diff
```{file_change.language or 'diff'}
{file_change.patch}
```

Return your findings as a JSON object with a "findings" key containing an array."""
