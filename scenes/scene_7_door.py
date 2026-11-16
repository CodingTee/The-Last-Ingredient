"""Scene 7 open-door geometry, shared by the view and the sprite renderer.

Coordinates are world units. Image rows in kitchen_refined.png map to world y
as 937 - row. Only the swinging leaf is modelled here; the closed door keeps
its own contour in scene_7_kitchen_view.py.
"""

LEAF_X_MIN = 58.0
LEAF_X_MAX = 157.0
LEAF_BOTTOM_Y_LEFT = 367.0
LEAF_BOTTOM_Y_RIGHT = 331.0

# When walking left towards the door from behind it, the protagonist's hair and
# front side (width ~51px from center) enter the door leaf before his center x
# reaches LEAF_X_MAX. Adding pad ensures occlusion activates early so hair
# naturally and seamlessly slips behind the door edge/handle without popping.
LEAF_OCCLUDE_PAD_RIGHT = 70.0

FRAME_X_NEAR = 40.0
FRAME_Y_NEAR = 287.0
FRAME_X_FAR = 58.0
FRAME_Y_FAR = 675.0

# Open-door copy of the closed-door skirting line. Kept here so the open branch
# never calls a closed-door function; the two collision sets stay independent.
SKIRTING = ((22.0, 248.0), (30.0, 260.0), (75.0, 342.0),
            (130.0, 422.0), (145.0, 436.0), (175.0, 488.0))

ROOM_SKIRTING_Y = 488.0

# High feet_y puts the player behind the leaf, where the frame wall is solid.
# 145 keeps his right half outside the leaf so the body never fully vanishes.
BEHIND_MIN_X = 145.0
BEHIND_RAMP_Y0 = 300.0
# Finish the ramp before feet_y reaches the behind-leaf threshold (333).
BEHIND_RAMP_Y1 = 340.0


def open_door_leaf_bottom_y(x: float) -> float:
    """World y of the leaf/floor contact line at x."""
    if x <= LEAF_X_MIN:
        return LEAF_BOTTOM_Y_LEFT
    if x >= LEAF_X_MAX:
        return LEAF_BOTTOM_Y_RIGHT
    t = (x - LEAF_X_MIN) / (LEAF_X_MAX - LEAF_X_MIN)
    return LEAF_BOTTOM_Y_LEFT + (LEAF_BOTTOM_Y_RIGHT - LEAF_BOTTOM_Y_LEFT) * t


def open_door_min_x(feet_y: float) -> float:
    """Left bound: doorway floor low down, solid frame wall behind the leaf."""
    t = (feet_y - FRAME_Y_NEAR) / (FRAME_Y_FAR - FRAME_Y_NEAR)
    t = min(1.0, max(0.0, t))
    frame = FRAME_X_NEAR + (FRAME_X_FAR - FRAME_X_NEAR) * t
    if feet_y <= BEHIND_RAMP_Y0:
        return frame
    if feet_y >= BEHIND_RAMP_Y1:
        return BEHIND_MIN_X
    ramp = (feet_y - BEHIND_RAMP_Y0) / (BEHIND_RAMP_Y1 - BEHIND_RAMP_Y0)
    return frame + (BEHIND_MIN_X - frame) * ramp


def open_door_max_feet_y(x: float) -> float:
    """Skirting line behind the open leaf: the same wall as the closed door."""
    if x <= SKIRTING[0][0]:
        return SKIRTING[0][1]
    for (x1, y1), (x2, y2) in zip(SKIRTING, SKIRTING[1:]):
        if x <= x2:
            return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    if x <= 1530.0:
        return ROOM_SKIRTING_Y
    return max(340.0, ROOM_SKIRTING_Y - (x - 1530.0) * 2.5)


def open_door_obstacles():
    """Thin slanted wall along the leaf contact line; feet cannot cross it."""
    rects = []
    steps = 12
    for i in range(steps):
        x1 = LEAF_X_MIN + (LEAF_X_MAX - LEAF_X_MIN) * i / steps
        x2 = LEAF_X_MIN + (LEAF_X_MAX - LEAF_X_MIN) * (i + 1) / steps
        y = open_door_leaf_bottom_y((x1 + x2) / 2.0)
        rects.append((x1, x2, y - 7.0, y + 7.0))
    return rects


def is_behind_open_door(x: float, feet_y: float) -> bool:
    """True when the leaf must be drawn in front of the player."""
    if not (LEAF_X_MIN - 16.0 <= x <= LEAF_X_MAX + LEAF_OCCLUDE_PAD_RIGHT):
        return False
    cx = min(LEAF_X_MAX, max(LEAF_X_MIN, x))
    return feet_y > open_door_leaf_bottom_y(cx) + 2.0
