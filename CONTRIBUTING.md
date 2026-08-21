# Contributing

Thanks for considering a contribution to Seam(De)Stress.

## Getting set up

The README's [🛠️ Development](README.md#️-development) section covers the
full local setup (virtualenv, `pip install -r requirements-dev.txt`,
`flask db upgrade`, `flask seed`, `flask run --debug`). The
[🚀 Quick Start](README.md#-quick-start) section covers running the whole
stack with Docker instead, if you'd rather not install Python/Postgres
locally.

## Before opening a pull request

CI runs both of these on every push and PR — running them locally first
saves a round-trip:

```bash
ruff check .
pytest -q --cov=app --cov-report=term-missing
```

Add or update tests for any behavior change. Coverage doesn't need to hit
100% (this repo deliberately favors meaningful coverage over the number),
but a new route or model change should have at least one test exercising
it.

## Conventions

[CLAUDE.md](CLAUDE.md) is the source of truth for this project's
architecture and the reasoning behind past decisions — app factory
structure, blueprint layout, config handling, i18n patterns, testing
fixtures, and a full milestone-by-milestone log of what shipped and why.
Please read the relevant sections before making structural changes (new
blueprint, new model, new config key, etc.) so new code follows the
existing patterns rather than introducing a second way of doing the same
thing.

A couple of house rules worth calling out:
- Comments should explain *why*, not *what* — well-named code should make
  the "what" obvious on its own.
- Don't add abstractions, config flags, or error handling for cases that
  can't occur yet — keep changes concrete and scoped to the problem at
  hand.

## Reporting bugs / requesting features

Use the issue templates — they ask for the details that are usually needed
to act on a report (repro steps, environment, etc.).
