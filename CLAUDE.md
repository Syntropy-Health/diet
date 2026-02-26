# DIET - Diet Insight Engine Transformer

## Project Overview

DIET is the central intelligence service for SyntropyHealth. It processes health journal entries through the SDO (Symptom-Diet Optimizer) pipeline and generates personalized nutritional recommendations.

## Architecture

- **Framework**: FastAPI + uvicorn
- **AI Pipeline**: LangGraph/LangChain with LangSmith tracing
- **Config**: Hydra 1.3+ / OmegaConf (all config in `config/`)
- **Package**: `diet` (Python package at `diet/`)
- **API**: REST with RFC 7807 error responses

## Key Directories

```
app/              # FastAPI application (main.py, routers/, services/)
diet/             # Core package (sdo/, models/, notifications/, utils/, health_store_agent/)
config/           # Hydra YAML configs (app/, llm/, api/, pipeline/, logging/, prompts/)
tests/            # Pytest test suite
data/demo/        # Demo journal entries for testing
.claude/          # PRDs and project docs
```

## Commands

```bash
# Setup
uv sync --all-extras
cp .env.template .env  # Fill in API keys

# Run
uvicorn app.main:app --reload --port 8000

# Test
PYTHONPATH=. uv run pytest tests/ -v

# Lint
uv run black . && uv run isort .
```

## Conventions

- All configuration via Hydra YAML, never hardcoded values
- Use `get_config_manager().get("key.path", default)` for config access
- RFC 7807 ProblemDetail for all error responses
- Correlation IDs on every request via middleware
- structlog for structured logging
- Pydantic v2 models for all request/response schemas

## Parent Monorepo

This repo is a submodule of `Syntropy-Health/SyntropyHealth` at `apps/diet/`.
