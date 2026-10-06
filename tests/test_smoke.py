"""Verify package imports work from the project root."""

from engine.map import HexMap
from render.map_renderer import HexMapRenderer


def test_engine_and_renderer_import() -> None:
    game_map = HexMap(2, 2)
    renderer = HexMapRenderer()
    assert game_map.get_neighbors(0, 0) == [(0, 1), (1, 0)]
    assert renderer.tile_center(0, 0) == (0.0, 0.0)
