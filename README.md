# Civ-RL

A small Civilization-inspired tactical combat simulator for studying reinforcement learning.

The existing engine and renderer are prototypes. The [implementation plan](IMPLEMENTATION_PLAN.md), [ordered tickets](IMPLEMENTATION_TICKETS.md), and [progress log](IMPLEMENTATION_PROGRESS.md) define the path to a deterministic siege benchmark.

Set up the locked environment with `uv sync --locked`. Run tests with `uv run --locked pytest`, lint with `uv run --locked ruff check .`, and check formatting with `uv run --locked ruff format --check .`.

For a quick static-rule check, run `uv run --locked python -c 'from engine.map import HexMap; from engine.visibility import has_line_of_sight; m = HexMap(6, 6); print(has_line_of_sight(m, (0, 2), (2, 2)))'`. It prints `True` on an open map. Movement, combat, turns, and RL integration are later tickets.
