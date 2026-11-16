"""S05 rear courtyard: bottom-to-top follows the mansion's left-to-right axis.

Coordinates are map pixels from top-left. The side gate is behind the camera;
the lower-left paving continues the side corridor rather than another gate.
"""
WALK_POLYGON = [(220,925),(1070,925),(1130,820),(1145,710),
                (1130,638),(880,638),(890,335),(950,335),
                (960,250),(540,250),(540,315),(400,315),
                (395,400),(350,540),(290,720)]
BLOCKS = [(665,840,638,773),(598,661,687,778),
          (847,915,687,778),(715,787,759,850)]
SPAWN = (320,865)
CORRIDOR_EXIT = (265,925)
DOOR = (467,352)
POND_RIPPLE_X = (1100,1320)
POND_RIPPLE_TOP_Y = (455,550)


def inside_polygon(x,y,points=WALK_POLYGON):
    inside=False
    j=len(points)-1
    for i,(xi,yi) in enumerate(points):
        xj,yj=points[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
        j=i
    return inside


def can_walk(x,y,radius=9):
    """Test a small foot footprint against courtyard boundary and furniture."""
    for dx,dy in [(0,0),(-radius,0),(radius,0),(0,-radius),(0,radius)]:
        px,py=x+dx,y+dy
        if not inside_polygon(px,py): return False
        if any(l<=px<=r and t<=py<=b for l,r,t,b in BLOCKS): return False
    return True
