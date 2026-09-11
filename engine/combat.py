import math


BASE_DAMAGE = 30
CURVATURE = 25
MAX_DELTA = 40



def compute_damage(strength_att, strength_def, ranged=False):
    '''
    Compute damage on defender and attacker.
    
    :param strength_att: Description
    :param strength_def: Description
    '''
    delta = max(min(strength_att - strength_def, MAX_DELTA), -MAX_DELTA)
    damage_to_def = BASE_DAMAGE * math.exp(delta / CURVATURE)

    damage_to_att = 0
    if ranged:
        damage_to_att = 0
    else:
        delta2 = - delta
        damage_to_att = BASE_DAMAGE * math.exp(delta2 / CURVATURE)

    return damage_to_def, damage_to_att

