"""Registered firebox opening and a two-plate rotary air regulator."""
import math
import arcade


class RoyalRangeHardware:
    AIR=(588,145)
    AIR_TRAVEL = 36
    def __init__(self,v,assets):
        self.v=v
        folder=assets/'range_hardware_v2'
        self.open_patch=arcade.load_texture(folder/'firebox_open_upper_left_vents.png')
        reference=arcade.load_texture(folder/'range_open_original.png')
        scale=max(1440/reference.width,900/reference.height)
        width=self.open_patch.width*scale;height=self.open_patch.height*scale
        self.patch_rect=arcade.XYWH((1440-reference.width*scale)/2+width/2,(900-reference.height*scale)/2+height/2,width,height)
        self.base=arcade.load_texture(folder/'air_fixed_plate.png')
        self.cover=arcade.load_texture(folder/'air_rotating_cover.png')
        self.reset()

    def reset(self):self.door_open=False

    def air_pointer_angle(self, x, y):
        cx, cy = self.AIR
        return math.degrees(math.atan2(y - cy, x - cx))

    def set_air(self, x, y):
        if math.dist((x, y), self.AIR) < 8:
            return
        pointer = self.air_pointer_angle(x, y)
        if self.air_pointer is not None:
            delta = (pointer - self.air_pointer + 180) % 360 - 180
            cook = self.v.cook
            cook.air_opening = min(1, max(0, cook.air_opening - delta / self.AIR_TRAVEL))
        self.air_pointer = pointer

    def press(self,x,y):
        v=self.v
        if math.dist((x,y),self.AIR)<72 and not self.door_open and v.coal_motion is None:
            self.air_pointer = None
            v.hold = 'air'
            self.set_air(x, y)
            return True
        bucket=(1170,465)
        if abs(x-bucket[0])<105 and abs(y-bucket[1])<110:
            if v.coal_motion is None:
                self.door_open=True;v.coal_motion=0.;v.hold=None;v.ping()
            return True
        if 165<x<680 and 55<y<235:
            if v.coal_motion is None:self.door_open=not self.door_open;v.ping()
            return True
        return False

    def update(self,dt):
        v=self.v
        if v.coal_motion is None:return
        before=v.coal_motion;v.coal_motion+=dt
        if before<.85<=v.coal_motion:
            v.cook.add_coal();v.ping('impact')
        if v.coal_motion>=1.35:v.coal_motion=None;self.door_open=False

    def draw(self):
        v=self.v;c=v.cook
        from .royal_view import image
        bucket=(1170,465)
        image(v.boil_sprites['coal_bucket'],*bucket,185,200)
        if self.door_open:
            arcade.draw_texture_rect(self.open_patch,self.patch_rect)
        else:self.draw_air()
        if v.coal_motion is not None:
            t=v.coal_motion
            p=min(1,max(0,(t-.20)/.55)) if t<.85 else max(0,1-(t-.85)/.5)
            x=bucket[0]+(430-bucket[0])*p;y=bucket[1]+(145-bucket[1])*p+math.sin(p*math.pi)*85
            image(v.boil_sprites['coal_shovel'],x,y,220)

    def hint(self,x,y):
        if math.dist((x,y),self.AIR)<72 and not self.door_open:
            return f'Air vent: {self.v.cook.air_opening:.0%} - drag to turn'
        if 165<x<680 and 55<y<235:return 'Close firebox' if self.door_open else 'Open firebox'
        bucket=(1170,465)
        if abs(x-bucket[0])<105 and abs(y-bucket[1])<110:
            c = self.v.cook
            if c.heat == 2:
                return 'Coal full (Level 2) - click to replenish'
            elif c.heat == 1:
                return 'Click to add coal (+1 Level to High)'
            else:
                return 'Click to add coal (+1 Level to ignite)'
        return ''

    def draw_air(self):
        rect = arcade.XYWH(*self.AIR, 156, 156)
        angle = self.AIR_TRAVEL * (1 - self.v.cook.air_opening)
        arcade.draw_texture_rect(self.base, rect)
        arcade.draw_texture_rect(self.cover, rect, angle=-angle)
