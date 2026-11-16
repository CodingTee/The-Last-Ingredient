"""Royal kitchen floor movement; cooking progress belongs to the Cooking model."""
from dataclasses import dataclass
import math


@dataclass
class KitchenWalker:
    x: float = 1130
    y: float = 250
    speed: float = 225
    door_open: bool = False

    def toggle_door(self):
        self.door_open = not self.door_open
        return self.door_open

    def legal(self, x: float, y: float) -> bool:
        # 1. Overall kitchen boundaries (floor allows walking up to back wall shelves and doorway)
        if not (70 <= x <= 1370 and 95 <= y <= 515):
            return False

        # 2. Bottom-left vegetable baskets, flour sacks & wall props:
        # Prevents protagonist from stepping onto produce baskets, flour sacks and mushrooms.
        if x < 170 and y < 355:  # Wall barrel and side props beside stove
            return False
        if x < 200 and y < 290:  # Large flour sacks and dried mushroom sack
            return False
        if x < 265 and y < 252:  # Center tomato/cabbage vegetable crate & rear sacks
            return False
        if x < 315 and y < 205:  # Rightmost fresh herb / green vegetable round basket
            return False
        # Left wall edge
        if x < 150:
            return False

        # 3. Cast iron cooking stove / range on left
        # Stove body ends horizontally at x=340 so path above barrel is open
        if 150 <= x <= 340 and y >= 335:
            return False

        # Central table: floor footprint between the front and rear legs.
        if 495 <= x <= 1005 and 190 <= y <= 255:
            return False

        # Footprints of the barrel and sack crate beside the table.
        # Barrel solid body footprint: floor base blocks walking into barrel, leaving a wide corridor behind (y: 256..369)
        # Sack crate footprint: solid wooden crate and flour sacks (rendered x: 978..1132), blocks front, right and rear
        if (375 <= x <= 495 and 185 <= y <= 255) or (985 <= x <= 1130 and 190 <= y <= 295):
            return False

        # 6. Back wall baseline: floor ends at y=370 (clean horizontal wall base across kitchen)
        # Prevents protagonist from walking onto the vertical stone brick wall.
        if 340 <= x <= 1115 and y >= 370:
            return False

        # 7. Doorway / archway (1115 <= x <= 1240):
        # Treated strictly as a solid wall at all times (whether door is open or closed).
        # Protagonist's feet can never step past y=358 into the archway doorway corridor.
        if 1115 <= x <= 1240 and y >= 358:
            return False

        # 8. Right wall sideboard / cupboard: wall baseline starts at y >= 368
        if x >= 1240 and y >= 368:
            return False

        # 9. Bottom-right floor barrel & water pot
        if x >= 1205 and y <= 245:
            return False

        return True

    def move(self, dx: float, dy: float, dt: float):
        length = math.hypot(dx, dy)
        if not length:
            return
        step_x = dx / length * self.speed * dt
        step_y = dy / length * self.speed * dt
        # Slide along solid obstacles rather than sticking
        if self.legal(self.x + step_x, self.y):
            self.x += step_x
        if self.legal(self.x, self.y + step_y):
            self.y += step_y

    def near(self, station: str) -> bool:
        if station == "prep":
            # Both front (165) and behind work positions (290) at the central prep table
            return math.dist((self.x, self.y), (790, 165)) <= 115 or math.dist((self.x, self.y), (790, 290)) <= 115
        targets = {
            "range": (310, 310),
            "door": (1175, 400),
        }
        target = targets.get(station)
        if not target:
            return False
        return math.dist((self.x, self.y), target) <= 115

