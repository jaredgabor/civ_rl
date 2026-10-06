# Civ-RL Engine and Rendering Plan

Reconciled with the current v1 scope. The detailed implementation order is in
[IMPLEMENTATION_TICKETS.md](IMPLEMENTATION_TICKETS.md).

## Goal and boundary

Build a deterministic, testable, Civ-inspired tactical-siege simulator from the
existing prototype. The first result is a small playable scenario with a
debug renderer and replay, not a full Civilization clone. Gymnasium and PPO
will be added later as separate consumers of the engine.

The engine must be fast to iterate on, clear enough to explain every tactical
outcome, and reproducible from a scenario plus seed.

## Current repository assessment

The current code establishes several valuable choices:

- `engine/map.py` uses odd-row horizontal offset hex coordinates, NumPy terrain
  storage, neighbor lookup, and canonical river edges.
- `engine/combat.py` has the desired capped exponential damage curve.
- `engine/units.py` and `engine/cities.py` point toward centralized,
  array-backed mutable state.
- `render/map_renderer.py` already renders compatible pointy-top geometry,
  terrain, river edges, basic unit markers, cities, and coordinate labels.

It is a prototype rather than a simulation today. Missing pieces include a game
state, scenarios, entity lifecycle APIs, occupancy checks, turns, legal actions,
combat/city resolution, an executable project definition, and tests. Several
partial methods reference missing helpers; city positions have two sources of
truth; and the renderer consumes ad-hoc dictionaries instead of game state.
The plan retains the good primitives but establishes stable contracts before
adding mechanics.

## Design rules

1. **Engine is RL-agnostic.** It imports neither Gymnasium nor Stable-Baselines.
2. **Static and dynamic data are separate.** Map owns terrain/features/rivers;
   entity containers own changing state.
3. **One source of truth.** Live unit occupancy derives from unit state; cities
   are represented only by city state, not duplicated on the map.
4. **Stable episode-local IDs.** Dead units retain their slot for debugging and
   replay but cease to occupy a tile.
5. **One mutation gateway.** Only the game/action resolver changes state. The
   renderer and later environment receive snapshots/views.
6. **Rules are centralized.** Use one fixed, versioned ruleset; no tuning framework
   is required. Scenarios contain layout and starting entities.
7. **Events are first-class.** Every successful transition reports an immutable
   movement/combat/turn/capture event used by tests, logging, and replay.

## Target architecture

```text
engine/
  __init__.py
  types.py          # Coordinate, owner, action, target, event value types
  rules.py          # Immutable ruleset and unit-type definitions
  map.py            # HexMap, features, coordinate conversion, rivers
  units.py          # Array-backed UnitStates and lifecycle APIs
  cities.py         # Array-backed CityStates and lifecycle APIs
  state.py          # GameState and invariant validation
  actions.py        # Typed actions and legal-action enumeration
  movement.py       # Path/occupancy/movement-cost checks
  combat.py         # Pure calculations and stateful combat resolution
  scenarios.py      # Fixed scenario schema and factory
  game.py           # Public state-transition facade and turn loop
  serialization.py  # Versioned snapshots/events for replay

render/
  scene.py          # Read-only state snapshot -> rendering records
  map_renderer.py   # Matplotlib map/drawing primitives
  debug_renderer.py # HUD, annotated frame, RGB-array output
  replay.py         # Episode load, stepping, frame/animation export

tests/
  test_map.py, test_entities.py, test_actions.py, test_combat.py,
  test_game.py, test_render.py, test_replay.py
```

The names may change, but not the ownership boundaries. `Game` is the sole
public gameplay facade: `reset`, `legal_actions`, `apply`, `end_turn`, and
`snapshot` (final names depend on the action decision).

## Data and API contracts

### Map and coordinates

Keep `(row, col)` odd-row offset coordinates publicly and in arrays, since they
match existing map and renderer code. Centralize offset-to-cube conversion, hex
distance, and range helpers so parity math is never copied by callers.

`HexMap` exposes validated, read-only queries: bounds, neighbors, distance,
terrain/feature, passability, movement cost, add/query river edge. Rivers remain
canonical immutable tile-pairs. It owns no unit or city data. The first map is
hand-authored; procedural terrain remains a later experiment. Construction may
use a builder or validated mutations; freeze the map before gameplay.

### Rules, units, cities, and game state

Define immutable `UnitType` records (name, HP, melee/ranged strength, range,
movement, tags such as city-capture capability) and one validated `Ruleset`.

Finish `UnitStates` as centralized arrays for alive, owner, type, position, HP,
movement remaining, and per-turn action flags, with `spawn`, `kill`,
`begin_turn`, and safe lookup helpers. `CityStates` holds alive, owner, position,
current/max city HP. Wall and garrison state belongs to later extensions.
A zero-HP city persists until capture; it is not removed like a dead unit.

`GameState` owns map, entity states, active side, turn, turn limit, terminal
outcome, seeded RNG, and last action/event. It supports immutable snapshots or
deep copies. `validate()` checks positions, unique occupancy, HP bounds, valid
types/owners, and terminal-state consistency.

### Actions, legality, and events

Develop the engine with readable typed actions:

```text
Move(unit_id, destination)
MeleeAttack(unit_id, target_kind, target_id)
RangedAttack(unit_id, target_kind, target_id)
EndTurn(side)
```

`legal_actions()` is the sole source of legitimacy. `apply()` rejects an
illegal action without mutation. A successful action returns an event with
enough before/after data to explain movement, damage, death, capture, turn
progress, and terminal outcome. The future Gym wrapper alone translates these
to a discrete encoding and action mask.

## Initial vertical slice

- Fixed 6x6 fully visible hand-authored map with a demonstrated winning trace.
  A river and varied terrain are optional in the first benchmark; mechanics
  fixtures cover them independently.
- One attacker-controlled side: two warriors plus one slinger. The defender is
  an ungarrisoned, wall-less, passive city with no mobile units and no ranged
  attack. This deliberately makes the first RL problem single-agent.
- One unit per tile; woods/hills cost extra movement and affect line of sight.
  Mountains and ocean are impassable. There are no combat modifiers in v1:
  terrain and river geometry influence movement/visibility, not strength.
- A side sequentially acts with eligible units and explicitly ends its turn.
  Units may take multiple moves up to their allowance and one attack per turn.
- Melee attacks adjacent targets and receives retaliation. Ranged attacks a
  valid target in range and does not receive retaliation.
- Use the existing capped exponential damage curve. Resolve each hit using one
  documented deterministic integer-rounding rule and store integer HP.
- City capture requires an eligible melee unit once city HP reaches zero. The
  initial city heals 10 HP at the end of its turn; a unit heals 10 HP only on a
  turn in which it neither moved nor attacked.
- Walls and city ranged attacks are supported by a subsequent engine scenario,
  not required to establish the first trainable environment. A city defaults to
  no walls; only a city with walls may take a ranged attack.
- Terminal outcomes are city captured, all attackers destroyed, or a turn cap.

This is enough to observe positioning, survival, focus fire, and the separate
roles of ranged and melee units before adding an opponent AI or random maps.

## Phased implementation backlog

### 0. Contracts and project foundation

1. Add project metadata, supported Python version, dependency groups, formatter,
   linter, and test command.
2. Add package/test layout and concise mechanics reference.
3. Freeze a versioned initial scenario (terrain/features/rivers, city, units,
   owners, turn limit, seed).
4. Establish small test fixtures; freeze winning/losing benchmark traces after
   the engine exists (T11), rather than guessing results before implementation.

Exit: clean setup and a basic test command work in a fresh environment.

### 1. Map and static rules

1. Normalize terrain versus feature identifiers, passability, movement-cost
   lookup, and compatibility palette.
2. Centralize/test neighbor parity, canonical river edges, offset/cube conversion,
   distance, and range candidates.
3. Make construction validate coordinates, terrain values, river adjacency, and
   scenario placements.
4. Move combat constants into a validated immutable ruleset.

Exit: map/rule tests cover both parities, corners, and invalid data.

### 2. Entity lifecycle and invariants

1. Complete arrays and lifecycle APIs in `UnitStates` and `CityStates`.
2. Add stable IDs, max HP, owner enums, and read-only
   entity/snapshot views for debugging.
3. Implement `GameState.validate()` and eliminate duplicate city-location state.
4. Remove incomplete helpers and undefined partial behavior from prototype code.

Exit: spawn, kill, copy, and begin-turn sequences preserve all invariants.

### 3. Movement, combat, city, and turn resolver

1. Implement movement legality: adjacency/path rule, bounds, passability,
   occupancy, remaining movement, and river behavior.
2. Implement attack target discovery/validation: ownership, range, line of
   sight, target life state, and one-attack-per-turn rule.
3. Keep strength/damage calculation pure; implement a resolver for retaliation,
   HP clamping, death, and events.
4. Implement v1 capture, turn reset/advance, idle-unit/city healing, and terminal
   resolution. Walls, garrisons, city shots, and unit-to-unit combat are deferred.
5. Expose everything through `Game`, validating after changes in debug mode.

Exit: the golden trace has exact state/event results; rejected actions leave a
byte-equivalent logical snapshot unchanged; every terminal outcome is tested.

### 4. Scenario driver and deterministic baseline

1. Implement `make_initial_siege()` plus a scriptable, human-readable driver.
2. Support deterministic resets from scenario plus seed even before randomness.
3. Use a verified scripted trace as the demonstration driver; a general heuristic
   is optional later work.
4. Keep victory and timeout traces for the benchmark and an all-dead trace in a
   separate melee-only fixture: a passive city cannot kill ranged attackers.

Exit: a deterministic siege can run start-to-finish without Gymnasium.

### 5. Debug renderer

1. Add a read-only scene adapter from game snapshot to renderer records.
2. Keep Matplotlib as first backend: terrain, river edges, coordinate labels in
   debug mode, city health, unit owner/type glyph, HP, movement, active
   side/turn, status, and last event.
3. Reuse engine coordinate geometry; remove renderer stdout debugging and
   dictionary-only rendering contract.
4. Support `render_snapshot(snapshot, ax=None)` and a non-blocking RGB-array
   path for later Gym `human`/`rgb_array` render modes.
5. Add headless saved-PNG smoke tests and semantic overlay/position tests.

Exit: every eventful transition of the fixed siege renders correctly and render
calls cannot mutate the game snapshot.

### 6. Replay and debugging workflow

1. Define a versioned record: complete scenario specification, ruleset/schema
   version, seed, actions, events, optional future rewards, and terminal result.
2. Reconstruct from actions and verify events/final state on playback. Reject
   unsupported versions. This checks consistency, not cryptographic authenticity.
3. Implement replay step/seek by replaying from reset for short episodes;
   add annotations and frame saving. Checkpoints and animation export wait.
4. Test that a fresh replay produces the same final snapshot and event sequence.

Exit: victory, defeat, and turn-limit episodes are reproducible and inspectable.

### 7. Readiness gate for the later RL wrapper

Before PPO, verify deterministic reset, complete legal action enumeration,
documented invalid-action policy, independent copying/serialization/rendering,
explainable win/loss fixtures, a winning scripted baseline, and a measured
render-free step rate. Then add Gymnasium observation, action encoding/masking,
reward, and termination/truncation policy outside the engine.

## Test strategy

- **Map:** parity/corner neighbors, symmetry, distances, river canonicalization,
  terrain passability, invalid input.
- **Entities:** lifecycle, stable IDs, max/current HP, array
  copying, and state invariants.
- **Combat:** curve properties/cap/rounding, retaliation, death, zero-HP city,
  melee-only capture, HP endpoints.
- **Actions:** movement cost/occupancy, range/LoS, per-turn flags, no mutation
  after rejection, and turn reset.
- **Integration:** golden win/loss/time-limit traces and deterministic replay.
- **Rendering:** no mutation, coordinate-to-center mapping, headless frame save,
  and overlays matching live state/events.

Start with deterministic examples. Add property-based map/action invariant tests
later, when the exact contracts are stable.

## Rendering and replay policy

The first renderer is a debug instrument, not a full UI:

- Matplotlib/Agg works in notebooks, local inspection, CI, and PNG output.
- Layer order: terrain; rivers; optional coordinates; cities/walls; units;
  selected/active overlays; HUD/event log.
- Color expresses owner, a glyph/letter unit type, and text/short bar HP; no
  essential information relies only on color.
- The HUD makes turn, side, status, action, damage/death/capture, and movement
  clear at a glance.
- Render methods return a figure/axes for people or RGB pixels for the later
  environment and never block/show by default.
- Replay records game truth (actions/events), while visual frames are generated
  on demand. An ASCII formatter is an optional CI/debug companion.

## Final ruleset decisions

- Approved v1 movement: plains cost 1; woods and hills cost 2; wooded hills
  also cost 2. Mountains and ocean are impassable.
- Approved v1 visibility: adjacent targets are visible. At range 2, a shot is
  legal if at least one shared intermediate hex is free of mountains, woods,
  and hills. Endpoints and units do not block.
- Approved attack budget: at least 1 movement point is required to attack;
  the attack uses the remaining movement and the unit's one attack allowance.
- Approved capture sequence: calculate city damage and retaliation from the
  pre-attack state; apply them together. A melee attacker captures on reaching
  zero city HP only if it survives. A zero-HP uncaptured city remains on the
  map and can heal; moving into an enemy city is otherwise illegal.

- The first RL scenario is single-agent: two warriors and one slinger attack an
  ungarrisoned, wall-less, passive city. It has no city ranged attack. This is
  intentionally simpler than a competing-agent or defended-city environment.
- The engine remains owner-aware so a later scenario can add defenders and a
  competing agent without a state-model rewrite.
- City HP is 100 and its fixed defensive strength is 25. For a later extension,
  optional walls have 100 HP, absorb damage before city HP, and enable a city
  ranged attack. The
  default city has no walls. A melee unit alone can capture a city after city
  HP reaches zero by entering its tile.
- Melee attacks receive city retaliation; ranged attacks do not. A passive city
  has no independent action. The city heals 10 HP at the end of its turn; a
  wall heals 10 HP under the same policy when walls are enabled. A unit heals
  10 HP only after a turn in which it neither moved nor attacked.
- V1 includes no health, terrain, river, fortification, flanking, support, or
  garrison combat-strength modifiers. Map terrain and river edges still matter
  through movement and line of sight.
- Woods and hills have movement penalties and line-of-sight behavior;
  mountains and ocean are impassable.
- A unit can move multiple times and then attack if it has movement remaining.
  On a river crossing, calculate the normal destination cost plus the river
  surcharge. If the unit begins that move with its full base movement, permit
  the crossing even when this cost exceeds its remaining movement, then set
  movement remaining to zero. Otherwise require sufficient movement. This
  applies the user's specified early-unit behavior: a fresh 2-movement unit can
  cross a river as its only move that turn. The Civ VI manual confirms river crossings
  consume 3 movement points; this project uses the specified special-case rule
  rather than reproducing every surrounding movement detail. See the
  [Civ VI 25th Anniversary Online Manual](https://shared.steamstatic.com/store_item_assets/steam/apps/289070/manuals/CIV_VI_25TH_ONLINE_MANUAL_ENG.pdf?t=1740607040).
- Use sequential unit actions then `EndTurn`, integer HP, deterministic setup
  and damage with recorded seeds, a 20-turn cap, win by capture, and loss on
  all attackers dead or the turn limit.
- The engine rejects illegal actions without mutation. The future RL wrapper
  exposes a legal-action mask by default.
- Use Matplotlib for the first renderer; save JSON action/event replays and PNG
  frames. uv, the Python pin, and dev tools are installed. T01 adds repository
  test/lint configuration; setup should not be repeated.

## Deferred complexity

After a single agent reliably captures the passive city, add one factor at a
time: walls/city ranged attack, a defender, a second controlled side, and then
combat modifiers. Each addition gets a new fixed scenario, regression traces,
and its own training experiment rather than changing the original benchmark.
