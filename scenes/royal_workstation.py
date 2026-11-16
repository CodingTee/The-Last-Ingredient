"""Independent ingredient, washing and final serving interactions for Royal cooking."""
import math
import arcade
from arcade.types import Color


class RoyalWorkstation:
    def __init__(self,view,asset_dir):
        self.v=view
        self.selected=None
        self.loaded=False
        self.motion=None
        self.regions=[]
        self.washed=0.0
        self.wash_hold=False
        self.textures={n:arcade.load_texture(asset_dir/'workstation_v2'/(n+'.png')) for n in ('wash_basin','washing_hands','wash_background','prep_board')}

    def stop_input(self):
        self.selected=None;self.loaded=False;self.wash_hold=False
        if getattr(self.v,'batch_tray',None):self.v.batch_tray.release()
        v=self.v;v.hold=None;v.drag=None;v.stir_angle=None;v.stir_travel=0
        v.walk_keys.clear()

    def draw(self,key,texture,x,y,w,h=None,angle=0,alpha=255):
        if texture is self.v.carrot_frames[-1]:
            scale=min(w/440,(h or w*.5)/200)
            self.v.carrot_slices.draw(9,90,center=(x,y),scale=scale)
            if key:self.regions.append((key,self.v.carrot_frames[-1],x,y,scale,90))
            return
        if texture is self.v.onion_frames[-1]:
            scale=min(w/360,(h or w*.5)/200)
            self.v.onion_slices.draw(10,90,center=(x,y),scale=scale)
            if key:self.regions.append((key,self.v.onion_frames[-1],x,y,scale,90))
            return
        h=h or w*texture.height/texture.width
        q=min(w/texture.width,h/texture.height)
        if key and self.selected==key:
            arcade.draw_texture_rect(texture,arcade.XYWH(x,y,texture.width*q*1.06,texture.height*q*1.06),angle=angle,color=Color(255,218,128,170))
        arcade.draw_texture_rect(texture,arcade.XYWH(x,y,texture.width*q,texture.height*q),angle=angle,color=Color(255,255,255,round(alpha)))
        if key:self.regions.append((key,texture,x,y,q,angle))

    def hit(self,x,y):
        for key,t,cx,cy,q,angle in reversed(self.regions):
            if key in {'onion','carrot'}:
                rx=(180 if key=='onion' else 220)*q;ry=100*q
                if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1:return key
                continue
            a=math.radians(-angle);dx=x-cx;dy=y-cy
            xx=dx*math.cos(a)-dy*math.sin(a);yy=dx*math.sin(a)+dy*math.cos(a)
            px=xx/q+t.width/2;py=t.height/2-yy/q
            if 0<=px<t.width and 0<=py<t.height and t.image.getpixel((int(px),int(py)))[3]>30:return key
        return None

    def animate(self,name,texture,start,end,finish):
        self.motion=dict(name=name,tex=texture,start=start,end=end,t=0.,finish=finish)
        self.selected=None;self.v.ping()

    def update(self,dt):
        if self.motion:
            m=self.motion;m['t']+=dt
            if m['t']>=.7:
                self.motion=None;m['finish']()
        if self.wash_hold and self.v.page=='wash':
            self.washed=min(1,self.washed+dt/3)
            if self.washed>=1:self.wash_hold=False

    def use_overlay(self):
        v=self.v
        if self.motion:
            m=self.motion;p=min(1,m['t']/.7);a,b=m['start'],m['end']
            self.draw(None,m['tex'],a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p+70*math.sin(math.pi*p),170,130,angle=-20*math.sin(math.pi*p))
            if m['name']=='salt' and p>.5:
                for j in range(7):arcade.draw_circle_filled(1000+(j-3)*7,590-(v.clock*80+j*12)%65,1.8,(245,239,210,220))
        if self.selected:
            row=next((r for r in self.regions if r[0]==self.selected),None)
            if row:self.draw(None,row[1],v.mouse[0]+25,v.mouse[1]+30,100,100)
        if self.loaded and self.selected=='ladle':
            self.draw(None,v.sprites['soup_bowl'],v.mouse[0]+28,v.mouse[1]+55,35,25)

    def fill_ingredients(self):
        self.regions.clear()
        self.v.batch_tray.draw()

    def handle_fill(self,x,y,button):
        if button!=arcade.MOUSE_BUTTON_LEFT:return False
        return self.v.batch_tray.press(x,y)

    def start_wash(self):
        self.stop_input();self.v.page='wash';self.v.location='kitchen'

    def wash_draw(self):
        v=self.v;self.regions.clear()
        self.draw(None,self.textures['wash_background'],720,450,1440,900)
        self.draw(None,self.textures['wash_basin'],720,440,700,420)
        if self.washed>0:arcade.draw_ellipse_filled(720,470,440,90,(160,195,195,90))
        sway=10*math.sin(v.clock*8) if self.wash_hold else 0
        self.draw(None,self.textures['washing_hands'],720+sway,430,430,260,angle=sway*.2)
        self.draw('jug',v.sprites['jug'],1100,650,210,240,angle=-35 if self.wash_hold else 0)
        if self.wash_hold:
            arcade.draw_line(1000,650,730,450,(170,210,230,200),7)
            for j in range(7):
                yy=420-(v.clock*100+j*14)%55
                arcade.draw_circle_filled(730+(j-3)*16,yy,2,(210,233,241,150))
        # Reuse a front-rim strip of the SAME sprite as an occluder. Cuffs enter
        # behind the basin front instead of ending in mid-air inside it.
        basin=self.textures['wash_basin'];top=round(basin.height*.72)
        if not hasattr(self,'basin_front'):
            self.basin_front=basin.crop(0,top,basin.width,basin.height-top)
        q=min(700/basin.width,420/basin.height)
        cy=440+(basin.height/2-(top+(basin.height-top)/2))*q
        self.draw(None,self.basin_front,720,cy,basin.width*q,(basin.height-top)*q)
        v.header('First-person washstand | The girl waits in the separate dining room')
        arcade.draw_rect_filled(arcade.XYWH(720,155,1050,220),(20,22,26,230))
        vtext('Hands rinsed. Return to the kitchen.' if self.washed>=1 else 'Hold the jug to rinse your hands. Release to stop.',400,220,22)
        from scenes.royal_view import meter
        meter(470,170,500,self.washed,'Hand washing')
        v.button('Return to kitchen',550,90,340,48,'wash_done',self.washed>=1)

    def wash_click(self,x,y,button):
        if button==arcade.MOUSE_BUTTON_LEFT and self.hit(x,y)=='jug' and self.washed<1:self.wash_hold=True
        return True

    def finish_draw(self):
        v=self.v;self.regions.clear()
        self.draw(None,v.fill_background,720,450,1440,900)
        pot=v.sprites['royal_pot'];ph=440*pot.height/pot.width
        mx,my=1000,565+ph*.285
        arcade.draw_ellipse_filled(mx,my,298,64,(168,133,73))
        for index,name in enumerate(('onion','carrot')):
            for j,tex in enumerate(v.food_pieces[name]):
                a=index*2+j*2.399
                self.draw(None,tex,mx+math.sin(a)*105,my+math.cos(a)*12,22,14)
        self.draw('pot',pot,1000,565,440)
        for j in range(4):
            yy=my+25+(v.clock*28+j*20)%100
            arcade.draw_circle_filled(mx+math.sin(v.clock+j)*25,yy,8,(230,222,202,35))
        self.draw('salt',v.sprites['salt'],360,440,140,180)
        self.draw('ladle',v.simmer_sprites['ladle'],640,360,180,210,angle=-15)
        self.draw('bowl',v.sprites['empty_bowl'],870,290,250,170)
        if v.cook.served>0:self.draw('bowl',v.sprites['soup_bowl'],870,290,250,170,alpha=v.cook.served*255)
        if v.hold=='ladle':
            self.draw(None,v.simmer_sprites['ladle'],870,440,190,200,angle=-35)
            for j in range(5):arcade.draw_circle_filled(870+(j-2)*4,390-(v.clock*110+j*13)%60,2,(218,181,110,180))
        self.use_overlay()
        v.header('Final seasoning & serving | The familiar salt jar remains')
        instruction='Select salt, then click the pot.' if v.cook.stage=='returned' else ('Click the full bowl to carry it to the dining room.' if v.cook.served>=1 else 'Select ladle > pot, then hold over the bowl. Release to stop.')
        v.footer('Workstation',v.note if v.note_time>0 else instruction)
        from scenes.royal_view import meter
        meter(180,720,350,v.cook.served,'Bowl fill')

    def finish_click(self,x,y,button):
        v=self.v;key=self.hit(x,y)
        if self.motion:return
        if button==arcade.MOUSE_BUTTON_RIGHT:self.selected=None;self.loaded=False;v.hold=None;return
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        if key=='salt':
            if v.cook.stage=='returned':self.selected='salt';v.say('Salt selected. Click the pot to add the last spoon.')
            else:v.say('The final seasoning is already in the soup.')
        elif key=='pot' and self.selected=='salt' and v.cook.stage=='returned':
            self.animate('salt',v.sprites['salt'],(360,440),(1000,650),v.season)
        elif key=='ladle' and v.cook.stage=='serve':self.selected='ladle';v.say('Click the pot to load the ladle.')
        elif key=='pot' and self.selected=='ladle' and v.cook.stage=='serve':self.loaded=True;v.say('Ladle loaded. Hold over the bowl to pour.')
        elif key=='bowl' and self.selected=='ladle' and self.loaded and v.cook.stage=='serve' and v.cook.served<1:v.hold='ladle'
        elif key=='bowl' and v.cook.served>=1:
            self.stop_input();v.deliver()


def vtext(*args):
    # Late import avoids a circular import while RoyalKitchenView loads.
    from scenes.royal_view import text
    text(*args)
