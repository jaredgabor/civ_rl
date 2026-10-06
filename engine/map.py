"""Static odd-row-offset hex map and terrain queries."""

from collections.abc import Iterable
from enum import IntEnum

import numpy as np

from engine.types import Coordinate, Feature, Terrain

LEGACY_TERRAIN: dict[int, tuple[Terrain, Feature]] = {
    1: (Terrain.OCEAN, Feature.NONE),
    2: (Terrain.PLAINS, Feature.NONE),
    3: (Terrain.PLAINS, Feature.WOODS),
    4: (Terrain.HILLS, Feature.NONE),
    5: (Terrain.HILLS, Feature.WOODS),
    6: (Terrain.MOUNTAINS, Feature.NONE),
}


def offset_to_cube(row: int, col: int) -> tuple[int, int, int]:
    """Convert odd-row horizontal offset coordinates to cube coordinates."""
    if type(row) is not int or type(col) is not int:
        raise ValueError("row and col must be integers")
    x = col - (row - (row & 1)) // 2
    z = row
    return x, -x - z, z


def hex_distance(a: Coordinate, b: Coordinate) -> int:
    ac, bc = offset_to_cube(*a), offset_to_cube(*b)
    return max(abs(ac[i] - bc[i]) for i in range(3))


class HexMap:
    """Validated static map; freeze before passing it into a game state."""

    def __init__(
        self,
        width: int,
        height: int,
        terrain: Iterable[Iterable[int]] | None = None,
        features: Iterable[Iterable[int]] | None = None,
        rivers: Iterable[tuple[Coordinate, Coordinate]] = (),
    ) -> None:
        if (
            type(width) is not int
            or type(height) is not int
            or width <= 0
            or height <= 0
        ):
            raise ValueError("map width and height must be positive integers")
        self.width = width
        self.height = height
        self._terrain = self._validated_array(terrain, Terrain, Terrain.PLAINS)
        self._features = self._validated_array(features, Feature, Feature.NONE)
        self._rivers: set[tuple[Coordinate, Coordinate]] = set()
        self._frozen = False
        self.validate()
        for a, b in rivers:
            self.add_river(a, b)

    def _validated_array(self, values, enum_type, default) -> np.ndarray:
        if values is None:
            return np.full((self.height, self.width), int(default), dtype=np.int8)
        rows = [list(row) for row in values]
        if len(rows) != self.height or any(len(row) != self.width for row in rows):
            raise ValueError("map arrays must have shape (height, width)")
        for row in rows:
            for value in row:
                if isinstance(value, IntEnum) and not isinstance(value, enum_type):
                    raise ValueError("map value uses the wrong enum type")
                if not isinstance(value, (int, np.integer)):
                    raise ValueError("map values must be integers of the correct type")
                try:
                    enum_type(value)
                except ValueError as exc:
                    raise ValueError(
                        f"invalid {enum_type.__name__} value: {value}"
                    ) from exc
        return np.array(rows, dtype=np.int8)

    @classmethod
    def from_legacy(cls, legacy: Iterable[Iterable[int]]) -> "HexMap":
        rows = [list(row) for row in legacy]
        if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("legacy map must be rectangular and nonempty")
        try:
            decoded = [[LEGACY_TERRAIN[value] for value in row] for row in rows]
        except KeyError as exc:
            raise ValueError(f"invalid legacy terrain ID: {exc.args[0]}") from exc
        return cls(
            len(rows[0]),
            len(rows),
            terrain=[[int(cell[0]) for cell in row] for row in decoded],
            features=[[int(cell[1]) for cell in row] for row in decoded],
        )

    @property
    def terrain(self) -> np.ndarray:
        """Return a copy; callers cannot mutate map storage through it."""
        return self._terrain.copy()

    @property
    def features(self) -> np.ndarray:
        return self._features.copy()

    @property
    def rivers(self) -> frozenset[tuple[Coordinate, Coordinate]]:
        return frozenset(self._rivers)

    def freeze(self) -> "HexMap":
        self.validate()
        self._frozen = True
        self._terrain.flags.writeable = False
        self._features.flags.writeable = False
        return self

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.height and 0 <= col < self.width

    def _check_coord(self, coord: Coordinate) -> None:
        if (
            not isinstance(coord, tuple)
            or len(coord) != 2
            or any(type(value) is not int for value in coord)
            or not self.in_bounds(*coord)
        ):
            raise ValueError(f"invalid map coordinate: {coord}")

    def get_neighbors(self, row: int, col: int) -> list[Coordinate]:
        self._check_coord((row, col))
        directions = (
            [(0, -1), (0, 1), (-1, 0), (-1, -1), (1, 0), (1, -1)]
            if row % 2 == 0
            else [(0, -1), (0, 1), (-1, 1), (-1, 0), (1, 1), (1, 0)]
        )
        return [
            (row + dr, col + dc)
            for dr, dc in directions
            if self.in_bounds(row + dr, col + dc)
        ]

    def are_neighbors(self, a: Coordinate, b: Coordinate) -> bool:
        self._check_coord(a)
        self._check_coord(b)
        return b in self.get_neighbors(*a)

    def distance(self, a: Coordinate, b: Coordinate) -> int:
        self._check_coord(a)
        self._check_coord(b)
        return hex_distance(a, b)

    def terrain_at(self, coord: Coordinate) -> Terrain:
        self._check_coord(coord)
        return Terrain(int(self._terrain[coord]))

    def feature_at(self, coord: Coordinate) -> Feature:
        self._check_coord(coord)
        return Feature(int(self._features[coord]))

    def get_tile_properties(self, row: int, col: int) -> dict[str, Terrain | Feature]:
        coord = (row, col)
        return {
            "terrain_type": self.terrain_at(coord),
            "feature_type": self.feature_at(coord),
        }

    def set_tile(
        self, coord: Coordinate, terrain: Terrain, feature: Feature = Feature.NONE
    ) -> None:
        if self._frozen:
            raise RuntimeError("cannot edit a frozen map")
        self._check_coord(coord)
        if isinstance(terrain, IntEnum) and not isinstance(terrain, Terrain):
            raise ValueError("terrain uses the wrong enum type")
        if isinstance(feature, IntEnum) and not isinstance(feature, Feature):
            raise ValueError("feature uses the wrong enum type")
        try:
            terrain = Terrain(terrain)
            feature = Feature(feature)
        except ValueError as exc:
            raise ValueError("invalid terrain or feature") from exc
        self._validate_combination(terrain, feature)
        self._terrain[coord] = terrain
        self._features[coord] = feature

    @staticmethod
    def _validate_combination(terrain: Terrain, feature: Feature) -> None:
        if terrain in (Terrain.OCEAN, Terrain.MOUNTAINS) and feature != Feature.NONE:
            raise ValueError("ocean and mountains cannot have woods")

    def validate(self) -> None:
        for row in range(self.height):
            for col in range(self.width):
                self._validate_combination(
                    self.terrain_at((row, col)), self.feature_at((row, col))
                )
        for a, b in self._rivers:
            if not self.are_neighbors(a, b):
                raise ValueError("river endpoints must be adjacent")

    def is_passable(self, coord: Coordinate) -> bool:
        return self.terrain_at(coord) not in (Terrain.OCEAN, Terrain.MOUNTAINS)

    def movement_cost(self, coord: Coordinate) -> int | None:
        """Entry cost, or None for an impassable tile."""
        if not self.is_passable(coord):
            return None
        return (
            2
            if (
                self.terrain_at(coord) == Terrain.HILLS
                or self.feature_at(coord) == Feature.WOODS
            )
            else 1
        )

    @staticmethod
    def _edge(a: Coordinate, b: Coordinate) -> tuple[Coordinate, Coordinate]:
        return tuple(sorted((a, b)))

    def add_river(self, a: Coordinate, b: Coordinate) -> None:
        if self._frozen:
            raise RuntimeError("cannot edit a frozen map")
        if not self.are_neighbors(a, b):
            raise ValueError("river endpoints must be adjacent")
        self._rivers.add(self._edge(a, b))

    def edge_has_river(self, a: Coordinate, b: Coordinate) -> bool:
        if not self.are_neighbors(a, b):
            raise ValueError("river query requires neighboring tiles")
        return self._edge(a, b) in self._rivers
