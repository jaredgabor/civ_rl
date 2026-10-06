"""Immutable definitions for the initial tactical ruleset."""

import math
from dataclasses import dataclass

from engine.types import UnitKind


@dataclass(frozen=True, slots=True)
class UnitType:
    kind: UnitKind
    name: str
    max_hp: int
    melee_strength: int
    ranged_strength: int
    attack_range: int
    movement: int
    can_capture_city: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, UnitKind):
            raise ValueError("kind must be a UnitKind")
        if not self.name:
            raise ValueError("unit name must not be empty")
        for name in ("max_hp", "melee_strength", "movement"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.ranged_strength) is not int or self.ranged_strength < 0:
            raise ValueError("ranged_strength must be a nonnegative integer")
        if type(self.attack_range) is not int or self.attack_range not in (0, 1, 2):
            raise ValueError("attack_range must be 0, 1, or 2")
        if (self.attack_range == 0) != (self.ranged_strength == 0):
            raise ValueError("ranged strength and attack range must both be set")
        if type(self.can_capture_city) is not bool:
            raise ValueError("can_capture_city must be boolean")
        if self.can_capture_city and self.attack_range != 0:
            raise ValueError("ranged units cannot capture cities")


@dataclass(frozen=True, slots=True)
class Ruleset:
    unit_types: tuple[UnitType, ...]
    city_max_hp: int = 100
    city_strength: int = 25
    unit_heal: int = 10
    city_heal: int = 10
    turn_limit: int = 20
    river_surcharge: int = 2
    min_movement_to_attack: int = 1
    base_damage: float = 30.0
    damage_curvature: float = 25.0
    max_strength_delta: float = 40.0

    def __post_init__(self) -> None:
        if type(self.unit_types) is not tuple or not self.unit_types:
            raise ValueError("unit_types must be a nonempty tuple")
        if any(not isinstance(unit, UnitType) for unit in self.unit_types):
            raise ValueError("unit_types must contain UnitType values")
        kinds = [unit.kind for unit in self.unit_types]
        if len(kinds) != len(set(kinds)):
            raise ValueError("unit kinds must be unique")
        for name in (
            "city_max_hp",
            "city_strength",
            "turn_limit",
            "min_movement_to_attack",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("unit_heal", "city_heal", "river_surcharge"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("base_damage", "damage_curvature", "max_strength_delta"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a positive finite number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite number")

    def unit(self, kind: UnitKind) -> UnitType:
        for unit_type in self.unit_types:
            if unit_type.kind == kind:
                return unit_type
        raise KeyError(kind)


STANDARD_RULES = Ruleset(
    unit_types=(
        UnitType(UnitKind.WARRIOR, "Warrior", 100, 20, 0, 0, 2, True),
        UnitType(UnitKind.SLINGER, "Slinger", 80, 5, 15, 1, 2, False),
        UnitType(UnitKind.ARCHER, "Archer", 100, 15, 25, 2, 2, False),
    )
)
