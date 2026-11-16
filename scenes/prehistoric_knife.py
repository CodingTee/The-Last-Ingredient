"""Shared knife presentation for prehistoric stations; all tools remain sprites."""
import math
import arcade

def show_spine(view,name,x,y,dip=0.,angle=0.):
    tex=view.sprites[name].texture
    height=240.
    scale=height/tex.height
    # Register the generated stone tip, not the center of its transparent canvas.
    dx=(.5-.505)*tex.width*scale
    dy=(.01-.5)*height
    theta=math.radians(angle)
    view.show(name,x+dx*math.cos(theta)+dy*math.sin(theta),
              y+dip-dx*math.sin(theta)+dy*math.cos(theta),tex.width*scale,angle)

def draw_knife_slot(view,position,rest_name):
    x,y=position
    arcade.draw_rect_filled(arcade.XYWH(x,y,120,260),(25,25,22,205))
    arcade.draw_rect_outline(arcade.XYWH(x,y,120,260),(173,143,94,180),1.5)
    sprite=view.sprites[rest_name]
    if sprite.visible:arcade.draw_sprite(sprite)
    view.label('knife_slot_title','FLINT KNIFE',x,y+147,10,(240,222,188),'center')
    view.label('knife_slot_action','IN USE' if view.knife_held else 'DRAG TO FOOD',
               x,y-150,10,(240,222,188),'center')
