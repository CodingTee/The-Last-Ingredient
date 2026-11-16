"""Deterministic prehistoric meal state. Cooking mistakes never select an ending."""
from dataclasses import dataclass, asdict

PEEL_PIECES = 3


@dataclass
class RoastMeal:
    version: int = 3
    stage: str = 'place'
    heat: float = .40
    side_a: float = 0.
    side_b: float = 0.
    scorch_a: float = 0.
    scorch_b: float = 0.
    hot_time: float = 0.
    ready_time: float = 0.
    prepared: bool = False
    prep_step: int = 0
    prep_cuts: int = 0
    prep_peels: int = 0
    cuts: int = 0
    portions: int = 0
    portion_mask: int = 0
    turn: float = 0.
    target_turn: float = 0.
    served: bool = False
    clue_seen: bool = False

    @classmethod
    def restore(cls, saved):
        if not saved or saved.get('version') not in (2, 3):
            return cls()
        meal = cls(**{k:v for k,v in saved.items() if k in cls.__dataclass_fields__})
        if 'portion_mask' not in saved:
            meal.portion_mask = (1 << meal.portions) - 1
        if 'target_turn' not in saved:
            meal.target_turn = meal.turn
        if 'prepared' not in saved and meal.stage != 'place':
            meal.prepared=True
            meal.prep_step=6
        meal.version = 3
        if saved.get('version') == 2 and meal.prep_step == 3:
            meal.prep_step = 4  # Resume old trimming saves at the skewer.
        return meal

    def prepare(self, action):
        """Ordered preparation gestures; errors never advance the recipe."""
        if self.prepared or self.stage != 'place': return False
        expected={0:'cut',1:'portion',2:'peel',3:'debone',4:'skewer',5:'mount'}.get(self.prep_step)
        if action != expected: return False
        if action=='cut':
            self.prep_cuts+=1
            if self.prep_cuts<2: return True
        elif action=='peel':
            self.prep_peels += 1
            if self.prep_peels >= PEEL_PIECES:
                self.prep_step = 3
            return True
        self.prep_step += 1
        if action=='mount':
            self.prepared=True
            self.place()
        return True

    def save(self):
        return asdict(self)

    @property
    def is_roasting(self):
        return self.stage in ('roast_a', 'roast_b', 'turn', 'roasting')

    @property
    def active_side(self):
        """Side currently facing the fire (bottom)."""
        return 'b' if self.turn >= 90 else 'a'

    @property
    def ambient_side(self):
        """Side currently facing the air (top)."""
        return 'a' if self.turn >= 90 else 'b'

    @property
    def exposed_side(self):
        return self.active_side

    @property
    def heat_warning(self):
        active_scorch = getattr(self, 'scorch_' + self.active_side)
        return active_scorch >= 0.20 or self.heat >= 0.75

    def toggle_turn(self):
        if not self.is_roasting and self.stage != 'lift':
            return False
        if self.target_turn == 0:
            self.target_turn = 180.0
        else:
            self.target_turn = 0.0
        return True

    def tick(self, dt, fanning=False):
        dt = max(0., min(.05, dt))
        if not self.is_roasting and self.stage != 'lift':
            return

        # Smooth crank turning interpolation (0.40s for 180 deg)
        if self.turn < self.target_turn:
            self.turn = min(self.target_turn, self.turn + 180.0 * dt / 0.40)
        elif self.turn > self.target_turn:
            self.turn = max(self.target_turn, self.turn - 180.0 * dt / 0.40)

        # 1. Fire heat dynamics: fanning pushes heat up, lack of fanning decays down
        if fanning:
            self.heat = min(1.0, self.heat + dt * 0.55)
        else:
            self.heat = max(0.0, self.heat - dt * 0.12)

        # Multiplier based on heat:
        # Cold (< 0.22): 0x
        # Steady (0.22 .. 0.70): 0.04x .. 1.0x
        # Turbo (> 0.70 .. 1.0): 1.0x .. 2.5x
        if self.heat < 0.22:
            heat_mult = 0.0
        elif self.heat < 0.70:
            heat_mult = (self.heat - 0.20) / 0.50
        else:
            heat_mult = 1.0 + (self.heat - 0.70) / 0.30 * 1.5

        if self.is_roasting:
            base_rate = 0.075 * heat_mult
            active = self.active_side
            ambient = self.ambient_side

            # Active side (facing fire)
            active_val = getattr(self, 'side_' + active)
            if active_val < 1.0:
                setattr(self, 'side_' + active, min(1.0, active_val + base_rate * dt))
            else:
                # 100% doneness reached on active side -> Scorch starts!
                scorch_rate = 0.09 * max(0.4, heat_mult)
                new_scorch = min(1.0, getattr(self, 'scorch_' + active) + scorch_rate * dt)
                setattr(self, 'scorch_' + active, new_scorch)
                if new_scorch >= 1.0:
                    self.stage = 'burned'
                    return

            # Ambient side (facing air) - cooks slowly at 22% rate, NEVER scorches in the air
            ambient_val = getattr(self, 'side_' + ambient)
            if ambient_val < 1.0:
                setattr(self, 'side_' + ambient, min(1.0, ambient_val + base_rate * 0.22 * dt))

            # Ready condition: both sides at 100% doneness!
            if self.side_a >= 1.0 and self.side_b >= 1.0 and self.scorch_a < 1.0 and self.scorch_b < 1.0:
                self.stage = 'lift'

    def retry(self):
        if self.stage != 'burned':
            return False
        self.stage = 'place'
        self.heat = 0.40
        self.side_a = 0.0
        self.side_b = 0.0
        self.scorch_a = 0.0
        self.scorch_b = 0.0
        self.turn = 0.0
        self.target_turn = 0.0
        self.hot_time = 0.0
        self.ready_time = 0.0
        return True

    def place(self):
        if self.stage == 'place':
            self.stage = 'roast_a'
            self.heat = 0.40
            self.side_a = 0.0
            self.side_b = 0.0
            self.scorch_a = 0.0
            self.scorch_b = 0.0
            self.turn = 0.0
            self.target_turn = 0.0
            return True
        return False

    def rotate(self, amount=180.0):
        if not self.is_roasting and self.stage != 'lift':
            return False
        return self.toggle_turn()

    def lift(self):
        if self.stage == 'lift' and min(self.side_a, self.side_b) >= 1:
            self.stage = 'carve'
            return True
        return False

    def cut(self):
        if self.stage != 'carve':
            return False
        self.cuts = min(3, self.cuts + 1)
        if self.cuts == 3:
            self.stage = 'plate'
        return True

    def portion(self, group=None):
        if self.stage != 'plate':
            return False
        if group is None:
            group = next((i for i in (0, 1) if not self.portion_mask & (1 << i)), None)
        if group not in (0, 1) or self.portion_mask & (1 << group):
            return False
        self.portion_mask |= 1 << group
        self.portions = self.portion_mask.bit_count()
        if self.portions == 2:
            self.stage = 'carry'
        return True

    def deliver(self):
        if self.stage == 'carry':
            self.stage = 'return_fire'
            self.served = True
            return True
        return False
