# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django REST API backend for an Academy of Arts chatbot. It implements a RAG (Retrieval-Augmented Generation) pipeline that indexes Academy documents (PDFs) and answers user questions in Arabic and English.

## Commands

```bash
# Start all services (PostgreSQL + Django)
docker-compose up

# Run development server (requires running DB)
python manage.py runserver 0.0.0.0:8000

# Database migrations
python manage.py migrate

# Lint and format
ruff check .
ruff format .

# Run all tests
python manage.py test

# Run a specific test module
python manage.py test chatbot.tests.test_views

# Run a single test case
python manage.py test chatbot.tests.test_views.AskViewTest.test_rate_limit
```

## Architecture

**Two Django apps:**
- `base_documents/` — manages uploaded PDF files (`BaseDocument` model with title, file, is_active)
- `chatbot/` — RAG pipeline, vector embeddings, and chat history

**RAG Pipeline** (`chatbot/services/`):
- `pipeline.py` — orchestrates the full query flow: embed query → retrieve chunks → generate answer with fallback
- `embedder.py` — Cohere multilingual v3.0 embeddings (1024-dim vectors)
- `retriever.py` — custom LangChain retriever doing cosine similarity against pgvector; threshold 0.45, top-k 5
- `generator.py` — LLM chain with bilingual system prompt; supports Groq and DeepSeek (switchable via `LLM_PROVIDER` env var)
- `parser.py` — PDF text extraction via PyMuPDF

**Background indexing:** `chatbot/signals.py` hooks into `BaseDocument` save/update signals and runs chunking + embedding in a background thread. DocumentChunks are automatically rebuilt when a document changes.

**Models:**
- `DocumentChunk` — FK to BaseDocument, text, 1024-dim pgvector embedding, page_number
- `ChatLog` — question, answer, was_answered, ip_address, created_at

**Only one public API endpoint:** `POST /api/chatbot/ask/`
- Input: `{"question": "..."}`
- Output: `{"answer": "...", "answered": boolean}`
- Rate limited to 20 requests/minute per IP (in-memory cache)

## Key Behaviors

- **Bilingual:** Arabic is detected via Unicode range check (`؀`–`ۿ`); system prompt switches language accordingly.
- **Fallback:** If the retriever returns too few chunks or the LLM responds with `INSUFFICIENT_DATA`, the pipeline returns a canned fallback message instead of a hallucinated answer.
- **Read-only admin:** `DocumentChunk` and `ChatLog` admin interfaces are intentionally read-only to prevent corrupting indexed data.

## Environment Variables

Key vars (see `.env.example`):
```
DATABASE_URL=postgres://...
SECRET_KEY=...
DEBUG=True
LLM_PROVIDER=groq          # or "deepseek"
COHERE_API_KEY=...
GROQ_API_KEY=...
DEEPSEEK_API_KEY=...
```

## Testing

Tests live in `chatbot/tests/` (one file per service: `test_views`, `test_pipeline`, `test_retriever`, `test_generator`, `test_parser`, `test_embedder`). All external LLM and embedding calls are mocked — tests do not require live API keys or a running database.

## CI

GitHub Actions (`.github/workflows/lint.yml`) runs ruff lint, ruff format check, and pip-audit on every push. Pre-commit hooks run the same ruff checks locally.
