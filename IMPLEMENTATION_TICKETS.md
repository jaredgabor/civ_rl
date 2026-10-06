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
- **Test rule:** run `uv run pytest` and `uv run ruff check .` for every ticket.
- **Commit rule:** keep functional code and its tests in the same ticket/commit
  where practical. Do not commit `.venv`, cache directories, or generated
  frames.

## Dependency map

```text
T01 -> T02 -> T03 -> T04 -> T05 -> T06 -> T07 -> T08 -> T09
                                              |                  |
                                              +--> T10 -> T11 ---+
                                                                 |
                                         T08 -> T12 -> T13 ------+
                                                                 v
                                                            T14 -> T15
```

`T01`–`T09` make the deterministic benchmark playable. `T10`–`T11` make it
inspectable without a graphical UI. `T12`–`T13` add graphical rendering;
`T14`–`T15` establish replay and the handoff boundary for the later RL work.

---

## Milestone A — Foundation and static world

### T01 — Establish project, packages, and test harness

**Depends on:** none

**Goal:** Turn the prototype directory into a consistently testable Python
project without changing game behavior.

**Work:**

- Add `engine/__init__.py` and a `tests/` package/layout.
- Add a project `.gitignore` for virtual environments, Python bytecode,
  notebook checkpoints, tool caches, and generated render/replay artifacts.
- Configure pytest and Ruff in `pyproject.toml`; define an explicit test command
  and formatting/linting policy.
- Add only the development dependencies actually used by the repository.
- Create a short mechanics/readme pointer explaining that the existing modules
  are being replaced behind tested APIs.
- Add a smoke test proving imports work through the package, not from a notebook
  working directory.

**Acceptance criteria:**

- `uv run pytest` discovers and passes at least one test.
- `uv run ruff check .` passes.
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
  city HP 100, city defense strength 25, wall HP 100, healing rules, and turn
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
  woods/hills have the agreed cost; combined feature/terrain costs are explicit.
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
- Apply the v1 blockers: mountains always block; woods and hills use the agreed
  line-of-sight behavior from the final plan.
- Expose a pure `has_line_of_sight(map, source, target)` query.
- Document every intentional simplification (for example, no unit blocking).

**Acceptance criteria:**

- All range-1 targets have line of sight unless an explicitly documented rule
  forbids it.
- Tests cover every range-2 direction on both row parities.
- Tests distinguish clear, mountain-blocked, woods-blocked, hills-blocked, and
  out-of-range targets.
- The function has no dependency on `GameState`, renderer, or RL code.

**Decision note:** If the exact woods/hills rule is still ambiguous while writing
this ticket, define it in the mechanics reference and lock it with tests before
continuing. Do not make attack legality depend on an unstated rule.

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
- Implement `CityStates` arrays for stable ID, owner, position, city/current
  HP, optional wall/current HP, and optional garrison reference.
- Provide validated `spawn`, `kill`, `begin_turn`, damage/heal, lookup, and
  read-only view/snapshot helpers.
- Ensure a default city has zero walls and no independent ranged action.
- Preserve dead records for replay but make them non-occupying/non-targetable.

**Acceptance criteria:**

- IDs remain stable after deaths and later spawns.
- HP always remains an integer in `[0, max_hp]`.
- A missing garrison can never cause a unit-type lookup with a sentinel index.
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
  unique, city positions unique, valid owners/types, HP bounds, garrison validity,
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
- Define immutable event records for attempted/rejected action context, move,
  damage, death, healing, turn advance, capture, and terminal outcome.
- Implement pure legal-target and legal-action enumeration for the active owner,
  including live state, ownership, movement/action flags, range, and LoS.
- Define a structured invalid-action error/result but do not mutate state on it.
- Make legal-action output deterministic in ordering so it can later map to a
  stable action mask.

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
- Apply ordinary destination movement cost.
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
- Include optional wall-first damage and wall-enabled city-attack hooks behind
  rules/scenario capability flags, but do not enable them in the benchmark.

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
- On the passive city's turn, apply city/wall healing and advance automatically;
  do not expose a city action in the initial scenario.
- End episodes on capture, every attacking unit dead, or the 20-turn limit.
- Emit events in an unambiguous sequence, including end/start turn, healing,
  terminal outcome, and the parent action identifier.

**Acceptance criteria:**

- A scripted episode runs to each terminal path: capture, all attackers dead,
  and time limit.
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
- Hand-author the exact 6x6 terrain, woods/hills/mountains/ocean, river edge(s),
  city coordinate, and attacker locations.
- Validate that the scenario is solvable under the fixed rules and has no
  unintended shortcuts.
- Add short named scripted traces for victory, defeat, and time-limit outcomes.
- Add a tiny deterministic heuristic driver for manual/demo use; it is not an
  opponent AI or an RL policy.

**Acceptance criteria:**

- Resetting with the same seed recreates exactly the same state.
- Golden traces have committed expected action/event summaries and final states.
- The scenario exercises at least one river crossing, terrain movement penalty,
  line-of-sight decision, melee retaliation, ranged damage, healing, and capture.
- A test demonstrates each terminal outcome without rendering.

---

## Milestone D — Human debugging and visualization

### T12 — Add text logging and a scriptable headless driver

**Depends on:** T10, T11

**Goal:** Make every episode understandable in a terminal before adding graphics.

**Work:**

- Provide a concise state/event formatter with coordinates, unit type/owner/HP,
  city HP, movement left, turn, and terminal state.
- Add a command/script entry point that runs a supplied action trace or the
  deterministic heuristic against the initial scenario.
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

---

### T14 — Add debug HUD and RGB-array render mode

**Depends on:** T12, T13

**Goal:** Make frames useful for tactical inspection and ready for the later
Gymnasium rendering interface, without importing Gymnasium.

**Work:**

- Add HUD fields: turn, active side, city/wall HP, terminal status, last action,
  event summary, and selected/active unit state where applicable.
- Add `render_snapshot(snapshot, ax=None)` and a non-blocking RGB-array method.
- Add explicit PNG-frame saving with caller-supplied paths; do not save or show
  by default.
- Represent wall/city capabilities accurately: a no-wall city has no wall bar
  and no city-shot annotation.

**Acceptance criteria:**

- A user can visually distinguish opening, movement, damage, healing, death,
  capture, and terminal frames.
- RGB output is a deterministic `uint8` array with documented shape/channel
  order.
- Tests assert overlay semantics/positions rather than fragile image bytes.

---

## Milestone E — Replay and RL handoff

### T15 — Implement versioned replay records and deterministic playback

**Depends on:** T10, T11, T14

**Goal:** Persist an episode as game truth, replay it in a fresh process, and
provide the evidence needed before starting the RL wrapper.

**Work:**

- Define a versioned JSON-compatible record containing ruleset/scenario ID,
  seed, ordered typed actions, emitted events, terminal outcome, and optional
  checkpoints.
- Serialize values explicitly; do not pickle `GameState` or use screenshots as
  the source of truth.
- Implement load, replay, verify, and seek (using periodic checkpoints if
  needed) APIs.
- Add a small replay driver to print events and render selected frames.
- Record/check a digest or canonical representation of events/final snapshot.
- Run an engine-readiness audit: deterministic reset, complete legal-action
  enumeration, invalid-action guarantee, state isolation, explainable victory/
  loss traces, render-free benchmark measurement, and clean engine dependency
  boundary.

**Acceptance criteria:**

- A victory, defeat, and time-limit replay load in a fresh process and recreate
  identical event sequence/final state.
- A modified/corrupt record fails verification with a useful error.
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
