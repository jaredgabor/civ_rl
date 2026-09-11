import numpy as np

BASE_STRENGTH_REFERENCE = 25
BASE_HP = 100

class CityStates:
    '''
    This is a container for all the state vectors 
    describing cities.  It has nothing to do with Civ6 
    independent "City States."
    '''
    def __init__(self, max_cities=10):
        self.city_location = np.zeros((max_cities, 2), np.int8)
        self.city_population = np.zeros(max_cities, dtype=np.int8)
        self.city_hp = np.zeros(max_cities, dtype=np.int32)
        self.garrison_unit_index = -1 + np.zeros(max_cities, dtype=np.int32)
        self.city_owner = np.zeros(max_cities, np.int8)

    def get_garrison_unit_strength(self, city_index, units):
        unit_index = self.garrison_unit_index[city_index]
        strength = units.get_combat_strength(unit_index)
        return strength

    def compute_combat_strength(self, ind, units):
        # Base strength is owner's strongest unit - 10
        owner_index = self.city_owner[ind]
        max_unit_strength = units.get_max_unit_strength(owner_index)
        reference_unit_strength = max(BASE_STRENGTH_REFERENCE, max_unit_strength)
        base_strength = reference_unit_strength - 10

        # Strength is the larger of the base_strength (which is
        # based on the strongest unit) and the garrison unit's 
        # strength
        garrison_strength = self.get_garrison_unit_strength(
            ind, units)
        base_combat_strength = max(base_strength, garrison_strength)

        # Add in bonuses
        wall_bonus = 0
        hill_bonus = 0
        undamaged_combat_strength = (
            base_combat_strength + wall_bonus + hill_bonus)
        
        # Calculate the damaged city penalty
        current_hp = self.city_hp[ind]
        max_hp = BASE_HP
        hp_penalty = (current_hp / max_hp - 1) * 10
        return undamaged_combat_strength + hp_penalty
    
    def apply_city_damage(self, ind, damage):
        self.city_hp[ind] -= damage

    def check_captured(self, city_index, units, attacker_index):
        capture_flag = False
        if self.city_hp[city_index] <= 0:
            unit_type = units.unit_type[attacker_index]
            if unit_type.attack_range == 0:
                capture_flag = True
        return capture_flag
    
    def heal_cities(self):
        # TODO: check if healing should occur 
        # (depending on whether city is under siege)
        self.city_hp += 10

        # Cities can't have more than 100 HP
        self.city_hp = np.clip(self.city_hp, a_max=BASE_HP)