"""Small in-world cues for water level, correction and ingredient identity."""
import math
import arcade


def draw_water_feedback(v,mx,my,rx,ry):
    v.pot_renderer.draw_mark()
    if v.drain_motion is not None:
        p=min(1,v.drain_motion/.9)
        move=min(1,p/.55)
        sx=mx+(1205-mx)*move;sy=my+(715-my)*move+55*math.sin(move*math.pi)
        ladle=v.simmer_sprites['ladle']
        arcade.draw_texture_rect(ladle,arcade.XYWH(sx+45,sy+20,145,145*ladle.height/ladle.width),angle=-20*move)
        if .5<p<.85:
            arcade.draw_line(sx,sy,1200,710,(159,202,220,190),4)

def water_hint(c):
    if c.can_add_water:return 'Too thick - add a small splash'
    if c.water>=.85:return 'Enough water - keep simmering and stirring'
    if c.thickness<=.75:return 'No water needed - keep simmering'
    return 'Check the soup with the spoon first'
