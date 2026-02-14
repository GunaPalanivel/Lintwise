# 🔍 Lintwise

**Automated GitHub Pull Request Review Agent** — Multi-agent AI-powered code analysis.

Lintwise reads PR diffs from GitHub, runs them through specialized review agents (logic, readability, performance, security), and produces structured, actionable review comments.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your GitHub token and OpenAI API key

# Run
uvicorn lintwise.api.app:create_app --factory --reload

# Test
pytest tests/ -v
```

## Architecture

- **Modular monolith** — clean module boundaries, deployable as microservices
- **Multi-agent pipeline** — parallel analysis with 4 specialized agents
- **FastAPI backend** — async, typed, production-ready
- **LLM abstraction** — swap providers without code changes
