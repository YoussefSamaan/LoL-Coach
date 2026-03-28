# Agents & Context

## Context Loading
When starting a new task, always ensuring you have the full context is critical.
1. **Check for Context**: If you do not have sufficient context about the project state, file structure, or recent changes, **ask the user** or use tools to explore (`list_dir`, `view_file` on `context/project_specs.md`, `tasks.txt`, etc.).
2. **Read Specs**: Verify current Milestone requirements in `context/project_specs.md`.

## Testing Standards
Reliability is paramount.
1. **100% Coverage**: All new code and refactors MUST be accompanied by tests that ensure 100% line coverage for the affected modules.
2. **Scaffolding**: Use the existing testing scaffolding found in `backend/tests` (e.g., `conftest.py` fixtures, `client` mocks) to ensure consistency.
   - Mock external dependencies (Riot API, Database, LLMs).
   - Use `pytest` fixtures for setup.
3. **No Regressions**: Ensure all existing tests pass before finishing a task.
