# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

All tasks run via `uv` + `poe` (poethepoet). Tasks are defined in `pyproject.toml` under `[tool.poe.tasks]`.

```bash
uv run poe format         # ruff check --fix && ruff format
uv run poe lint           # ruff check && mypy
uv run poe test           # pytest -n auto --dist=loadfile
uv run poe cover          # test + coverage report
uv run poe check-commit   # commitizen check on commits since origin/main
uv run poe all            # format → lint → check-commit → cover
uv run poe ci             # check-commit → prek run --all-files → cover
uv run poe setup-pre-commit  # install pre-commit hooks via prek
```

Releases: `cz bump` updates the version in `pyproject.toml` and regenerates `CHANGELOG.md` from conventional-commit history. Don't hand-edit `CHANGELOG.md` — it's regenerated.

## Architecture

The plugin is a single-file implementation: `src/pelican/plugins/heatmap/heatmap.py`. Bundled static assets (`static/`: JS + CSS widget) are copied into Pelican's output at build time. At build time the plugin scans all articles and writes a JSON data file; the widget fetches that JSON in the browser and renders the calendar client-side. A content shortcode can embed the heatmap in pages; static files are skipped during shortcode expansion.

## Conventions

- **Conventional commits** are required — `cz check` runs in pre-commit (and via `poe check-commit`).
- **Type checking**: mypy runs on `src` and `tests`; `pelican.*` modules are untyped, so missing imports are ignored for that namespace only.
- **Pre-commit**: `prek` is the runner; hooks live in `.pre-commit-config.yaml`.
