# AGENTS.md

## Build & Test Commands
- **Frontend dev**: `npm run dev`
- **Frontend tests**: `npm run test` (single: `npx vitest run path/to/test.ts`)
- **Type check**: `npm run type-check`
- **Backend tests**: `cd backend && uv run pytest` (single: `uv run pytest tests/unit/test_file.py::test_name`)
- **Build**: `npm run build:win` (Windows), `npm run build:mac` (Mac), `npm run build:linux` (Linux)

## Architecture
- **Electron + React + Vite** frontend in `src/` with Zustand state, Radix UI, TailwindCSS
- **FastAPI + Python** backend in `backend/` using CAMEL-AI multi-agent framework
- Backend uses `uv` for dependency management (Python 3.10), Ruff for linting (line-length=120)
- Multi-agent workforce system with specialized agents (developer, browser, document, MCP)

## Code Style
- **Python**: Ruff linting, 120 char lines, type hints required, async/await patterns
- **TypeScript**: Strict mode, React functional components, absolute imports from `src/`
- **Naming**: camelCase (TS), snake_case (Python), PascalCase for components/classes
- **Imports**: Group stdlib → third-party → local; use `@/` alias for src imports in frontend
- **Error handling**: Use try/catch with proper logging; Python uses `logging` module
- **No mutable default args** in Python (Ruff B006 enabled)
