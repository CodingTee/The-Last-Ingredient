"""Deterministic cooking model for the Royal chapter (c. 1910).
Carrots, onions, and barley stew on a closed coal-fired cast iron range.
"""
from dataclasses import dataclass, field


@dataclass
class Cooking:
    stage: str = "prep"
    cuts: dict = field(default_factory=lambda: {"carrot": 0, "onion": 0})
    onion_turned: bool = False
    carrot_turned: bool = False
    water: float = 0.0
    checked_thick: bool = False
    ingredients: set = field(default_factory=set)
    temperature: float = 18.0
    heat: int = 0
    coal_fuel: float = 0.0
    air_opening: float = 0.0
    left_plate_heat: float = 0.0
    right_plate_heat: float = 0.0
    softness: float = 0.0
    thickness: float = 0.35
    scorch: float = 0.0
    unstirred: float = 0.0
    simmer_heat: float = 1.0
    boiled: bool = False
    salted: bool = False
    served: float = 0.0
    spills: int = 0
    spill_cooldown: float = 0.0
    completed: bool = False

    @property
    def fire_output(self):
        return (0.0, 0.52, 1.0)[self.heat] * self.air_opening

    def cut_goal(self, ingredient):
        return {"onion": 10, "carrot": 10}[ingredient]

    def chop(self, ingredient):
        if self.stage != "prep" or ingredient not in self.cuts:
            return False
        if self.cuts[ingredient] >= self.cut_goal(ingredient):
            return False
        if ingredient == 'onion' and self.cuts['onion'] >= 6 and not self.onion_turned:
            return False
        if ingredient == 'carrot' and self.cuts['carrot'] >= 6 and not self.carrot_turned:
            return False
        self.cuts[ingredient] += 1
        return True

    def turn_onion(self):
        if self.stage != 'prep' or self.cuts['onion'] != 6 or self.onion_turned:
            return False
        self.onion_turned = True
        return True

    def turn_carrot(self):
        if self.stage != 'prep' or self.cuts['carrot'] != 6 or self.carrot_turned:
            return False
        self.carrot_turned = True
        return True

    @property
    def prepared(self):
        return all(n == self.cut_goal(item) for item, n in self.cuts.items())

    def start_fill(self):
        if self.stage == "prep" and self.prepared:
            self.stage = "fill"
            return True
        return False

    @property
    def water_ready(self):
        return .45 <= self.water <= .72

    def add(self, ingredient):
        if self.stage == 'fill' and self.water_ready and ingredient in {'carrot','onion','barley'}:
            self.ingredients.add(ingredient)
            return True
        return False

    def pour(self, dt):
        if self.stage == 'fill' and not self.ingredients:
            self.water = min(.85, self.water + dt*.22)

    def drain(self):
        if self.stage != 'fill' or self.ingredients or self.water <= 0:
            return False
        self.water = max(0,self.water-.10)
        return True

    def add_coal(self):
        if self.stage in {"boil", "simmer"}:
            self.coal_fuel = min(2.0, self.coal_fuel + 1.0)
            if self.coal_fuel > 1.0:
                self.heat = 2
            elif self.coal_fuel > 0.0:
                self.heat = 1
            else:
                self.heat = 0
            return True
        return False

    def start_boil(self):
        if self.stage == "fill" and 0.45 <= self.water <= 0.72 and len(self.ingredients) == 3:
            self.stage = "boil"
            self.heat = 0
            self.coal_fuel = 0.0
            self.left_plate_heat = 0.0
            return True
        return False

    def tick(self, dt, paused=False):
        if paused:
            return
        self.spill_cooldown = max(0, self.spill_cooldown - dt)
        if self.stage in {"boil", "simmer"}:
            # Coal burns down gradually over time: 2nd level -> 1st level -> 0 level (unlit)
            if self.coal_fuel > 0:
                rate = (1.15 / 16.0) * self.air_opening
                self.coal_fuel = max(0.0, self.coal_fuel - dt * rate)

            if self.coal_fuel > 1.0:
                self.heat = 2
            elif self.coal_fuel > 0.0:
                self.heat = 1
            else:
                self.heat = 0

            self.left_plate_heat += (self.fire_output - self.left_plate_heat) * min(1, dt / 4)
            self.right_plate_heat += (self.left_plate_heat * 0.58 - self.right_plate_heat) * min(1, dt / 7)
        if self.stage == "boil":
            if self.left_plate_heat > 0.05:
                gain = 6.2 * self.left_plate_heat
                self.temperature = min(100, self.temperature + dt * gain)
            else:
                self.temperature = max(18.0, self.temperature - dt * 0.35)
            evaporation = min(1.0, max(0.0, (self.temperature - 60.0) / 36.0))
            if self.water > 0.12:
                self.water = max(0.12, self.water - dt * 0.0018 * evaporation)
            if self.temperature >= 96:
                self.boiled = True
                self.move_to_gentle_hob()
                return
            if self.temperature >= 99 and self.left_plate_heat > 0.80 and self.spill_cooldown == 0:
                self.spills += 1
                self.water = max(0.40, self.water - 0.025)
                self.temperature = 98
                self.spill_cooldown = 5
        elif self.stage == "simmer":
            if self.fire_output == 0:
                self.temperature += (18 + 60 * self.left_plate_heat - self.temperature) * min(1, dt / 6)
                return
            if self.air_opening >= .80:
                target_temperature = 98.0
                self.temperature += (target_temperature - self.temperature) * min(1, dt / 4)
                # Rapid water evaporation
                self.water = max(0.12, self.water - dt * 0.016)
                # Thickness surges
                self.thickness = min(0.98, self.thickness + dt * 0.022)
                # Sticking and scorching
                self.unstirred += dt * 1.8
                if self.unstirred > 10.0 or self.thickness > 0.70 or self.water < 0.38:
                    self.scorch = min(1.0, self.scorch + dt * 0.045)
            elif self.air_opening <= .55:
                # Gentle simmer (70~80 C)
                target_temperature = 72.0 + 8.0 * self.left_plate_heat
                self.temperature += (target_temperature - self.temperature) * min(1, dt / 6)
                # Very slow natural evaporation
                self.water = max(0.12, self.water - dt * 0.0018)
                # Vegetables and barley soften thoroughly
                effective = 1.0 if self.unstirred < 16 else 0.4
                self.softness = min(1.0, self.softness + dt * 0.040 * effective)
                # Thickness stabilizes in golden 25%~75% range (~0.45)
                self.thickness += (0.45 - self.thickness) * min(1, dt * 0.02)
                self.unstirred += dt
                self.scorch = max(0.0, self.scorch - dt * 0.015)
            else:
                # Half damper (80~88 C)
                target_temperature = 84.0
                self.temperature += (target_temperature - self.temperature) * min(1, dt / 6)
                self.water = max(0.12, self.water - dt * 0.006)
                effective = 0.8 if self.unstirred < 16 else 0.3
                self.softness = min(1.0, self.softness + dt * 0.032 * effective)
                self.thickness = min(0.95, self.thickness + dt * 0.008)
                self.unstirred += dt * 1.2

    def move_to_gentle_hob(self):
        if self.stage == "boil" and self.boiled:
            self.stage = "simmer"
            return True
        return False

    def tend_fire(self):
        if self.stage in {"boil", "simmer"}:
            self.heat = 2

    def stir(self):
        if self.stage == "simmer":
            self.unstirred = 0
            self.softness = min(1.0, self.softness + .02)
            self.scorch = max(0.0, self.scorch - 0.05)

    def inspect_consistency(self):
        if self.stage != 'simmer': return None
        if self.scorch > 0.4:
            kind = 'scorched'
        elif self.thickness > 0.75:
            kind = 'thick'
        elif self.thickness < 0.25:
            kind = 'thin'
        else:
            kind = 'balanced'
        self.checked_thick = (kind in {'thick', 'scorched'})
        return kind

    @property
    def can_add_water(self):
        return self.stage == 'simmer' and (self.water < 0.75 or self.thickness > 0.60)

    def add_water(self):
        if not self.can_add_water: return False
        self.water = min(0.75, self.water + 0.16)
        self.thickness = max(0.25, self.thickness - 0.20)
        self.scorch = max(0.0, self.scorch - 0.35)
        self.temperature = max(70.0, self.temperature - 4.0)
        self.checked_thick = False
        return True

    @property
    def ready(self):
        return (self.stage == "simmer" and self.softness >= 1.0
                and 0.25 <= self.thickness <= 0.75 and self.water >= 0.35
                and self.unstirred < 16 and self.scorch < 0.35)

    def taste(self):
        if self.scorch > 0.4:
            return "The soup is scorching and tastes bitter! Turn vent to Low and add water from the jug right away!"
        if self.air_opening >= .80 and self.temperature > 90:
            return "The fire is roaring and boiling furiously! Turn the air vent down to Low to let it gently simmer."
        if self.water < 0.35 or self.thickness > 0.75:
            return "The broth has boiled down too far! Add water from the jug to replenish the soup."
        if self.softness < 0.50:
            return "The carrots and barley are still firm. Keep simmering on gentle heat."
        if self.softness < 1.0:
            return "The barley needs a little more time to soften. Remember to stir gently."
        if self.unstirred >= 16:
            return "Starting to stick to the bottom. Gently stir it loose."
        return "Tender vegetables and rich, balanced broth. The simmering is perfection! Ready to finish."

    def leave(self):
        if self.ready:
            self.stage = "away"
            return True
        return False

    def season(self):
        if self.stage == "returned" and not self.salted:
            self.salted = True
            return True
        return False

    def finish_seasoning(self):
        if self.stage == "returned" and self.salted:
            self.stage = "serve"
            return True
        return False

    def ladle(self, dt):
        if self.stage == "serve":
            self.served = min(1, self.served + dt * 0.35)

    def finish(self):
        if self.stage == "serve" and self.served >= 1:
            self.stage = "complete"
            self.completed = True
            return True
        return False
