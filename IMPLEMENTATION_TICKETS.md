# Civ-RL Implementation Tickets

This is the ordered coding backlog for the engine, visualization, and replay
work described in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). A ticket is
complete only when its acceptance criteria pass. Later tickets may refine a
public interface only with corresponding test updates.

## Shared conventions

- **Initial benchmark:** two warriors and one slinger controlled by one player;
  an ungarrisoned, wall-less, passive city; deterministic 6x6 map; 20 turns.
- **Out of scope until after the benchmark:** Gymnasium, PPO, rewards,
  observations, action-index encoding, active defenders, city ranged attacks,
  walls in the benchmark, and combat-strength modifiers.
- **Engine rule:** a rejected action never changes state. Renderer and replay
  consume snapshots/events and never mutate a `Game`.
- **Test rule:** run focused tests, `uv run --locked pytest`, and
  `uv run --locked ruff check .` for code tickets; add
  `uv run --locked ruff format --check .` once T01 configures formatting.
- **Commit rule:** keep functional code and its tests in the same ticket/commit
  where practical. Do not commit `.venv`, cache directories, or generated
  frames.

## Implementation order and dependencies

Implement T01–T15 in numeric order. The table lists actual prerequisites;
earlier tickets need not depend on every intervening ticket.

| Ticket | Prerequisites |
| --- | --- |
| T01 | None |
| T02 | T01 |
| T03 | T01, T02 |
| T04 | T02, T03 |
| T05 | T02 |
| T06 | T03, T05 |
| T07 | T04, T06 |
| T08 | T03, T06, T07 |
| T09 | T02, T06, T07 |
| T10 | T08, T09 |
| T11 | T10 |
| T12 | T10, T11 |
| T13 | T03, T06, T10 |
| T14 | T12, T13 |
| T15 | T10, T11, T14 |

T01–T04 establish static mechanics; T05–T07 establish state and legality;
T08–T11 produce the playable benchmark; T12–T14 provide text and graphical
inspection; T15 supplies replay and the RL handoff.

## Review findings and decision gates

Environment setup already exists: uv metadata/lockfile, Python 3.13 pin, dev
dependencies, .envrc, and basic Git ignores. T01 verifies and extends this setup;
it must not reinitialize it. Python commands should explicitly use uv because
non-interactive shells need not activate direnv. Cache permission prompts are
sandbox controls, not evidence that the environment is broken.

The user approved the following rules for v1. They are also recorded in
IMPLEMENTATION_PLAN.md. Future tickets should use them without reopening the
decision unless implementation reveals a material conflict.

| Choice | Proposed simple v1 rule | Gate |
| --- | --- | --- |
| Terrain cost and mountains | Plains 1; woods or hills 2; wooded hills 2 (non-additive); mountains/ocean impassable. | T02/T03 |
| Range-2 line of sight | Adjacent targets always visible. At distance 2, consider shared neighbors; at least one must be free of mountain/woods/hills. Endpoints and units do not block; no elevation advantage. Reject distance 0 or >2 in this v1 query. | T04 |
| Attack movement cost | Require at least 1 MP; attack consumes all remaining movement and the one attack allowance. Melee uses adjacency, not movement-path costs, including across rivers. | T07 |
| Capture and retaliation ordering | Resolve both melee damage amounts from pre-attack state simultaneously. If attacker survives and city reaches 0 HP, enter/capture atomically. If attacker dies, no capture. A zero-HP uncaptured city remains present; a subsequent melee attack still retaliates. Ordinary Move cannot enter an enemy city. | T07/T09 |

The slinger cannot be killed by this passive city: ranged attacks receive no
retaliation. Therefore the baseline can lose at the time limit, but an
all-attackers-dead trace needs a separately identified melee-only fixture.
Likewise range-2 LoS requires an archer fixture, not the initial range-1 roster.
Do not alter those mechanics merely to manufacture coverage.

Use the following engineering conventions when implementing:
integer damage is rounded half-up (`floor(damage + 0.5)`); healing clamps at
maximum HP; rejected actions return diagnostics without appending game events;
dead unit IDs are never reused during an episode. A zero-HP city is not a dead
unit and can remain uncaptured and heal. These conventions need explicit tests.

---

## Milestone A — Foundation and static world

### T01 — Establish project, packages, and test harness

**Depends on:** none

**Goal:** Turn the prototype directory into a consistently testable Python
project without changing game behavior.

**Work:**

- Add `engine/__init__.py` and a `tests/` package/layout.
- Extend the existing `.gitignore` with tool caches and a dedicated generated
  output directory. Keep intentionally committed JSON replay fixtures trackable.
- Configure pytest and Ruff in `pyproject.toml`; define explicit local settings
  so user-global Ruff preferences cannot change project checks. Resolve existing
  lint/format findings without implementing gameplay or removing public exports.
- Limit routine checks to maintained Python source/tests; the scratch notebook
  is exploratory and is excluded from the initial lint scope.
- Add only the development dependencies actually used by the repository.
- Create a short mechanics/readme pointer explaining that the existing modules
  are being replaced behind tested APIs.
- Add a smoke test proving imports work through the package, not from a notebook
  working directory.

**Acceptance criteria:**

- `uv run --locked pytest` discovers and passes at least one test.
- `uv run --locked ruff check .` and `uv run --locked ruff format --check .` pass.
- A fresh `uv sync --locked` produces a runnable test environment.
- `.venv`, Python caches, notebook checkpoints, and generated visual artifacts
  are ignored by Git; source, tests, `pyproject.toml`, and `uv.lock` are not.

**Notes:** Do not add Gymnasium, Stable-Baselines3, or PyTorch here.

---

### T02 — Define domain types and the fixed v1 ruleset

**Depends on:** T01

**Goal:** Replace magic integers and scattered constants with a small, immutable
domain vocabulary and one documented ruleset.

**Work:**

- Add value types/enums for coordinates, owners, terrain, features, unit kinds,
  target kinds, terminal outcomes, and action/event categories.
- Add immutable `UnitType` and `Ruleset` records.
- Encode the agreed unit and city values: warrior, slinger, archer (present for
  future scenarios), integer HP, base movement, attack range, damage curve,
  city HP 100, city defense strength 25, healing rules, and turn
  cap default 20.
- Make invalid ruleset definitions fail at construction with useful errors.
- Document explicitly that v1 has no health/terrain/river/fortification/flank/
  support/garrison strength modifiers.

**Acceptance criteria:**

- Tests instantiate the standard ruleset and assert every fixed v1 value.
- Invalid HP, range, movement, strength, and damage-curve values are rejected.
- No mutable game state lives in `Ruleset` or `UnitType`.

**Notes:** This ticket defines configuration values; it does not resolve combat.

---

### T03 — Rebuild hex-map geometry and static terrain contract

**Depends on:** T01, T02

**Goal:** Make `HexMap` the validated, read-only source of static world truth.

**Work:**

- Retain `(row, col)` odd-row offset coordinates and centralize neighbors,
  offset-to-cube conversion, hex distance, and in-bounds checks.
- Separate base terrain from features where needed while retaining a clean
  compatibility mapping for the prototype terrain IDs.
- Define passability and entry movement costs: ocean/mountains are impassable;
  plains cost 1; woods/hills/wooded hills cost 2.
- Retain canonical unordered river-edge storage and validate river adjacency.
- Remove city positions and all mutable entity ownership from `HexMap`.
- Add map construction/validation APIs suitable for hand-authored scenarios.

**Acceptance criteria:**

- Neighbor symmetry holds for both row parities, all corners, and interior cells.
- Hex distance is symmetric, zero only for identical tiles, and one for every
  neighbor.
- Invalid coordinates, terrain/feature combinations, and non-adjacent river
  edges fail without changing the map.
- Tests cover terrain passability and every defined movement cost.

**Notes:** No random-map work in this ticket; retain it only if it can sit behind
the new static-map contract without weakening tests.

---

### T04 — Implement the v1 line-of-sight contract

**Depends on:** T02, T03

**Goal:** Specify and test visibility before attack legality depends on it.

**Work:**

- Define line-of-sight semantics for range 1 and range 2 attacks on the selected
  odd-row coordinate system.
- Implement the range-2 intermediate-tile lookup without duplicating coordinate
  parity logic.
- Implement the LoS decision recorded at the gate above, including ambiguous
  distance-2 paths, endpoints, map boundaries, and terrain blockers.
- Expose a pure `has_line_of_sight(map, source, target)` query.
- Document every intentional simplification (for example, no unit blocking).

**Acceptance criteria:**

- All range-1 targets have line of sight unless an explicitly documented rule
  forbids it.
- Tests cover every range-2 direction on both row parities.
- Tests distinguish clear, mountain-blocked, woods-blocked, hills-blocked, and
  out-of-range targets.
- The function has no dependency on `GameState`, renderer, or RL code.

**Decision note:** The LoS rule above has been approved; lock it with tests.

---

## Milestone B — Mutable state and legal actions

### T05 — Complete array-backed entity lifecycle

**Depends on:** T02

**Goal:** Replace partial prototype arrays with safe, centralized unit and city
state containers.

**Work:**

- Implement `UnitStates` arrays for stable ID, alive state, owner, type,
  position, current/max HP, movement remaining, and per-turn moved/attacked
  flags.
- Implement `CityStates` arrays for stable ID, owner, position, and current/max
  HP. Wall and garrison behavior/fields can wait for their later tickets.
- Provide validated `spawn`, `kill`, `begin_turn`, damage/heal, lookup, and
  read-only view/snapshot helpers.
- A default city has no walls or independent ranged action; no capability
  framework is needed in v1.
- Preserve dead unit records for replay but make them non-occupying/non-targetable.
  An uncaptured city at zero HP is still present and capturable; do not kill it.

**Acceptance criteria:**

- IDs remain stable after deaths and later spawns.
- HP always remains an integer in `[0, max_hp]`.
- Remove prototype garrison lookup and strongest-unit strength logic from v1;
  city strength is fixed and independent of attacker roster.
- Begin-turn behavior restores exactly the permitted fields and does not revive
  entities.
- Copy/snapshot tests show no mutable-array aliasing.

**Notes:** Do not put occupancy maps, action legality, or combat calculations in
the entity containers.

---

### T06 — Add `GameState`, snapshots, and invariants

**Depends on:** T03, T05

**Goal:** Create one coherent in-memory world state that is safe to validate,
copy, render, and later serialize.

**Work:**

- Add `GameState` owning map, units, cities, active owner, turn number/limit,
  seeded RNG, last event, and terminal outcome.
- Provide immutable/debug snapshots and a deep-copy path.
- Implement state validation: live entity locations in bounds, unit occupancy
  unique, city positions unique, valid owners/types, HP bounds,
  valid terminal state, and no dead entity as a target/occupant.
- Make occupancy a query derived from live unit state; do not cache it in tiles.
- Add a minimal factory used only by tests to create valid/invalid states.

**Acceptance criteria:**

- Validation accepts a minimal valid scenario and rejects each invariant breach
  with a precise error.
- Mutating a copy or snapshot cannot mutate the original state.
- The map contains no dynamic city/unit state.
- State creation and validation are deterministic for a supplied seed.

---

### T07 — Model typed actions, events, and legal-action discovery

**Depends on:** T04, T06

**Goal:** Establish the engine-facing action contract before writing mutating
resolvers.

**Work:**

- Define immutable action records: move, melee attack, ranged attack, and end
  turn. Omit fortify from v1 rather than adding a no-op placeholder.
- Define immutable event records for successful transitions: move,
  damage, death, healing, turn advance, capture, and terminal outcome.
- Implement pure legal-target and legal-action enumeration for the active owner,
  including live state, ownership, movement/action flags, range, and LoS.
- Define a structured invalid-action error/result but do not mutate state on it.
- Make legal-action output deterministic. A later wrapper must define a fixed
  action catalog and mask that catalog; indices in a changing list of legal
  actions are not a stable RL action encoding.
- Implement shared pure movement-cost/legality helpers here (including river
  handling) and reuse them in T08. Resolvers must not duplicate legality rules.
- EndTurn is always legal for a nonterminal attacker turn. No action is legal
  after termination. Apply the attack/capture decision gate to legal targets.

**Acceptance criteria:**

- The same state always enumerates actions in the same order.
- Illegal owner, dead unit, dead target, out-of-range target, blocked LoS,
  exhausted movement, duplicate attack, and inactive-side actions are absent.
- No legal-action query mutates arrays or consumes RNG.
- Tests can construct actions using IDs/coordinates without renderer knowledge.

---

## Milestone C — Deterministic siege engine

### T08 — Resolve movement, including Civ-like river crossing

**Depends on:** T03, T06, T07

**Goal:** Implement the first mutating game action with full validation and
auditable events.

**Work:**

- Add a movement resolver used exclusively by the future `Game.apply` facade.
- Enforce active owner, live unit, legal destination, one-unit-per-tile,
  passability, and remaining-movement rules.
- Move actions step to one adjacent tile; apply the approved destination cost.
  Do not add pathfinding or multi-tile move actions in v1.
- Apply the agreed river special case: compute normal destination cost plus river
  surcharge; a unit beginning the move at full base movement may cross even when
  that cost exceeds remaining movement, then has zero remaining movement;
  otherwise sufficient movement is required.
- Set moved flags and emit a move event containing source/destination/cost and
  movement before/after.

**Acceptance criteria:**

- A 2-movement unit can cross an adjacent river as its only move from full
  movement, and cannot do so after first spending movement.
- Ordinary, woods, hills, impassable, occupied, out-of-bounds, and insufficient
  movement cases behave exactly as documented.
- A rejected move leaves a deep logical snapshot byte-for-byte unchanged.
- The resolver performs no rendering or direct action-mask encoding.

---

### T09 — Resolve combat, city damage, retaliation, and capture

**Depends on:** T02, T06, T07

**Goal:** Implement deterministic combat against the passive city without adding
deferred modifiers or an independent defender action.

**Work:**

- Preserve/refactor the capped exponential pure damage calculation.
- Define and test the one rounding convention used to convert computed damage
  to integer HP changes.
- Resolve melee unit-to-city attacks: city loses HP and the attacker receives
  city retaliation based on fixed city defense strength 25.
- Resolve ranged unit-to-city attacks: city loses HP and attacker receives no
  retaliation.
- Implement death and target-removal events.
- Require a living melee unit to enter a city tile after city HP reaches zero;
  ranged units cannot capture.
- Defer wall damage, city shots, garrisoning, and unit-to-unit combat completely.
  Apply the agreed capture/retaliation decision atomically, including simultaneous
  lethal damage and a pre-existing zero-HP city.

**Acceptance criteria:**

- Damage curve, delta cap, rounding, HP clamp, retaliation, and death have
  independently specified tests.
- A slinger can damage but cannot capture a zero-HP city.
- A valid melee capture creates an explicit capture event and terminal victory.
- A city with no walls exposes no independent ranged action.
- Tests prove that no combat-strength modifiers affect v1 damage.

---

### T10 — Implement turns, healing, terminal outcomes, and `Game.apply`

**Depends on:** T08, T09

**Goal:** Join all resolvers into the sole public mutation gateway for a complete
deterministic episode.

**Work:**

- Implement `Game.reset`, `legal_actions`, `apply`, `end_turn`, and `snapshot`.
- Dispatch typed actions only after exact legal-action validation.
- Enforce one attack per unit per turn; reset movement/action state at turn start.
- At EndTurn heal surviving idle attackers by 10 (no movement or attack that
  turn), then heal the uncaptured city by 10 during the automatic defender phase.
  Clamp healing to maximum HP. Reset unit flags only after checking eligibility.
- Number attacker turns 1–20. Allow capture during turn 20. After EndTurn on
  turn 20, resolve healing then timeout; do not start turn 21. Victory/all-dead
  outcomes resolve immediately after actions and prevent subsequent healing.
- Define Game.reset from a validated scenario specification in this ticket;
  tests use tiny fixtures. T11 supplies the named benchmark, not this API.
- End episodes on capture, every attacking unit dead, or the 20-turn limit.
  Keep distinct outcome reasons: timeout is a scenario loss but the later Gym
  wrapper maps the time limit to truncation, not a natural termination.
- Emit events in an unambiguous sequence, including end/start turn, healing,
  terminal outcome, and the parent action identifier.

**Acceptance criteria:**

- Scripted fixtures exercise capture, all attackers dead, and time limit;
  the all-dead fixture has only melee attackers.
- Rejected actions do not change snapshot, turn, RNG, or event history.
- The same scenario, seed, and action trace yield equal final snapshots/events.
- `Game` imports no rendering, Gymnasium, Stable-Baselines, or training code.

---

### T11 — Freeze initial scenario and golden integration traces

**Depends on:** T10

**Goal:** Make the first tactical experiment reproducible and explainable.

**Work:**

- Implement versioned, data-oriented `InitialSiegeScenario` and
  `make_initial_siege(seed=...)`.
- Hand-author a simple exact 6x6 benchmark with city and attacker positions.
  River and varied terrain are optional in this first training map; exercise
  them in named mechanics fixtures rather than requiring every feature here.
- Demonstrate solvability with an explicit winning action trace within 20 turns.
  Verify it respects occupancy, action budgets, and healing. If the starting
  layout prevents victory, revise layout before freezing it, not combat rules.
- Add short named scripted traces for victory, defeat, and time-limit outcomes.
- Use the verified scripted trace as the first demo driver. A general heuristic
  policy is optional follow-up work, not a blocker for the initial engine.

**Acceptance criteria:**

- Resetting with the same seed recreates exactly the same state.
- Golden traces have committed expected action/event summaries and final states.
- Benchmark traces exercise melee retaliation, ranged damage, healing, capture,
  and timeout. Separate river/terrain and range-2 archer fixtures cover geometry.
- Use a separately named melee-only scenario for the all-dead outcome; retain its
  full scenario identity in logs/replays.

---

## Milestone D — Human debugging and visualization

### T12 — Add text logging and a scriptable headless driver

**Depends on:** T10, T11

**Goal:** Make every episode understandable in a terminal before adding graphics.

**Work:**

- Provide a concise state/event formatter with coordinates, unit type/owner/HP,
  city HP, movement left, turn, and terminal state.
- Add a command/script entry point that runs a supplied action trace or the
  scripted benchmark trace.
- Format rejected actions and events clearly enough to diagnose a test failure.
- Keep output separate from engine mutation and avoid print statements in engine
  modules.

**Acceptance criteria:**

- A developer can run the victory trace and read every transition from stdout.
- The formatter does not mutate state and is covered by deterministic snapshot
  tests.
- No notebook is required to execute the initial scenario.

---

### T13 — Build read-only scene adapter and static hex renderer

**Depends on:** T03, T06, T10

**Goal:** Replace the prototype renderer’s ad-hoc input with an engine-aligned,
read-only visual representation.

**Work:**

- Define immutable scene records generated only from a `GameState` snapshot.
- Move common tile-center/vertex geometry to a shared source so renderer and
  engine cannot disagree about odd-row placement.
- Refactor `HexMapRenderer` to accept the scene/static map rather than unit/city
  HP dictionaries; remove the `print('doing rivers')` side effect.
- Render terrain, river edges, optional coordinate labels, city state, unit
  owner/type glyphs, HP, and movement remaining.
- Use the non-interactive Agg backend in automated tests.

**Acceptance criteria:**

- A known coordinate has identical engine/renderer center geometry.
- River edges lie on the shared geometric hex edge.
- Rendering opening and post-action snapshots does not mutate them.
- A headless smoke test writes a deterministic-size PNG.
- Keep pixel projection/render sizing in the rendering layer; reuse the
  engine's coordinate convention without importing Matplotlib into the engine.

---

### T14 — Add debug HUD and RGB-array render mode

**Depends on:** T12, T13

**Goal:** Make frames useful for tactical inspection and ready for the later
Gymnasium rendering interface, without importing Gymnasium.

**Work:**

- Add HUD fields: turn, active side, city HP, terminal status, last action,
  event summary, and selected/active unit state where applicable.
- Add `render_snapshot(snapshot, ax=None)` and a non-blocking RGB-array method.
- Add explicit PNG-frame saving with caller-supplied paths; do not save or show
  by default.
- Represent wall/city capabilities accurately: a no-wall city has no wall bar
  and no city-shot annotation.

**Acceptance criteria:**

- A user can visually distinguish opening, movement, damage, healing, death,
  capture, and terminal frames.
- RGB output is a `uint8` array with documented shape/channel order and fixed
  dimensions. Repeated frames are stable in the same environment; do not promise
  pixel equality across font, Matplotlib, or OS versions.
- Visually inspect saved opening, damage, and capture frames for overlap and
  readability. Reusing caller-supplied axes must not accumulate old artists;
  repeated render/save operations must release owned figures.
- Tests assert overlay semantics/positions rather than fragile image bytes.

---

## Milestone E — Replay and RL handoff

### T15 — Implement versioned replay records and deterministic playback

**Depends on:** T10, T11, T14

**Goal:** Persist an episode as game truth, replay it in a fresh process, and
provide the evidence needed before starting the RL wrapper.

**Work:**

- Define a versioned JSON-compatible record containing schema/ruleset version,
  complete scenario specification (map, units, city, limits), seed, ordered
  actions, emitted events, and terminal outcome. IDs alone are insufficient
  unless a versioned scenario registry is guaranteed to retain every fixture.
- Serialize values explicitly; do not pickle `GameState` or use screenshots as
  the source of truth.
- Implement load, replay, verify, and step/seek APIs. For short 20-turn episodes,
  replay from the initial state for seeking; defer checkpoint machinery until
  profiling justifies it. Reject unsupported schema/ruleset versions explicitly.
- Add a small replay driver to print events and render selected frames.
- Record/check a digest or canonical representation of events/final snapshot.
- Run an engine-readiness audit: deterministic reset, complete legal-action
  enumeration, invalid-action guarantee, state isolation, explainable victory/
  loss traces, render-free benchmark measurement, and clean engine dependency
  boundary.

**Acceptance criteria:**

- A victory, defeat, and time-limit replay load in a fresh process and recreate
  identical event sequence/final state.
- The defeat record identifies its melee-only fixture; it is not presented as
  an all-dead outcome from the normal warrior/slinger benchmark.
- Malformed records and records whose actions disagree with stored events or
  final state fail verification with useful errors. A coherently rewritten valid
  record is not detectable tampering; this is consistency checking, not signing.
- Replaying never invokes RL libraries and does not require an interactive GUI.
- The readiness checklist is recorded in project documentation with measured
  baseline step-rate results and any open risks.

**Handoff:** The next backlog begins with Gymnasium observation design, stable
action-index/mask encoding, reward definition, and PPO/MaskablePPO training. It
must consume this engine rather than modify its mechanics.

---

## Deferred-ticket queue

Do not schedule these until T15 is complete and the baseline agent behavior is
understood:

1. Wall-enabled scenario with city ranged attacks.
2. Defensive mobile unit and deterministic opponent behavior.
3. Multi-agent/competing-agent environment.
4. One combat modifier at a time: health, terrain, river, fortification,
   flanking, support, then garrison.
5. Random-map generation and scenario curriculum.
6. Fog of war, more unit types, promotions, multiple cities, production, and
   broader Civilization-inspired systems.
