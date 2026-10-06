"""Fixed ruleset contract and validation tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from engine.rules import STANDARD_RULES, UnitType
from engine.types import ActionKind, Feature, Outcome, Owner, Terrain, UnitKind


def test_standard_rules_match_initial_design() -> None:
    rules = STANDARD_RULES
    assert (rules.city_max_hp, rules.city_strength, rules.turn_limit) == (100, 25, 20)
    assert (rules.base_damage, rules.damage_curvature, rules.max_strength_delta) == (
        30,
        25,
        40,
    )
    assert (rules.unit_heal, rules.city_heal) == (10, 10)
    assert (rules.river_surcharge, rules.min_movement_to_attack) == (2, 1)
    assert rules.unit(UnitKind.WARRIOR) == UnitType(
        UnitKind.WARRIOR, "Warrior", 100, 20, 0, 0, 2, True
    )
    assert rules.unit(UnitKind.SLINGER) == UnitType(
        UnitKind.SLINGER, "Slinger", 80, 5, 15, 1, 2, False
    )
    assert rules.unit(UnitKind.ARCHER) == UnitType(
        UnitKind.ARCHER, "Archer", 100, 15, 25, 2, 2, False
    )
    assert (Owner.ATTACKER, Terrain.HILLS, Feature.WOODS) == (1, 3, 1)
    assert (ActionKind.END_TURN.value, Outcome.TURN_LIMIT.value) == (
        "end_turn",
        "turn_limit",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_hp", 0),
        ("melee_strength", -1),
        ("movement", 0),
        ("ranged_strength", -1),
        ("attack_range", 3),
    ],
)
def test_invalid_unit_values(field: str, value: int) -> None:
    with pytest.raises(ValueError, match=field):
        replace(STANDARD_RULES.unit(UnitKind.WARRIOR), **{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("city_max_hp", 0),
        ("city_strength", 0),
        ("turn_limit", 0),
        ("unit_heal", -1),
        ("base_damage", float("inf")),
        ("damage_curvature", 0),
        ("max_strength_delta", -1),
    ],
)
def test_invalid_ruleset_values(field: str, value: int | float) -> None:
    with pytest.raises(ValueError, match=field):
        replace(STANDARD_RULES, **{field: value})


def test_ruleset_is_immutable_and_kinds_are_unique() -> None:
    with pytest.raises(FrozenInstanceError):
        STANDARD_RULES.city_max_hp = 101  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        STANDARD_RULES.unit(UnitKind.WARRIOR).max_hp = 101  # type: ignore[misc]
    with pytest.raises(ValueError, match="unique"):
        replace(STANDARD_RULES, unit_types=(STANDARD_RULES.unit_types[0],) * 2)
    with pytest.raises(KeyError):
        STANDARD_RULES.unit(99)
