"""Line-of-sight behavior for each range-two direction and row parity."""

import pytest

from engine.map import HexMap
from engine.types import Feature, Terrain
from engine.visibility import has_line_of_sight, intermediate_tiles


@pytest.mark.parametrize("source", [(4, 4), (5, 4)])
def test_every_range_two_target_with_clear_and_blocked_paths(source) -> None:
    game_map = HexMap(10, 10)
    targets = [
        (row, col)
        for row in range(10)
        for col in range(10)
        if game_map.distance(source, (row, col)) == 2
    ]
    assert len(targets) == 12
    for target in targets:
        intermediates = intermediate_tiles(game_map, source, target)
        assert 1 <= len(intermediates) <= 2
        assert has_line_of_sight(game_map, source, target)
        for intermediate in intermediates:
            game_map.set_tile(intermediate, Terrain.MOUNTAINS)
        assert not has_line_of_sight(game_map, source, target)
        game_map.set_tile(intermediates[0], Terrain.PLAINS)
        assert has_line_of_sight(game_map, source, target)
        for intermediate in intermediates:
            game_map.set_tile(intermediate, Terrain.PLAINS)


@pytest.mark.parametrize(
    ("terrain", "feature"),
    [
        (Terrain.MOUNTAINS, Feature.NONE),
        (Terrain.PLAINS, Feature.WOODS),
        (Terrain.HILLS, Feature.NONE),
        (Terrain.HILLS, Feature.WOODS),
    ],
)
def test_each_blocker_type(terrain: Terrain, feature: Feature) -> None:
    game_map = HexMap(8, 8)
    source, target = (3, 3), (5, 3)
    intermediates = intermediate_tiles(game_map, source, target)
    for tile in intermediates:
        game_map.set_tile(tile, terrain, feature)
    assert not has_line_of_sight(game_map, source, target)


def test_endpoints_adjacent_distance_and_bounds() -> None:
    game_map = HexMap(6, 6)
    source, target = (2, 2), (2, 3)
    game_map.set_tile(target, Terrain.HILLS, Feature.WOODS)
    assert has_line_of_sight(game_map, source, target)
    assert not has_line_of_sight(game_map, source, source)
    assert not has_line_of_sight(game_map, (0, 0), (5, 5))
    with pytest.raises(ValueError, match="range-two"):
        intermediate_tiles(game_map, source, target)
    with pytest.raises(ValueError, match="coordinate"):
        has_line_of_sight(game_map, source, (8, 8))
