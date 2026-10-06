"""Range-one and range-two line of sight on the static hex map."""

from engine.map import HexMap
from engine.types import Coordinate, Feature, Terrain


def intermediate_tiles(
    game_map: HexMap, source: Coordinate, target: Coordinate
) -> tuple[Coordinate, ...]:
    """Shared neighbors that can form a two-step route between two hexes.

    A range-two shot may use either route when the hex geometry offers two.
    Both endpoint coordinates must be on the map and exactly two hexes apart.
    """
    if game_map.distance(source, target) != 2:
        raise ValueError("intermediate tiles require a range-two target")
    target_neighbors = set(game_map.get_neighbors(*target))
    return tuple(
        neighbor
        for neighbor in game_map.get_neighbors(*source)
        if neighbor in target_neighbors
    )


def has_line_of_sight(game_map: HexMap, source: Coordinate, target: Coordinate) -> bool:
    """Whether a range-one or range-two shot has a clear intermediate hex.

    Adjacent endpoints are always visible. At range two, mountains, woods, and
    hills block an intermediate tile. At least one available two-step route
    must be clear. Endpoint terrain and units do not block. Longer shots are
    outside the initial ruleset and return False.
    """
    distance = game_map.distance(source, target)
    if distance == 1:
        return True
    if distance != 2:
        return False
    return any(
        game_map.terrain_at(tile) not in (Terrain.MOUNTAINS, Terrain.HILLS)
        and game_map.feature_at(tile) != Feature.WOODS
        for tile in intermediate_tiles(game_map, source, target)
    )
