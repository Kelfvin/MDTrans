# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `mdtrans/`. Use `cli.py` for argument parsing and entrypoints, `app.py`/`main.py` for orchestration, `mineru_runner.py` for PDF conversion, and `translator.py` plus `chunking.py` for Markdown translation flow. Shared constants and config helpers are in `constants.py` and `config.py`. Utility scripts belong in `tools/`, and repository-level config lives in `pyproject.toml`, `uv.lock`, and `config.toml`. Treat `tmp/` as generated working data; do not commit PDFs or translated outputs.

## Build, Test, and Development Commands
Install and lock dependencies with `uv sync`. Run the CLI locally with `uv run mdtrans path/to/input.pdf path/to/output-dir`. For ad hoc module execution, use `uv run python -m mdtrans.cli path/to/input.pdf path/to/output-dir`. Estimate Markdown token counts with `uv run python tools/token_length.py path/to/file.md`. Before running translation, export `OPENAI_API_KEY` and keep `config.toml` populated with `[llm] base_url` and `model`.

## Coding Style & Naming Conventions
Target Python 3.11+ and follow existing style: 4-space indentation, type hints on public functions, `Path` over raw strings for filesystem paths, and small focused modules. Use `snake_case` for functions, variables, and module names; use `PascalCase` for dataclasses like `LLMConfig`; reserve `UPPER_SNAKE_CASE` for constants. Prefer clear exceptions over silent fallbacks, and keep CLI help text and log messages direct.

## Testing Guidelines
There is no dedicated `tests/` package yet. When adding non-trivial logic, create `tests/` with `test_*.py` files and cover path resolution, config validation, chunk splitting, and failure handling around external tools. Until a formal suite exists, verify changes with targeted `uv run` CLI runs against a small sample PDF and document the command used in the PR.

## Commit & Pull Request Guidelines
Current history uses short, imperative commit subjects in Chinese, for example `完成pdf 文档转换`. Keep subjects concise, action-oriented, and scoped to one change. Pull requests should include the purpose, affected modules, manual verification steps, and any required config or environment changes. Include sample input/output paths or terminal excerpts when CLI behavior changes.

## Security & Configuration Tips
Do not commit secrets. Keep `OPENAI_API_KEY` in the environment, not in `config.toml`. Review generated Markdown before sharing it externally, since source PDFs may contain sensitive material.
