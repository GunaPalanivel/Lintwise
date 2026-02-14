"""Security vulnerability analysis agent."""

from __future__ import annotations

from lintwise.agents.base import ReviewAgent
from lintwise.core.models import FileChange, PRDiff


class SecurityAgent(ReviewAgent):
    """Detects security vulnerabilities: SQL injection, XSS, hardcoded secrets,
    insecure deserialization, missing input validation, unsafe regex."""

    name = "security_agent"
    category = "security"

    def build_prompt(self, file_change: FileChange, context: PRDiff) -> str:
        return f"""Analyze this code diff for **security vulnerabilities**.

## PR Context
- **Title**: {context.title}
- **Description**: {context.description or 'N/A'}
- **File**: `{file_change.filename}` ({file_change.language or 'unknown'})
- **Changes**: +{file_change.additions} / -{file_change.deletions}

## Focus Areas
- SQL injection (string interpolation in queries)
- Cross-site scripting (XSS) via unsanitized user input
- Hardcoded secrets, API keys, passwords, tokens
- Insecure deserialization (pickle, eval, exec)
- Missing input validation and sanitization
- Path traversal vulnerabilities
- Unsafe regular expressions (ReDoS)
- Insecure cryptographic practices
- SSRF (Server-Side Request Forgery)
- Missing authentication/authorization checks
- Sensitive data exposure in logs or error messages

## Diff
```{file_change.language or 'diff'}
{file_change.patch}
```

Return your findings as a JSON object with a "findings" key containing an array."""
