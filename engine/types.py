"""Small, stable identifiers shared by engine components."""

from enum import Enum, IntEnum
from typing import TypeAlias

Coordinate: TypeAlias = tuple[int, int]  # (row, col), odd-row horizontal offset


class Owner(IntEnum):
    ATTACKER = 1
    DEFENDER = 2


class Terrain(IntEnum):
    OCEAN = 1
    PLAINS = 2
    HILLS = 3
    MOUNTAINS = 4


class Feature(IntEnum):
    NONE = 0
    WOODS = 1


class UnitKind(IntEnum):
    WARRIOR = 1
    SLINGER = 2
    ARCHER = 3


class TargetKind(str, Enum):
    UNIT = "unit"
    CITY = "city"


class Outcome(str, Enum):
    CITY_CAPTURED = "city_captured"
    ATTACKERS_DESTROYED = "attackers_destroyed"
    TURN_LIMIT = "turn_limit"


class ActionKind(str, Enum):
    MOVE = "move"
    MELEE_ATTACK = "melee_attack"
    RANGED_ATTACK = "ranged_attack"
    END_TURN = "end_turn"


class EventKind(str, Enum):
    MOVED = "moved"
    DAMAGED = "damaged"
    DIED = "died"
    HEALED = "healed"
    TURN_ADVANCED = "turn_advanced"
    CAPTURED = "captured"
    TERMINATED = "terminated"
