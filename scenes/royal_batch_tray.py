"""One physical tray transfers the three prepared ingredients in one held gesture."""
import math
import arcade


class RoyalBatchTray:
    ORDER=('onion','carrot','barley')
    def __init__(self,v,assets):
        self.v=v
        self.texture=arcade.load_texture(assets/'range_hardware_v2/prep_tray.png')
        self.reset()

    def reset(self):
        self.dragging=False;self.progress=0.;self.tilt=0.

    def over_pot(self):
        x,y=self.v.mouse
        mx,my,rx,ry=self.v.pot_renderer.mouth(*self.v.CLOSEUP_POT)
        return ((x-mx)/(rx*1.05))**2+((y-my)/(ry*1.05))**2<=1

    def press(self,x,y):
        v=self.v
        if len(v.cook.ingredients)==3:return False
        if 600<x<1050 and 345<y<510:
            if v.cook.water_ready and v.drain_motion is None:
                self.dragging=True;v.hold=None;v.barley_intro_until=v.clock+4;v.ping()
            return True
        return False

    def release(self):
        self.dragging=False

    def update(self,dt):
        v=self.v
        if v.page!='cooking' or v.cook.stage!='fill':self.dragging=False;return
        pouring=self.dragging and self.over_pot()
        self.tilt+=(int(pouring)-self.tilt)*min(1,dt*10)
        if pouring and v.cook.water_ready:
            self.progress=min(1.5,self.progress+dt)
            for i,name in enumerate(self.ORDER):
                if self.progress >= (i+1)*.5 and name not in v.cook.ingredients:
                    if v.cook.add(name):v.ping('click')
            if len(v.cook.ingredients)==3:self.dragging=False

    def draw(self):
        v=self.v;c=v.cook
        if len(c.ingredients)==3:return
        from .royal_view import image,text,GOLD
        x,y=(v.mouse[0]+140,v.mouse[1]+75) if self.dragging else (825,430)
        angle=-25*self.tilt
        arcade.draw_texture_rect(self.texture,arcade.XYWH(x,y,450,450*self.texture.height/self.texture.width),angle=angle)
        radians=math.radians(-angle)
        for i,name in enumerate(self.ORDER):
            if name in c.ingredients:continue
            portion=max(0,min(1,(self.progress-i*.5)/.5))
            size=1-portion
            offset=(i-1)*115
            fx=x+offset*math.cos(radians);fy=y+offset*math.sin(radians)+10
            if size>.02:
                # The tray carries the same diced heaps that end up on the board
                # (draw_pile, no tips/discards), never whole halves or a cut head.
                if name=='onion':v.onion_slices.draw_pile((fx,fy),.40*size)
                elif name=='carrot':v.carrot_slices.draw_pile((fx,fy),.30*size)
                else:image(v.boil_sprites['barley'],fx,fy,105*size,60*size)
            if self.dragging and self.over_pot() and i==min(2,int(self.progress/.5)):
                texture=v.pot_renderer.grain if name=='barley' else v.food_pieces[name][0]
                mx,my,_,_=v.pot_renderer.surface(c.water,*v.CLOSEUP_POT)
                for j in range(8):
                    t=(v.clock*2.7+j*.12)%1
                    px=(x-170)*(1-t)+v.CLOSEUP_POT[0]*t+math.sin(j*3)*7
                    py=(y+20)*(1-t)+my*t+math.sin(t*math.pi)*18
                    image(texture,px,py,11,11*texture.height/texture.width if name=='barley' else 8)
    def hint(self,x,y):
        if self.dragging:return ''
        if len(self.v.cook.ingredients)<3 and 600<x<1050 and 345<y<510:
            return 'Drag the tray over the pot and hold' if self.v.cook.water_ready else 'Fill water to the mark first'
        return ''
