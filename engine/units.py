import numpy as np

UNIT_TYPES = {
    1: {
        "name": "Warrior",
        "base_hp": 100,
        "base_strength": 20,
        "base_movement": 2,
        "attack_range": 0,
        "ranged_strength": 0,
    },
    2: {
        "name": "Slinger",
        "base_hp": 80,
        "base_strength": 5,
        "base_movement": 2,
        "attack_range": 1,
        "ranged_strength": 15,
    },
    3: {
        "name": "Archer",
        "base_hp": 100,
        "base_strength": 15,
        "base_movement": 2,
        "attack_range": 2,
        "ranged_strength": 25,
    },
}


class UnitStates:
    def __init__(self, max_units=20):
        # These don't change once a unit is created.
        self.unit_type = np.zeros(max_units, dtype=np.int8)
        self.unit_owner = np.zeros(max_units, np.int8)

        # These change as the unit interacts with the map.
        self.unit_hp = np.zeros(max_units, dtype=np.float32)
        self.unit_movement_remaining = np.zeros(max_units, dtype=np.int8)
        self.unit_position = np.zeros((max_units, 2), dtype=np.int8)
        self.unit_alive = np.zeros(max_units, dtype=bool)

    def get_combat_strength(self, ind, attack_flag=False, river_flag=False):
        base = UNIT_TYPES[self.unit_type[ind]]["base_strength"]
        strength = (
            base
            + self.get_terrain_bonus(ind, attack_flag)
            + self.get_support_bonus(ind, attack_flag)
            + self.get_flanking_bonus(ind, attack_flag)
            + self.get_fortification_bonus(ind, attack_flag)
            + self.get_health_penalty(ind, attack_flag)
        )
        return strength

    def get_max_unit_strength(self, owner_index):
        pass
