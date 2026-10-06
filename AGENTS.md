# Civ-RL working instructions

- Follow `IMPLEMENTATION_PLAN.md` and `IMPLEMENTATION_TICKETS.md` in ticket order. The user's latest decisions take precedence. Stop at the requested milestone boundary.
- Keep the simulation engine independent of rendering, Gymnasium, and training libraries. The first benchmark is a passive, wall-less city.
- Use `uv run --locked` for project commands. For each code ticket, run focused tests, the full test suite, `ruff check .`, and `ruff format --check .`; fix failures before advancing.
- Add tests for behavior and invariants, especially deterministic outcomes and unchanged state after invalid actions. Keep render outputs out of Git.
- Record completed tickets, validation, decisions, blockers, and next work in `IMPLEMENTATION_PROGRESS.md` after each ticket.
- Preserve unrelated user changes. Ask about gameplay decisions that materially change the agreed rules; do not silently expand v1 into deferred mechanics.
