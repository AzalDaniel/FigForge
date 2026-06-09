# Contributing to figforge

Thanks for your interest! figforge is small on purpose — clean, dependency-light
building blocks for turning Figma exports into email-safe assets. Contributions
that keep it that way are very welcome.

## Ways to help

- **Report a bug** or **request a feature** via the issue templates.
- **Add a lint rule** for an email-client gotcha you've hit (these are the most
  valuable contributions — each rule saves someone a debugging session).
- **Improve the SVG forensics** to cover more Figma/Anima/Kombai export shapes.
- **Docs & examples**, especially recipes for other ESPs/templates.

## Dev setup

```bash
git clone https://github.com/AzalDaniel/FigForge && cd FigForge
python -m venv .venv && . .venv/bin/activate
pip install -e ".[render,dev]"        # core + render extras + dev tools
# Render extras need system libs:
#   Debian/Ubuntu: sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0
#   macOS:         brew install cairo pango
pre-commit install
```

## Before you open a PR

```bash
ruff check . && ruff format --check .   # lint + format
mypy figforge                           # types
pytest                                  # tests
```

- Keep the **core** (`forensics`, `lint`, pure-PIL helpers) free of heavy deps;
  put anything needing cairo/pango behind the `render` extra and import it lazily.
- Add a test for new behaviour. Lint rules should have a "catches it" and a
  "doesn't false-positive" case.
- Follow [Conventional Commits](https://www.conventionalcommits.org/) for
  messages (e.g. `feat(lint): flag VML-less background images`).
- Update `CHANGELOG.md` under `[Unreleased]`.

## Code style

Ruff (lint + format) and mypy are configured in `pyproject.toml`; pre-commit
runs them. Public functions get a docstring and type hints.

By contributing you agree your work is licensed under the project's
[Apache License 2.0](LICENSE).
