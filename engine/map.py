import numpy as np


terrain_types = {
    1: "OCEAN",
    2: "PLAINS",
    3: "PLAINS-WOODS",
    4: "HILLS",
    5: "HILLS-WOODS",
    6: "MOUNTAINS",
}


class HexMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.terrain = np.zeros((height, width), dtype=np.int8)
        self.city_positions = set()
        self.rivers = set()

    def in_bounds(self, row, col):
        '''
        Determine if a given coordinate is in-bounds for the map

        :param self: Description
        :param row: Description
        :param col: Description
        :return: Description
        :rtype: Any
        '''
        return 0 <= row < self.height and 0 <= col < self.width

    def get_neighbors(self, row, col):
        '''
        return a list of neighboring tile coordinates

        :param self: Description
        :param row: Description
        :param col: Description
        '''
        nbrs = []
        r = row
        c = col
        if row % 2 == 0:
            nbrs = [
                (r, c - 1),
                (r, c + 1),
                (r - 1, c),
                (r - 1, c - 1),
                (r + 1, c),
                (r + 1, c - 1),
            ]
        else:
            nbrs = [
                (r, c - 1),
                (r, c + 1),
                (r - 1, c + 1),
                (r - 1, c),
                (r + 1, c + 1),
                (r + 1, c),
            ]

        # Remove proposed neighbor tiles that are out of bounds
        neighbors = [tile_coord for tile_coord in nbrs if self.in_bounds(*tile_coord)]
        return neighbors

    def are_neighbors(self, a, b):
        '''
        Determine whether two tiles are adjacent/neighbors.

        :param self: Description
        :param a: Tuple denoting the coordinates of tile A
        :param b: Tuple denoting the coordinates of tile B
        '''
        return b in self.get_neighbors(*a)

    def get_tile_properties(self, row, col):
        if not self.in_bounds(row, col):
            raise ValueError(f"({row}, {col}) is out of bounds")
        properties = {
            'terrain_type': self.terrain[row, col]
        }
        return properties

    def add_river(self, a, b):
        if not self.are_neighbors(a, b):
            raise ValueError("River must border adjacent tiles")
        edge = tuple(sorted([a, b]))
        self.rivers.add(edge)

    def edge_has_river(self, a, b):
        '''
        Determine whether an edge shared between 2 tiles has a river.

        :param self: Description
        :param a: Description
        :param b: Description
        '''
        return tuple(sorted([a, b])) in self.rivers

    def generate_random_terrain(
        self,
        base_weights=None,
        cluster_strength=0.7,
        seed=None,
    ):
        '''
        Generate terrain for every tile with local clustering in one pass.

        Each tile is assigned exactly one terrain type. Terrain selection
        combines global base weights with already-assigned neighbor terrain.

        :param base_weights: Optional dict[int, float]
        :param cluster_strength: Blend factor in [0, 1] favoring neighbor terrain
        :param seed: Optional RNG seed for reproducibility
        '''
        if not 0 <= cluster_strength <= 1:
            raise ValueError("cluster_strength must be between 0 and 1")

        rng = np.random.default_rng(seed)
        terrain_ids = np.array(sorted(terrain_types.keys()), dtype=np.int8)
        terrain_index = {terrain_id: idx for idx, terrain_id in enumerate(terrain_ids)}

        default_weights = {
            1: 0.30,  # OCEAN
            2: 0.25,  # PLAINS
            3: 0.15,  # PLAINS-WOODS
            4: 0.15,  # HILLS
            5: 0.10,  # HILLS-WOODS
            6: 0.05,  # MOUNTAINS
        }
        if base_weights is None:
            base_weights = default_weights

        probs = np.array(
            [float(base_weights.get(int(t), 0.0)) for t in terrain_ids],
            dtype=np.float64,
        )
        if np.any(probs < 0):
            raise ValueError("base_weights cannot contain negative values")
        if probs.sum() <= 0:
            raise ValueError("base_weights must contain at least one positive value")
        probs = probs / probs.sum()

        # 0 means "unassigned" during generation.
        self.terrain = np.zeros((self.height, self.width), dtype=np.int8)

        for row in range(self.height):
            for col in range(self.width):
                neighbors = self.get_neighbors(row, col)
                assigned_neighbors = [
                    self.terrain[r, c]
                    for r, c in neighbors
                    if self.terrain[r, c] != 0
                ]

                if assigned_neighbors:
                    counts = np.zeros(len(terrain_ids), dtype=np.float64)
                    for terrain_id in assigned_neighbors:
                        counts[terrain_index[int(terrain_id)]] += 1
                    local_probs = counts / counts.sum()
                    blended = ((1 - cluster_strength) * probs) + (
                        cluster_strength * local_probs
                    )
                else:
                    blended = probs

                blended = blended / blended.sum()
                self.terrain[row, col] = rng.choice(terrain_ids, p=blended)


    @classmethod
    def generate_random_map(
        cls, width, height, myseed=None
        ):
        mymap = cls(width, height)
        mymap.generate_random_terrain(
            seed=myseed
        )
        return mymap
    
    @classmethod
    def generate_mapA(cls):
        seed = 545
        size = 8
        return cls.generate_random_map(size, size)
        
