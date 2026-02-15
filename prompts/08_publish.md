# Prompt 08 — Publish & Ship

## Context
You are building ClaudeMD Forge. Read CLAUDE.md for full context. Prompts 01-07 are complete — everything works locally.

## Task
Prepare for PyPI publication and GitHub release. Make it shippable.

## Steps

### 1. README.md

Write a compelling README with:

```markdown
# 🔨 ClaudeMD Forge

> Generate optimized CLAUDE.md files for AI coding agents in seconds.

Stop hand-rolling CLAUDE.md. Let Forge analyze your codebase and generate 
a production-grade configuration file that makes Claude Code, Cursor, 
Windsurf, and Codex actually understand your project.

## Why?

AI coding agents are only as good as the context you give them. A well-crafted 
CLAUDE.md is the difference between an agent that writes idiomatic code and one 
that fights your conventions on every change.

ClaudeMD Forge:
- 🔍 **Scans** your codebase to detect languages, frameworks, and patterns
- 📝 **Generates** a complete CLAUDE.md with coding standards, commands, and anti-patterns
- 🔎 **Audits** existing CLAUDE.md files and scores them against best practices
- 🎯 **Framework-aware** presets for React, FastAPI, Rust, Django, Next.js, and more

## Install

\```bash
pip install claudemd-forge
\```

## Quick Start

\```bash
# Generate a CLAUDE.md for your project
claudemd-forge generate .

# Audit an existing CLAUDE.md
claudemd-forge audit ./CLAUDE.md

# Interactive setup
claudemd-forge init .

# See what would change
claudemd-forge diff .

# List available presets
claudemd-forge presets
\```

## Example Output

[Show a truncated example of generated CLAUDE.md for a React project]

## Framework Presets

| Preset | Description |
|--------|-------------|
| `python-fastapi` | FastAPI + async patterns |
| `react-typescript` | React + TypeScript + hooks |
| `rust` | Rust with clippy + proper error handling |
| `nextjs` | Next.js App Router conventions |
| `django` | Django with ORM patterns |
| `python-cli` | Python CLI with typer/click |
| `go` | Go with standard project layout |
| `node-express` | Express.js backend |

## Audit Scoring

Forge scores your CLAUDE.md on:
- Section coverage (does it have the essentials?)
- Accuracy (does it match your actual codebase?)
- Specificity (are instructions actionable or vague?)
- Anti-patterns (does it prevent common mistakes?)
- Freshness (is it up to date?)

## Contributing

[Standard contributing section]

## License

MIT
```

### 2. GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv pip install -e ".[dev]"
      - run: pytest tests/ -v --tb=short
      - run: ruff check src/ tests/
      - run: mypy src/
```

### 3. GitHub Actions (`.github/workflows/publish.yml`)

```yaml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

### 4. Final Checks

- [ ] `LICENSE` file exists (MIT)
- [ ] `.gitignore` covers Python, node, IDE files
- [ ] `pyproject.toml` metadata is complete for PyPI
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Lint clean: `ruff check src/ tests/`
- [ ] Type check clean: `mypy src/`
- [ ] README renders correctly on GitHub
- [ ] CLI help text is clear: `claudemd-forge --help`
- [ ] Tool works on itself: `claudemd-forge generate .` produces valid CLAUDE.md
- [ ] Audit works on itself: `claudemd-forge audit CLAUDE.md` scores > 60
- [ ] No hardcoded paths or secrets
- [ ] Version in `__init__.py` matches `pyproject.toml`

### 5. Publish Sequence

```bash
# Final test
pytest tests/ -v
ruff check src/ tests/
mypy src/

# Build
uv build

# Test install from wheel
pip install dist/claudemd_forge-0.1.0-py3-none-any.whl
claudemd-forge --help
claudemd-forge generate /tmp/some-test-project

# Tag and release
git tag v0.1.0
git push origin v0.1.0
# Create GitHub release → triggers publish workflow

# Verify on PyPI
pip install claudemd-forge
```

## Acceptance Criteria
- Package installs cleanly from built wheel
- `claudemd-forge --help` works after install
- CI pipeline passes on Python 3.11, 3.12, 3.13
- README renders correctly (no broken markdown)
- PyPI metadata shows correct description, author, links
- Tool is dogfood-ready: works on its own codebase
