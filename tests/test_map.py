"""Geometry, static terrain, and river invariants."""

import numpy as np
import pytest

from engine.map import HexMap, hex_distance, offset_to_cube
from engine.types import Feature, Terrain


def test_neighbors_and_distance_on_both_parities_and_edges() -> None:
    game_map = HexMap(5, 5)
    assert game_map.get_neighbors(0, 0) == [(0, 1), (1, 0)]
    assert game_map.get_neighbors(1, 2) == [
        (1, 1),
        (1, 3),
        (0, 3),
        (0, 2),
        (2, 3),
        (2, 2),
    ]
    assert game_map.get_neighbors(2, 2) == [
        (2, 1),
        (2, 3),
        (1, 2),
        (1, 1),
        (3, 2),
        (3, 1),
    ]
    assert len(game_map.get_neighbors(4, 4)) == 3
    for row in range(game_map.height):
        for col in range(game_map.width):
            origin = (row, col)
            assert game_map.distance(origin, origin) == 0
            assert sum(offset_to_cube(*origin)) == 0
            for neighbor in game_map.get_neighbors(*origin):
                assert origin in game_map.get_neighbors(*neighbor)
                assert game_map.distance(origin, neighbor) == 1
                assert hex_distance(origin, neighbor) == 1
            for other_row in range(game_map.height):
                for other_col in range(game_map.width):
                    other = (other_row, other_col)
                    assert game_map.distance(origin, other) == game_map.distance(
                        other, origin
                    )


def test_terrain_features_costs_and_legacy_conversion() -> None:
    game_map = HexMap.from_legacy([[1, 2, 3], [4, 5, 6]])
    expected = [None, 1, 2, 2, 2, None]
    assert [
        game_map.movement_cost((row, col)) for row in range(2) for col in range(3)
    ] == expected
    assert game_map.terrain_at((1, 1)) == Terrain.HILLS
    assert game_map.feature_at((1, 1)) == Feature.WOODS
    assert game_map.get_tile_properties(0, 2) == {
        "terrain_type": Terrain.PLAINS,
        "feature_type": Feature.WOODS,
    }


def test_river_edges_canonical_and_map_freeze() -> None:
    game_map = HexMap(3, 3)
    game_map.add_river((0, 0), (1, 0))
    game_map.add_river((1, 0), (0, 0))
    assert len(game_map.rivers) == 1
    assert game_map.edge_has_river((0, 0), (1, 0))
    assert game_map.edge_has_river((1, 0), (0, 0))
    copy = game_map.terrain
    copy[0, 0] = Terrain.OCEAN
    assert game_map.terrain_at((0, 0)) == Terrain.PLAINS
    game_map.freeze()
    with pytest.raises(RuntimeError, match="frozen"):
        game_map.add_river((0, 1), (1, 1))
    with pytest.raises(RuntimeError, match="frozen"):
        game_map.set_tile((0, 0), Terrain.HILLS)


@pytest.mark.parametrize(
    "construct",
    [
        lambda: HexMap(0, 2),
        lambda: HexMap(2, 2, terrain=[[2]]),
        lambda: HexMap(1, 1, terrain=[[99]]),
        lambda: HexMap(1, 1, features=[[99]]),
        lambda: HexMap(1, 1, terrain=[[Terrain.OCEAN]], features=[[Feature.WOODS]]),
        lambda: HexMap.from_legacy([[2, 2], [2]]),
        lambda: HexMap.from_legacy([[7]]),
    ],
)
def test_invalid_map_data_rejected(construct) -> None:
    with pytest.raises(ValueError):
        construct()


def test_invalid_edits_do_not_change_map() -> None:
    game_map = HexMap(3, 3)
    old_terrain = game_map.terrain
    old_features = game_map.features
    old_rivers = game_map.rivers
    with pytest.raises(ValueError):
        game_map.set_tile((1, 1), Terrain.OCEAN, Feature.WOODS)
    with pytest.raises(ValueError):
        game_map.set_tile((1, 1), Feature.WOODS)
    with pytest.raises(ValueError):
        game_map.add_river((0, 0), (2, 2))
    with pytest.raises(ValueError):
        game_map.edge_has_river((0, 0), (2, 2))
    with pytest.raises(ValueError):
        game_map.get_neighbors(-1, 0)
    assert np.array_equal(game_map.terrain, old_terrain)
    assert np.array_equal(game_map.features, old_features)
    assert game_map.rivers == old_rivers


def test_numpy_arrays_can_construct_a_map() -> None:
    terrain = np.array([[Terrain.PLAINS, Terrain.HILLS]], dtype=np.int8)
    game_map = HexMap(2, 1, terrain=terrain)
    assert game_map.movement_cost((0, 1)) == 2
    terrain[0, 1] = Terrain.OCEAN
    assert game_map.terrain_at((0, 1)) == Terrain.HILLS
