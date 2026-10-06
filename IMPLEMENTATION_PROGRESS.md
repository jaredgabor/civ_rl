# Civ-RL implementation progress

Current milestone: A — foundation and static world.

| Ticket | Status | Validation | Decision or note |
| --- | --- | --- | --- |
| T01 | Complete | Focused/full pytest: 1 passed; Ruff lint/format passed; locked offline sync made no changes. | Existing uv environment retained; pytest root import configured. |
| T02 | Complete | Focused pytest: 14 passed; full pytest: 15 passed; Ruff lint/format passed. | Fixed immutable unit/rules definitions and domain IDs. |
| T03 | Complete | Focused pytest: 12 passed after review fix; full pytest: 34 passed; Ruff lint/format passed. | Static odd-row map, validated terrain/features, canonical rivers, distance, and legacy ID decoder. |
| T04 | Complete | Focused visibility pytest: 7 passed; full pytest: 34 passed; Ruff lint/format and diff check passed. | Range-2 shot needs at least one clear shared intermediate tile; prototype renderer color lookup adjusted to separate terrain/features. |

Current blockers: None. T05 begins mutable entity state and is outside the requested milestone.

Next ticket: T05 (Milestone B). Do not start until the user asks to continue.
