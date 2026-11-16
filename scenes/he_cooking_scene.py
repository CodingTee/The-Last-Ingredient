"""A separate HE-only, sprite-based kitchen and empty-handed return scene."""
from __future__ import annotations
import json,math
from pathlib import Path
import arcade
from PIL import Image,ImageChops,ImageFilter
from arcade.types.rect import LRBT
from core.base_view import BaseGameView
from core.constants import ASSETS_DIR
from core.player import Player,FEET_OFFSET
from core.audio import AudioManager
from scenes.future_integrated_view import FOOTPRINTS,WORLD_W,WORLD_H,FutureLabView,bob_offset,get_future_lab_obstacles
from scenes.he_meal_state import HEMeal
from scenes.kitchen_shared import draw_console_chrome,advance_console

LOCAL_ART=Path(__file__).resolve().parents[1]/'assets'
ART=LOCAL_ART/'he_cooking' if (LOCAL_ART/'he_cooking').exists() else LOCAL_ART
POT=(538,461,400,310)
PAN=(1136,410,460,220)
PAN_FOOD_X=1067
BOWL=(830,246,245,150)
JUG=(175,454,100,108)
NOODLES=(175,442,120,85)
EGG=(175,434,58,68)
LADLE=(390,160,130,150)
SPATULA=(1220,160,130,150)
LIFT_BOWL=(175,461,*BOWL[2:])
SERVING={
    'serve_broth': ('SCOOP BROTH', 'ladle', 'ladle_full', (620,610), 'broth_to_bowl'),
    'serve_noodles': ('LIFT NOODLES', 'chopsticks', 'noodle_lift', (620,610), 'noodles_to_bowl'),
    'serve_egg': ('LIFT EGG', 'spatula', 'egg_spatula', (1160,495), 'egg_to_bowl'),
}
NEXT=(1390, 223.5, 278.7, 41.0)
CHOICES=((1292,490,90,92),(1390,490,90,92),(1488,490,90,92))
KEEP=(1390, 395, 278, 38)
ADJUST=(1390, 340, 278, 34)
SLIDER=(1390, 444, 254, 20)
# A moving band alone would complete itself; progress needs a fresh drag.
SWITCH=(1440,107,120,64)
HINT_RING=(1440,107,158.4,102.4)
HINT_ARROW=(1410,187,58,42)
# Decorative lab switch, sheared to the station's -39 deg perspective.
LAB_SWITCH=(410.5,525,14,20.2)
HOLO=(1330,506,484,730)
# Legacy click guard; keeps the pan and tools reachable after the resize.
HOLO_HIT=(1375,462,434,647)
HK=1.22
# Panel contents keep legacy coords; HB/HXY scale them into the bigger screen.
def HB(b):
    x,y,w,h=b
    return (HOLO[0]+(x-1390)*HK,HOLO[1]+(y-462)*HK,w*HK,h*HK)
def HXY(x,y):
    return (HOLO[0]+(x-1390)*HK,HOLO[1]+(y-462)*HK)
CYAN=(103, 231, 255);WHITE=(235, 245, 250);GOLD=(255, 212, 124);GREEN=(136, 242, 185);MUTED=(159, 187, 204)
STEPS={
'program':('H03 / THE QUIET LEFT BEHIND','Transit ration is optional. Skip to cook your own meal.'),
'choose':('01 / SELECT RECIPE','Configure the homestyle recipe: select water, noodles, and farm egg.'),
'recipe':('02 / CONFIRM RECIPE','Childhood Egg Noodle Soup: recipe blueprint confirmed.'),
'water':('H05 / POUR WATER','Dispense water from the kitchen control.'),
'heat_water':('HEAT THE WATER','Start heating. Keep 90-100 C for a gentle boil.'),
'add_noodles':('ADD NOODLES','Dispense noodles from the kitchen control.'),
'cook_noodles':('AUTOMATIC STIRRING','Start the robotic magnetic stirrer.'),
'add_egg':('A SEPARATE FRYING PAN','Dispense an egg from the kitchen control.'),
'crack_egg':('CRACK THE EGG','Tap the egg twice over the pan.'),
'fry_egg':('FRY THE EGG','Keep 130-165 C. A gently browned edge is fine.'),
'serve_broth':('ASSEMBLE / BROTH','Dip the ladle into the pot, then pour into the bowl.'),
'serve_noodles':('ASSEMBLE / NOODLES','Lift noodles from the pot into the bowl.'),
'serve_egg':('ASSEMBLE / EGG','Use the spatula to move the egg onto the noodles.'),
'presentation':('ADJUST PRESENTATION?','The edge is uneven. The meal is already enough.'),
'pickup':('NO MORE ADJUSTMENTS','Click the completed bowl to carry it.'),
'carry':('H06 / THE BOWL STAYS HERE','Walk to Consciousness Return.'),
'return':('EMPTY HANDS','Return to the chair. The bowl stays on the table.'),
'returning':('LEAVE THE BOWL IN THE FUTURE','Returning consciousness only...')
}

_GROUND_MASK=None
def ground_mask_rects(art,layers,cell=4):
    """Compile furniture alpha coverage into obstacle rectangles."""
    global _GROUND_MASK
    # One lab layout per process; reuse the rects on scene re-entry.
    if _GROUND_MASK is not None:return _GROUND_MASK
    gw,gh=math.ceil(WORLD_W/cell),math.ceil(WORLD_H/cell)
    mask=Image.new('L',(gw,gh),0)
    for l in layers:
        # Lounge pieces stay walkable on top; legacy FOOTPRINTS gate their front edge.
        if l.get('architecture_baked') or l.get('id') in ('sofa','coffee_table','return_chair'):continue
        p=art/l['file']
        if not p.exists():continue
        im=Image.open(p).convert('RGBA')
        im=im.resize((max(1,round(l['width']/cell)),max(1,round(l['height']/cell))),Image.LANCZOS)
        alpha=im.getchannel('A').point(lambda v:255 if v>60 else 0)
        tile=Image.new('L',(gw,gh),0)
        tile.paste(alpha,(round(l['x']/cell),round(l['y']/cell)))
        mask=ImageChops.lighter(mask,tile)
    mask=mask.filter(ImageFilter.MaxFilter(5))
    px=mask.load();rects=[]
    for gy in range(gh):
        run=None
        for gx in range(gw+1):
            on=gx<gw and px[gx,gy]>0
            if on and run is None:run=gx
            elif not on and run is not None:
                y2=WORLD_H-gy*cell;y1=WORLD_H-(gy+1)*cell
                # Player.update tests feet_y+8; widen the band past cell borders.
                rects.append((run*cell,gx*cell,y1+6,y2+10))
                run=None
    _GROUND_MASK=rects
    return rects

class HECookingScene(BaseGameView):
    def __init__(self,ending,initial_mode='lab'):
        if not getattr(ending,'h01_confirmed',False):
            raise ValueError('HE cooking requires an explicitly confirmed Abort Time Jump.')
        super().__init__()
        self.ending=ending
        self.meal=HEMeal()
        self.mode=initial_mode;self.keys=set();self.held=None
        self.mouse=(800,450);self.elapsed=0.;self.return_time=0.
        self.stirring=False;self.modal=None;self.nearest=None
        self.press_origin=None;self.dragging=False;self.ignore_release=False;self.adjusting_power=False
        self.audio=AudioManager();self._labels={}
        self.delivery_time=0.;self.last_tech_phase=None
        self.arm_motion="idle";self.arm_clock=0.
        self.bowl_delivered=False
        self.serve_motion=None
        self.serve_clock=0.
        self.serve_step=None
        self.pour_stage = 'idle'
        self.pour_clock = 0.
        self.water_level = 0.
        self.pour_held = False
        self.arm_ingredient = None
        self.console_open = (initial_mode == 'counter')
        self.console_hint = (initial_mode != 'counter')
        self.console_t = 0.
        self.console_log = []
        self.sprites={p.stem:arcade.Sprite(arcade.load_texture(p)) for p in ART.glob('*.png') if not p.stem.startswith('sheet_')}
        nutrient_art=ASSETS_DIR/'future_lab'/'nutrient'
        for name in ('counter_be','gantry','mold','press'):
            self.sprites[name]=arcade.Sprite(arcade.load_texture(nutrient_art/(name+'.png')))
        self.build_station_layers()
        self.station_swap=None
        self.unify_bowl_sprites()
        self.build_remaining_broth()
        self.lab_background=arcade.Sprite(arcade.load_texture(ASSETS_DIR/'future_lab/room_background.png'))
        self.layers=[]
        for l in json.loads((ASSETS_DIR/'future_lab/layout.json').read_text())['layers']:
            self.layers.append((l,arcade.Sprite(arcade.load_texture(ASSETS_DIR/'future_lab'/l['file']))))
        self.player=Player(690,300+FEET_OFFSET,'astronaut')
        # Unified HE collision mechanism
        self.obstacles=get_future_lab_obstacles([l for l,_ in self.layers])
        self.world_camera=None
        self.float_enabled=True
        self.table_shadow=arcade.load_texture(ASSETS_DIR/'future_lab/table_shadow.png')
        self.hologram=arcade.load_texture(ASSETS_DIR/'future_lab/hologram_analysis.png')
        self.steam=[arcade.Sprite(arcade.load_texture(ART/'steam.png')) for _ in range(6)]

    def on_show_view(self):
        super().on_show_view();self.fit()
    def fit(self):
        w,h=self.window.width,self.window.height
        self.scale=min(w/1600,h/900);self.ox=(w-1600*self.scale)/2;self.oy=(h-900*self.scale)/2
        aspect=w/h;vh=min(720,WORLD_H,WORLD_W/aspect);vw=vh*aspect
        if self.world_camera is None:self.world_camera=arcade.Camera2D(window=self.window)
        self.world_camera.viewport=LRBT(0,w,0,h)
        self.world_camera.projection=LRBT(-vw/2,vw/2,-vh/2,vh/2)
        self.vw,self.vh=vw,vh
        self.follow()
    def follow(self,dt=0.,snap=True):
        self._view_w,self._view_h=self.vw,self.vh
        FutureLabView._follow_camera(self,dt,snap)
    def on_resize(self,w,h):
        super().on_resize(w,h);self.cancel_hold();self.ignore_release=True;self.fit()
    def xy(self,x,y):return self.ox+x*self.scale,self.oy+y*self.scale
    def box(self,b,color=(10,27,41,238),border=None):
        x,y,w,h=b;r=arcade.XYWH(*self.xy(x,y),w*self.scale,h*self.scale)
        arcade.draw_rect_filled(r,color)
        if border:arcade.draw_rect_outline(r,border,2*self.scale)
    def text(self,t,x,y,size=17,color=WHITE,center=False,width=None,bold=False,anchor_y=None,anchor_x=None):
        if anchor_y is None:
            anchor_y = 'center' if center else 'baseline'
        if anchor_x is None:
            anchor_x = 'center' if center else 'left'
        key=(t,x,y,size,color,center,width,bold,anchor_y,anchor_x,self.window.width,self.window.height)
        if key not in self._labels:
            if len(self._labels)>300:self._labels.clear()
            self._labels[key]=arcade.Text(t,*self.xy(x,y),color,size*self.scale,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                width=int(width*self.scale) if width else 0,
                multiline=bool(width),
                font_name=('Segoe UI', 'Calibri', 'Arial'),
                bold=bold)
        self._labels[key].draw()
    def unify_bowl_sprites(self):
        from PIL import Image, ImageDraw, ImageFilter

        base = self.sprites['bowl_empty'].texture.image.convert('RGBA')
        # Each rectangle traces the inner surface in its source sprite.
        crops = {
            'bowl_broth': (42, 72, 556, 294),
            'bowl_noodles': (41, 65, 558, 293),
            'bowl_complete': (39, 48, 561, 312),
        }
        raw = self.sprites['dry_noodles'].texture.image.convert('RGBA')
        raw_mask = Image.new('L', (600,406))
        ImageDraw.Draw(raw_mask).polygon(
            [(158,51),(197,18),(255,11),(307,0),(396,11),(445,30),(481,63),
             (502,100),(509,143),(532,169),(534,205),(516,224),(529,253),
             (510,278),(470,286),(444,307),(393,315),(354,330),(288,335),
             (238,319),(191,321),(156,296),(124,280),(99,246),(69,221),
             (68,192),(87,167),(102,132),(104,104),(129,73)], fill=255)
        mask = raw_mask.resize(raw.size, Image.Resampling.LANCZOS)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        mask = Image.composite(mask, Image.new('L',raw.size),raw.getchannel('A'))
        ingredient = base.copy()
        ingredient.paste(raw.resize((510,345),Image.Resampling.LANCZOS),
                         (45,20),mask.resize((510,345),Image.Resampling.LANCZOS))
        self.sprites['raw_noodle_bowl'] = arcade.Sprite(arcade.Texture(ingredient))
        target = (45, 91, 555, 323)
        size = (target[2]-target[0], target[3]-target[1])
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).ellipse((3, 3, size[0]-4, size[1]-4), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        for name, crop in crops.items():
            contents = self.sprites[name].texture.image.crop(crop).resize(size, Image.Resampling.LANCZOS)
            bowl = base.copy()
            bowl.paste(contents, target[:2], mask)
            self.sprites[name] = arcade.Sprite(arcade.Texture(bowl))

    def sprite(self,name,b,angle=0,alpha=255,world=False):
        s=self.sprites[name];x,y,w,h=b
        scale=min(w/s.texture.width,h/s.texture.height)*(1 if world else self.scale)
        s.scale=scale
        if name in ('raw_egg','fried_egg') and not world:
            # Food lies in the same projected plane as the frying pan.
            s.width=w*self.scale;s.height=h*self.scale
        s.position=(x,y) if world else self.xy(x,y);s.angle=angle;s.alpha=alpha
        arcade.draw_sprite(s)
    def cover(self,s):
        w,h=self.window.width,self.window.height
        s.scale=max(w/s.texture.width,h/s.texture.height);s.position=(w/2,h/2);s.angle=0;s.alpha=255
        arcade.draw_sprite(s)
    @staticmethod
    def inside(x,y,b):
        cx,cy,w,h=b;return abs(x-cx)<=w/2 and abs(y-cy)<=h/2
    def do(self,action):
        ok=self.meal.act(action)
        if ok:
            if action=="start_stir" and self.arm_motion=="idle":
                self.arm_motion="extend";self.arm_clock=0.
            self.audio.play('sizzle' if action=='heat' and self.meal.phase=='fry_egg' else 'click')
        return ok

    def cancel_hold(self):
        self.pour_held = False
        if self.held=='egg_spatula':self.meal.egg_lifted=False
        self.held=None;self.dragging=False;self.adjusting_power=False
        self.press_origin=None

    def on_update(self,dt):
        if self.is_paused:return
        dt=min(dt,.05 if self.mode=='lab' else .1);self.elapsed+=dt
        advance_console(self,dt)
        if self.modal:return
        if self.mode=='counter':
            self.delivery_time=min(1.,self.delivery_time+dt*1.6) if self.meal.phase not in ('program','choose','recipe') else 0.
            old=self.meal.phase
            self.update_pour(dt)
            self.update_serving(dt)
            if self.station_swap is not None:
                self.station_swap=min(2.45,self.station_swap+dt)
            self.update_arm(dt)
            self.meal.update(dt,self.arm_motion=="stir")
            if self.meal.phase!=old:
                self.audio.play('sizzle' if self.meal.phase=='serve_broth' else 'boil')
                if self.meal.phase in ('add_noodles','add_egg'):
                    self.meal.feedback=STEPS[self.meal.phase][1]
        else:
            if self.meal.phase=='returning':
                self.return_time+=dt
                if self.return_time>=1.8:self.finish()
                return
            mx=int(bool(self.keys&{arcade.key.D,arcade.key.RIGHT}))-int(bool(self.keys&{arcade.key.A,arcade.key.LEFT}))
            my=int(bool(self.keys&{arcade.key.W,arcade.key.UP}))-int(bool(self.keys&{arcade.key.S,arcade.key.DOWN}))
            self.player.update(dt,mx,my,bounds=(125,1860,72+FEET_OFFSET,441+FEET_OFFSET),obstacles=self.obstacles)
            feet=self.player.y-FEET_OFFSET;edge=max(125,125+(feet-290)*1.2)
            clamped_x = max(edge,min(WORLD_W-edge,self.player.x))
            if clamped_x != self.player.x:
                self.player.x = clamped_x
                self.player.sprite.center_x = clamped_x
            self.follow(dt,snap=False)
            spots=[('kitchen',(390,345)),('chair',(1590,191))]
            if self.can_place_bowl():
                spots.append(('table',(1030,82)))
            def distance(spot):
                if spot[0]!='kitchen':
                    return math.hypot(self.player.x-spot[1][0],feet-spot[1][1])
                def segment(x1,y1,x2,y2):
                    dx,dy=x2-x1,y2-y1
                    t=max(0.,min(1.,((self.player.x-x1)*dx+(feet-y1)*dy)/(dx*dx+dy*dy)))
                    return math.hypot(self.player.x-(x1+t*dx),feet-(y1+t*dy))
                return min(segment(220,340,290,350),segment(290,350,470,470))
            best=min(spots,key=distance)
            self.nearest=best[0] if distance(best)<125 else None


    def draw_lab(self):
        self.world_camera.use()
        self.lab_background.position=(WORLD_W/2,WORLD_H/2)
        self.lab_background.width=WORLD_W;self.lab_background.height=WORLD_H
        arcade.draw_sprite(self.lab_background)
        for item,_ in self.layers:
            if item.get('architecture_baked') or item.get('architecture_shadow_baked'):continue
            contact=item.get('floor_contact')
            if contact:
                x,y,width=contact['x'],contact['y'],contact['width']
                arcade.draw_texture_rect(self.table_shadow,arcade.XYWH(x,y,width*1.35,18))
                arcade.draw_ellipse_filled(x,y,width,9,(10,19,34,145))
            footprint=FOOTPRINTS.get(item['id'])
            if footprint:
                x1,x2,y1,y2=footprint
                rect=arcade.XYWH(1030,136,367.2,80.2) if item['id']=='central_research_table' else arcade.XYWH((x1+x2)/2,y1+8,max(28,(x2-x1)*.88),min(45,max(18,(y2-y1)*.45)))
                arcade.draw_texture_rect(self.table_shadow,rect)
        inserted=False;feet=self.player.y-FEET_OFFSET
        for l,s in sorted(self.layers,key=lambda x:x[0]['depth_y'],reverse=True):
            if not inserted and feet>l['depth_y']:
                self.draw_player();inserted=True
            if l.get('architecture_baked'):continue
            dy=bob_offset(l,self.elapsed) if self.float_enabled else 0
            s.position=(l['x']+l['width']/2,WORLD_H-l['y']-l['height']/2-dy)
            s.width=l['width'];s.height=l['height'];arcade.draw_sprite(s)
            if l['id']=='central_research_table' and self.meal.bowl_placed:
                self.sprite('bowl_complete',(1030,285-dy,74,52),world=True)
                self.draw_steam(1030,307-dy,True)
            if l['id']=='cooking_station':
                x,y,w,h=LAB_SWITCH
                self.sprite('lab_switch',(x,y-dy,w,h),world=True)
        if not inserted:self.draw_player()
        dy=5*math.sin(self.elapsed*math.tau/3.6) if self.float_enabled else 0
        arcade.draw_texture_rect(self.hologram,arcade.XYWH(1121,WORLD_H-148.5-dy,366,183),alpha=225)
        # Station Visual Cue (Floating tailless yellow arrow)
        if self.nearest:
            station_targets = {'kitchen': (344, 576), 'chair': (1590, 233), 'table': (1030, 260)}
            if self.nearest in station_targets:
                tx, ty = station_targets[self.nearest]
                bob = 5.0 * math.sin(self.elapsed * 4.5)
                pulse = int(210 + 45 * math.sin(self.elapsed * 4.5))
                self.sprite('switch_hint_arrow', (tx, ty + bob, 42, 30), alpha=pulse, world=True)
        # The physical jump capsule is deliberately inactive in this committed HE scene.
        self.window.default_camera.use()
        hints={'kitchen':'[E] Cook','chair':'[E] Consciousness Return','table':'[E] Place bowl'}
        if self.nearest:
            hint=hints[self.nearest]
            self.text(hint,800,47,17,CYAN,True)

    def draw_player(self):
        self.player.draw(1.)
        if self.meal.carrying:
            self.sprite('bowl_complete',(self.player.x+24,self.player.y-49,43,32),world=True)

    def draw_steam(self,x,y,world=False):
        for i,s in enumerate(self.steam):
            f=(self.elapsed*.22+i/6)%1
            scale=(.08+.06*f)*(1 if world else self.scale)
            s.scale=scale;s.position=(x+math.sin(self.elapsed+i)*6,y+f*(65 if world else 105)) if world else self.xy(x+math.sin(self.elapsed+i)*12,y+f*105)
            s.alpha=int((1-f)*105);arcade.draw_sprite(s)

    def draw_counter(self):
        self.window.default_camera.use()
        self.cover(self.sprites['counter'])  # Fill outer margins without black bars.
        # The working surface and cookware must share one virtual coordinate plane.
        background=self.sprites['counter']
        background.position=self.xy(800,450)
        background.width=1600*self.scale;background.height=900*self.scale
        arcade.draw_sprite(background)
        m=self.meal;p=m.phase
        if self.station_swap is None or self.station_swap<2.45:
            self.draw_station_swap()
            self.draw_console()
            return
        # Vessel, broth and noodles are one coherent sprite with correct rim occlusion.
        pot_art = 'pot'
        if m.noodles and not m.noodles_served and not self.serving_carries('serve_noodles'):
            pot_art = 'pot_with_noodles'
        self.sprite(pot_art, POT)
        if pot_art == 'pot' and self.water_level:
            self.draw_pot_water(broth=m.noodles or m.noodles_served)
        self.sprite('pan', PAN)
        if self.pour_stage=='egg_tap':
            arcade.draw_ellipse_outline(*self.xy(1240,426),58*self.scale,17*self.scale,CYAN,2*self.scale)
        if m.egg_cracks>=2 and not m.egg_served and not self.serving_carries('serve_egg'):
            self.sprite('raw_egg',(PAN_FOOD_X,397,170,68),alpha=int(255*(1-min(1,m.egg_progress/5))))
            self.sprite('fried_egg',(PAN_FOOD_X,397,170,68),alpha=int(255*min(1,m.egg_progress/5)))
        if self.pour_stage=='egg_open':
            t=min(1.,max(0.,(self.pour_clock-.24)/.34))
            self.sprite('raw_egg',(PAN_FOOD_X,453-56*t,50+120*t,42))
        bowl='bowl_empty'
        if p=='serve_noodles':bowl='bowl_broth'
        elif p=='serve_egg':bowl='bowl_noodles'
        elif p in ('presentation','pickup'):bowl='bowl_complete'
        if self.bowl_delivered:
            self.sprite(bowl,BOWL)
        self.draw_ingredient_lift()
        self.draw_tech_station()
        self.draw_robot_tool()
        if m.temperature>65 or m.noodles:self.draw_steam(538,600)
        if m.egg_progress>0 and p=='fry_egg':self.draw_steam(1072,440)
        if p in ('presentation','pickup'):self.draw_steam(BOWL[0],BOWL[1]+50)
        self.draw_console()

    def build_station_layers(self):
        from PIL import Image, ImageDraw

        # The moving face is cut from the actual counter art in both configurations.
        x, top, right, bottom = 260, 458, 1370, 658
        size = (right-x, bottom-top)
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).polygon([(75,0),(size[0]-75,0),
                                     (size[0]-1,size[1]-1),(0,size[1]-1)], fill=255)
        interior = self.sprites['main_lift_interior'].texture.image.convert('RGBA')
        interior = interior.resize(size, Image.Resampling.LANCZOS)
        recess = Image.new('RGBA',size,(19,51,91,255))
        recess.alpha_composite(interior)
        for name in ('counter_be','counter'):
            scene = self.sprites[name].texture.image.convert('RGBA').resize(
                (1600,900), Image.Resampling.LANCZOS)
            face = scene.crop((x,top,right,bottom))
            face.putalpha(mask)
            scene.paste(recess,(x,top),mask)
            self.sprites[name+'_face'] = arcade.Sprite(arcade.Texture(face))
            self.sprites[name+'_recess'] = arcade.Sprite(arcade.Texture(scene))
        rim = Image.new('RGBA', size)
        edge = ImageDraw.Draw(rim)
        outline = [(76,2),(size[0]-76,2),(size[0]-4,size[1]-3),(3,size[1]-3),(76,2)]
        edge.line(outline, fill=(55,77,99,255), width=5, joint='curve')
        bevel = [(79,4),(size[0]-79,4),(size[0]-8,size[1]-5),(7,size[1]-5),(79,4)]
        edge.line(bevel, fill=(222,233,241,255), width=2, joint='curve')
        self.sprites['station_cutout_rim'] = arcade.Sprite(arcade.Texture(rim))
        self.station_face = ((x+right)/2,900-(top+bottom)/2,*size)

    def draw_station_swap(self):
        t=self.station_swap
        before=t is None or t<1.27
        name='counter_be' if before else 'counter'
        x,y,w,h=self.station_face
        if t is None:
            self.draw_station_layer(name,(800,450,1600,900))
            self.draw_synthesizer(0)
        else:
            self.draw_station_layer(name+'_recess',(800,450,1600,900))
            progress=min(1., t/.96) if before else max(0.,1-(t-1.27)/1.18)
            drop=550*progress*progress
            ctx=self.window.ctx
            previous=ctx.scissor
            cutoff=max(0,min(self.window.height-1,int(self.xy(0,y-h/2)[1])))
            try:
                ctx.scissor=(0,cutoff,self.window.width,self.window.height-cutoff)
                self.draw_station_layer(name+'_face',(x,y-drop,w,h))
                if before:
                    self.draw_synthesizer(drop)
                else:
                    for tool,(px,py,pw,ph) in (('pot',POT),('pan',PAN)):
                        self.sprite(tool,(px,py-drop,pw,ph))
            finally:
                ctx.scissor=previous
            if drop>2:
                self.draw_station_layer('station_cutout_rim',(x,y,w,h))
        self.draw_nutrient_idle_arm()

    def draw_synthesizer(self,drop):
        from scenes.future_nutrient_view import INST_X

        for name,y,w,h in (('gantry',480,650,470),('mold',345,555,260),('press',560,400,200)):
            self.sprite(name,(INST_X,y-drop,w,h))

    def draw_station_layer(self,name,bounds):
        x,y,w,h=bounds
        sprite=self.sprites[name]
        sprite.position=self.xy(x,y)
        sprite.width=w*self.scale
        sprite.height=h*self.scale
        arcade.draw_sprite(sprite)

    def draw_nutrient_idle_arm(self):
        self.draw_robot_arm()
        self.draw_robot_tool()

    def serving_carries(self, step):
        return self.serve_step == step and self.serve_motion == 'transfer'

    def start_serving(self):
        if self.serve_motion is not None or self.pour_stage != 'idle' or self.arm_motion != 'idle':
            return
        self.serve_step=self.meal.phase
        self.serve_motion='reach' if self.bowl_delivered else 'bowl_elevate'
        self.serve_clock=0.
        self.meal.feedback=('Moving the robot tool into position.' if self.bowl_delivered
                            else 'Bringing up a clean bowl.')

    def update_serving(self,dt):
        motion=self.serve_motion
        if motion is None:
            return
        self.serve_clock+=dt
        duration,next_motion={
            'bowl_elevate':(.93,'bowl_reach'), 'bowl_reach':(.8,'bowl_transfer'),
            'bowl_transfer':(.9,'bowl_home'), 'bowl_home':(.65,None),
            'reach':(.85,'scoop' if self.serve_step=='serve_broth' else 'transfer'),
            'scoop':(.72,'transfer'), 'pour':(.65,'home'),
            'transfer':(.95,'pour' if self.serve_step=='serve_broth' else 'home'), 'home':(.7,None),
        }[motion]
        if self.serve_clock<duration:
            return
        if motion=='bowl_transfer':
            self.bowl_delivered=True
            self.meal.feedback='Bowl ready. Select SCOOP BROTH.'
        elif motion=='pour' or (motion=='transfer' and self.serve_step!='serve_broth'):
            self.do(SERVING[self.serve_step][4])
        self.serve_motion=next_motion
        self.serve_clock=0.

    def serving_wrist(self,parked):
        bowl=(BOWL[0]+48,BOWL[1]+65)
        if self.serve_motion in ('transfer','pour','home'):
            tool=SERVING[self.serve_step][2]
            rotation=42 if tool=='ladle_full' else 0
            dx,dy=self.serving_food_offset(tool,rotation)
            bowl=(BOWL[0]-dx,BOWL[1]+24-dy+(23 if tool=='ladle_full' else 0))
        lift=(LIFT_BOWL[0]+48,LIFT_BOWL[1]+65)
        source=SERVING[self.serve_step][3]
        if self.serve_step=='serve_broth':
            # Position the wrist so the spoon bowl lands inside the pot at full dip.
            texture=self.sprites['ladle'].texture
            dx=(.19-.93)*142
            dy=(.21-.94)*142*texture.height/texture.width
            angle=math.radians(29)
            target_x,target_y=POT[0],550
            source=(target_x-dx*math.cos(angle)+dy*math.sin(angle),
                    target_y-dx*math.sin(angle)-dy*math.cos(angle))

        start,end,duration={
            'bowl_elevate':(parked,parked,1), 'bowl_reach':(parked,lift,.8),
            'bowl_transfer':(lift,bowl,.9), 'bowl_home':(bowl,parked,.65),
            'reach':(parked,source,.85), 'scoop':(source,source,.72), 'pour':(bowl,bowl,.65),
            'transfer':(source,bowl,.95), 'home':(bowl,parked,.7),
        }[self.serve_motion]
        t=min(1.,self.serve_clock/duration)
        t=t*t*(3-2*t)
        return tuple(a+(b-a)*t for a,b in zip(start,end))

    def update_arm(self,dt):
        if self.arm_motion=='idle':return
        self.arm_clock+=dt
        sequence={'extend':(1.,'swap'),'swap':(.4,'lower'),'lower':(.6,'stir'),
                  'raise':(.6,'retract'),'retract':(1.,'idle')}
        if self.arm_motion=='stir':
            if not self.meal.auto_stir:self.arm_motion='raise';self.arm_clock=0.
        elif self.arm_clock>=sequence[self.arm_motion][0]:
            self.arm_motion=sequence[self.arm_motion][1];self.arm_clock=0.

    def draw_ingredient_lift(self):
        stage=self.pour_stage
        t=self.pour_clock
        bowl_lift=self.serve_motion in ('bowl_elevate','bowl_reach')
        if self.serve_motion=='bowl_reach':
            self.sprite('bowl_empty',LIFT_BOWL)
            return
        if bowl_lift:
            stage='elevate'
            t=self.serve_clock
        noodle_bowl=self.arm_ingredient=='dry_noodles' and not bowl_lift
        if stage=='position' and noodle_bowl:
            self.sprite('bowl_empty',(175,421,137,76))
            return
        if stage=='pickup':
            if noodle_bowl:
                self.sprite('raw_noodle_bowl',(175,421,137,76))
                return
            bounds={'water_jug':JUG,'dry_noodles':NOODLES,'whole_egg':EGG}[self.arm_ingredient]
            x,y,w,h=bounds
            arcade.draw_ellipse_filled(*self.xy(x,y-h/2+3),w*.65*self.scale,9*self.scale,(65,43,25,85))
            if self.arm_ingredient=='water_jug':
                self.draw_lift_jug()
            else:
                self.sprite(self.arm_ingredient,bounds)
            return
        if stage=='elevate':
            opening=min(1.,t/.28)
            rise=max(0.,min(1.,(t-.28)/.65))
        elif stage in ('plate_park','shell_park'):
            opening=min(1.,max(0.,(1.03-t)/.28))
            rise=max(0.,1-t/.68)
        elif stage=='park':
            opening=max(0.,min(1.,(t-.30)/.18,(1.21-t)/.28))
            rise=max(0.,min(1.,1-(t-.48)/.45))
            if t<=.30:
                self.draw_lift_jug(empty=True)
                return
        else:
            return

        ctx=self.window.ctx
        original_scissor=ctx.scissor
        width,height=self.window.width,self.window.height
        left,bottom=self.xy(69,370)
        right,top=self.xy(281,430)
        middle=(top+bottom)/2
        half_gap=(top-bottom)*opening/2
        lower_edge=middle-half_gap
        upper_edge=middle+half_gap
        surface_alpha=int(255*min(1.,(1-rise)*8))

        def clip_hatch(low,high):
            ctx.scissor=(int(left),int(low),max(1,int(right-left)),max(1,int(high-low)))

        try:
            if opening>0 and surface_alpha:
                clip_hatch(lower_edge,upper_edge)
                self.sprite('small_lift_interior',(175,400,212,60),alpha=surface_alpha)
                if rise>0:
                    self.sprite('lift_cover',(175,400-131*(1-rise),212,60),
                                alpha=surface_alpha)
                if opening<1:
                    # Each leaf retreats into its own end of the hatch.
                    leaf_travel=30*opening
                    clip_hatch(bottom,lower_edge)
                    self.sprite('lift_door_lower',(175,385-leaf_travel,212,30),alpha=surface_alpha)
                    clip_hatch(upper_edge,top)
                    self.sprite('lift_door_upper',(175,415+leaf_travel,212,30),alpha=surface_alpha)

            if rise>0:
                cutoff=max(0,int(self.xy(0,371)[1]))
                ctx.scissor=(0,cutoff,width,max(1,height-cutoff))
                bounds=LIFT_BOWL if bowl_lift else {
                    'water_jug':JUG,'dry_noodles':NOODLES,'whole_egg':EGG
                }[self.arm_ingredient]
                x,y,w,h=bounds
                art='bowl_empty' if bowl_lift else self.arm_ingredient
                displacement=131*(1-rise)
                if noodle_bowl:
                    bowl='bowl_empty' if stage=='plate_park' else 'raw_noodle_bowl'
                    self.sprite(bowl,(175,421-displacement,137,76))
                elif stage=='shell_park':
                    self.sprite('lift_tray',(175,401-displacement,172,43))
                    self.sprite('shells',(175,429-displacement,65,54))
                elif art=='water_jug':
                    self.draw_lift_jug(displacement,empty=stage=='park')
                elif stage!='plate_park':
                    self.sprite(art,(x,y-displacement,w,h))
                if surface_alpha:
                    ctx.scissor=original_scissor
                    self.sprite('lift_front_edge',(175,374.5,212,9),alpha=surface_alpha)
        finally:
            ctx.scissor=original_scissor

    def ingredient_wrist(self):
        if self.arm_ingredient == 'dry_noodles':
            return (NOODLES[0],NOODLES[1]+63)
        if self.arm_ingredient == 'whole_egg':
            return (EGG[0],EGG[1]+72)
        return (JUG[0]+36,JUG[1]+62)

    def ingredient_destination(self):
        if self.arm_ingredient == 'dry_noodles':
            return (POT[0],650)
        if self.arm_ingredient == 'whole_egg':
            return (1240,522)
        return (630,692)

    def update_pour(self,dt):
        stage=self.pour_stage
        if stage=='idle':return
        self.pour_clock+=dt
        if stage=='elevate' and self.pour_clock>=.93:
            self.pour_stage='pickup'
            self.pour_clock=0.
            self.meal.feedback='The arm is collecting the ingredient.'
        elif stage=='pickup' and self.pour_clock>=.8:
            self.pour_stage='position'
            self.pour_clock=0.
            self.meal.feedback='The arm is moving the ingredient into place.'
        elif stage=='position' and self.pour_clock>=.8:
            if self.arm_ingredient == 'water_jug':
                self.pour_stage='ready'
                self.meal.feedback='Hold to pour, then release at the gold mark.'
            else:
                self.do('egg_to_pan' if self.arm_ingredient=='whole_egg' else 'add_noodles')
                self.pour_stage='egg_tap' if self.arm_ingredient=='whole_egg' else 'plate_park'
                self.pour_clock=0.
                if self.pour_stage=='egg_tap':
                    self.meal.feedback='The robot is cracking the egg.'
        elif stage=='ready' and self.pour_held:
            self.water_level=min(1.,self.water_level+dt*.48)
        elif stage=='return' and self.pour_clock>=.8:
            self.pour_stage='set_down'
            self.pour_clock=0.
            self.meal.feedback='Setting the empty jug onto the lift.'
        elif stage=='set_down' and self.pour_clock>=.3:
            self.pour_stage='park'
            self.pour_clock=0.
            self.meal.feedback='Retracting the lift.'
        elif stage=='egg_tap' and self.pour_clock>=.52:
            self.do('crack')
            self.pour_stage='egg_center'
            self.pour_clock=0.
        elif stage=='egg_center' and self.pour_clock>=.55:
            self.pour_stage='egg_open'
            self.pour_clock=0.
            self.meal.feedback='The robot is opening the shell over the pan.'
        elif stage=='egg_open' and self.pour_clock>=.62:
            self.do('crack')
            self.pour_stage='shell_return'
            self.pour_clock=0.
        elif stage=='shell_return' and self.pour_clock>=.8:
            self.pour_stage='shell_park'
            self.pour_clock=0.
        elif ((stage=='park' and self.pour_clock>=1.22)
              or (stage in ('plate_park','shell_park') and self.pour_clock>=1.03)):
            self.pour_stage='idle'
            if stage=='park':self.do('pour_water')

    def arm_pose(self):
        mode=self.arm_motion;t=self.arm_clock
        def ease(x):
            x=max(0.,min(1.,x));return x*x*(3-2*x)
        if self.serve_motion is not None:
            wrist=self.serving_wrist((980,560))
            return (1200,685),((1200+wrist[0])/2,715),wrist
        if self.pour_stage!='idle':
            parked=(980,560)
            pickup=self.ingredient_wrist()
            over_pot=self.ingredient_destination()
            amount=ease(self.pour_clock/.8)
            egg_center=(PAN_FOOD_X,520)
            if self.pour_stage=='egg_tap':
                dip=24*math.sin(math.pi*min(1,self.pour_clock/.52))
                wrist=(over_pot[0],over_pot[1]-dip)
                return (1200,685),((1200+wrist[0])/2,715),wrist
            if self.pour_stage=='egg_center':
                amount=ease(self.pour_clock/.55)
            start,end={
                'elevate':(parked,parked),
                'pickup':(parked,pickup),
                'position':(pickup,over_pot),
                'ready':(over_pot,over_pot),
                'return':(over_pot,pickup),
                'set_down':(pickup,pickup),
                'park':(pickup,parked),
                'plate_park':(over_pot,parked),
                'egg_center':(over_pot,egg_center),
                'egg_open':(egg_center,egg_center),
                'shell_return':(egg_center,pickup),
                'shell_park':(pickup,parked),
            }[self.pour_stage]
            wrist=tuple(a+(b-a)*amount for a,b in zip(start,end))
            return (1200,685),((1200+wrist[0])/2,715),wrist
        reach=ease(t) if mode=='extend' else 1-ease(t) if mode=='retract' else 0. if mode=='idle' else 1.
        lower=ease(t/.6) if mode=='lower' else 1-ease(t/.6) if mode=='raise' else 1. if mode=='stir' else 0.
        wrist=(980-442*reach,560+136*reach-20*lower)
        if mode in ('lower','stir','raise'):
            orbit=min(1.,t/.30) if mode=='stir' else 0.
            phase=t*4.5
            wrist=(wrist[0]+38*orbit*math.sin(phase),
                   wrist[1]+8*orbit*(1-math.cos(phase)))
        elbow=(1100-230*reach,640+35*reach)
        return (1200,685),elbow,wrist

    def arm_segment(self,a,b):
        # Same unscaled joint size at both ends; rails extend between fixed pivots.
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        sprite=self.sprites['arm_link'];sprite.position=self.xy((a[0]+b[0])/2,(a[1]+b[1])/2)
        sprite.width=(length+28)*self.scale;sprite.height=48*self.scale
        sprite.angle=-math.degrees(math.atan2(dy,dx));sprite.alpha=255
        arcade.draw_sprite(sprite)

    def draw_robot_arm(self):
        mount,elbow,wrist=self.arm_pose()
        self.sprite('arm_mount',(*mount,150,175))
        self.arm_segment(mount,elbow);self.arm_segment(elbow,wrist)

    def pot_water_geometry(self):
        level = self.water_level
        return 538, 516 + 19 * level, 82 + 33 * level, 14 + 18 * level

    def draw_pot_water(self, broth=False):
        cx, cy, rx, ry = self.pot_water_geometry()
        if broth:
            self.draw_remaining_broth()
            return
        # Keep the whole ellipse inside the curved inner lip at every fill level.
        for inset in range(9):
            fraction = inset / 8
            radius = 1 - .38 * fraction
            color = (int(32+32*fraction), int(88+43*fraction), int(128+46*fraction))
            arcade.draw_ellipse_filled(*self.xy(cx, cy),
                                       2*rx*radius*self.scale, 2*ry*radius*self.scale, color)
        if self.pour_stage == 'ready' and self.pour_held and self.water_level < 1:
            for offset in (0, .5):
                phase = (self.elapsed*2.4+offset)%1
                arcade.draw_ellipse_outline(*self.xy(548, max(511, cy)),
                                            (8+50*phase)*self.scale, (3+13*phase)*self.scale,
                                            (169,222,244,int(155*(1-phase))), self.scale)

    def build_remaining_broth(self):
        from PIL import Image, ImageDraw

        surface=Image.new('RGBA',(700,518))
        draw=ImageDraw.Draw(surface)
        back,front=[],[]
        for x in range(-224,225,4):
            liquid_depth=72*math.sqrt(max(0.,1-(x/225)**2))
            rim_depth=86*math.sqrt(max(0.,1-(x/235)**2))
            top=max(122-liquid_depth,99-rim_depth)
            bottom=min(122+liquid_depth,99+rim_depth)
            if bottom>=top:
                back.append((350+x,top))
                front.append((350+x,bottom))
        draw.polygon(back+front[::-1],fill=(158,101,31,255))
        for index in range(10):
            fraction=index/9
            rx,ry=190*(1-.5*fraction),55.5*(1-.5*fraction)
            draw.ellipse((350-rx,121-ry,350+rx,121+ry),
                         fill=(174+int(45*fraction),111+int(42*fraction),34+int(22*fraction),255))
        self.sprites['remaining_broth']=arcade.Sprite(arcade.Texture(surface))

    def draw_remaining_broth(self):
        px,py,width,height=POT
        texture=self.sprites['pot'].texture
        scale=min(width/texture.width,height/texture.height)
        sprite=self.sprites['remaining_broth']
        sprite.position=self.xy(px,py)
        sprite.width=texture.width*scale*self.scale
        sprite.height=texture.height*scale*self.scale
        arcade.draw_sprite(sprite)

    def draw_lift_jug(self, displacement=0., empty=False):
        name='jug_empty' if empty else 'water_jug'
        x,y,width,height=JUG
        self.sprite(name,(x,y-displacement,width,height))

    def draw_gripped_jug(self, wrist):
        pouring = self.pour_stage == 'ready' and self.pour_held and self.water_level < 1.
        angle = -32 if pouring else 0
        name='jug_empty' if self.pour_stage in ('return','set_down') else 'water_jug'
        texture=self.sprites[name].texture
        scale=min(JUG[2]/texture.width,JUG[3]/texture.height)
        width,height=texture.width*scale,texture.height*scale
        pickup=self.ingredient_wrist()
        dx,dy=JUG[0]-pickup[0],JUG[1]-pickup[1]
        radians=math.radians(-angle)
        cos_a,sin_a=math.cos(radians),math.sin(radians)
        x=wrist[0]+dx*cos_a-dy*sin_a
        y=wrist[1]+dx*sin_a+dy*cos_a
        self.sprite(name,(x,y,width,height),angle=angle)
        grip_x,grip_y=width*.28,height*.21
        handle=(x+grip_x*cos_a-grip_y*sin_a,y+grip_x*sin_a+grip_y*cos_a)
        arcade.draw_line(*self.xy(*wrist),*self.xy(*handle),(30,57,84),12*self.scale)
        arcade.draw_circle_filled(*self.xy(*handle),8*self.scale,(86,202,230))
        if pouring:
            _, surface_y, _, _ = self.pot_water_geometry()
            landing = max(511, surface_y)
            # Pixel landmark on the left lip, measured in the unrotated jug.
            lip_x,lip_y=-.47*width,.40*height
            spout=(x+lip_x*cos_a-lip_y*sin_a,y+lip_x*sin_a+lip_y*cos_a)
            points=[]
            for index in range(19):
                t=index/18
                px=spout[0]+(548-spout[0])*t
                py=spout[1]+(landing-spout[1])*(.3*t+.7*t*t)
                points.append(self.xy(px,py))
            arcade.draw_line_strip(points,(94,192,235,190),7*self.scale)
            arcade.draw_line_strip(points,(213,244,255,220),2*self.scale)

    SERVING_PIVOTS={
        'ladle':(.93,.94), 'ladle_full':(.92,.95),
        'noodle_lift':(.94,.92), 'spatula':(.93,.95), 'egg_spatula':(.93,.95),
    }

    def serving_food_offset(self,tool,rotation):
        food_x,food_y={'ladle_full':(.27,.25),'noodle_lift':(.25,.24),
                       'egg_spatula':(.34,.29)}[tool]
        pivot_x,pivot_y=self.SERVING_PIVOTS[tool]
        texture=self.sprites[tool].texture
        dx=(food_x-pivot_x)*142
        dy=(food_y-pivot_y)*142*texture.height/texture.width
        angle=math.radians(rotation)
        return dx*math.cos(angle)-dy*math.sin(angle),dx*math.sin(angle)+dy*math.cos(angle)

    def draw_serving_head(self, wrist):
        x,y=wrist
        motion=self.serve_motion
        _,empty,loaded,_,_=SERVING[self.serve_step]
        carrying=motion in ('transfer','pour')
        if empty=='chopsticks' and not carrying:
            for offset in (0,-9):
                start=self.xy(x,y+offset)
                tip=self.xy(x-114,y-42+offset)
                arcade.draw_line(*start,*tip,(18,45,80),7*self.scale)
                arcade.draw_line(*start,*tip,(67,166,204),2*self.scale)
        else:
            tool=loaded if carrying else empty
            pivot_x,pivot_y=self.SERVING_PIVOTS[tool]
            texture=self.sprites[tool].texture
            width=142
            height=width*texture.height/texture.width
            rotation=0.
            if motion=='scoop':
                rotation=29*math.sin(math.pi*min(1,self.serve_clock/.72))
            elif motion=='pour':
                rotation=42*math.sin(math.pi*min(1,self.serve_clock/.65))
            dx,dy=(.5-pivot_x)*width,(.5-pivot_y)*height
            angle=math.radians(rotation)
            cos_a,sin_a=math.cos(angle),math.sin(angle)
            center=(x+dx*cos_a-dy*sin_a,y+dx*sin_a+dy*cos_a)
            self.sprite(tool,(*center,width,height),angle=-rotation)
            if motion=='pour' and rotation>30:
                dx,dy=self.serving_food_offset(tool,rotation)
                arcade.draw_line(*self.xy(x+dx,y+dy-6),*self.xy(BOWL[0],BOWL[1]+24),
                                 (227,174,75,210),5*self.scale)
        arcade.draw_circle_filled(*self.xy(x,y),10*self.scale,(24,49,76))
        arcade.draw_circle_outline(*self.xy(x,y),10*self.scale,(100,206,238),2*self.scale)

    def draw_robot_tool(self):
        _,_,wrist=self.arm_pose();mode=self.arm_motion
        motion=self.serve_motion
        if motion=='bowl_transfer':
            self.sprite('bowl_empty',(wrist[0]-48,wrist[1]-65,*BOWL[2:]))
        if motion in ('reach','scoop','transfer','pour','home'):
            self.draw_serving_head(wrist)
            return
        if self.pour_stage=='position' and self.arm_ingredient=='dry_noodles':
            self.sprite('noodle_lift',(wrist[0]-48,wrist[1]-54,112,91))
            return
        if self.pour_stage in ('position','ready','return','set_down',
                               'egg_tap','egg_center','egg_open','shell_return'):
            if self.arm_ingredient=='water_jug':
                self.draw_gripped_jug(wrist)
                return
            if self.arm_ingredient=='whole_egg':
                opened=self.pour_stage=='shell_return' or (self.pour_stage=='egg_open' and self.pour_clock>.24)
                self.sprite('shells' if opened else 'whole_egg',(wrist[0],wrist[1]-67,58,60))
        stir=mode in ('lower','stir','raise') or (mode=='swap' and self.arm_clock>=.2)
        if mode=='idle':
            self.sprite('arm_grip',(wrist[0],wrist[1]-27,64,72))
            for x,y in self.arm_pose()[1:]:
                arcade.draw_circle_filled(*self.xy(x,y),9*self.scale,(24,49,76))
                arcade.draw_circle_outline(*self.xy(x,y),9*self.scale,(100,206,238),2*self.scale)
            return
        height=145 if stir else 78
        name='arm_stir' if stir else 'arm_grip'
        alpha=int(abs(self.arm_clock-.2)*1275) if mode=='swap' else 255
        bounds=(wrist[0],wrist[1]-height/2,78,height)
        if not stir or mode=='swap':
            self.sprite(name,bounds,alpha=min(255,alpha))
            return
        # Clip only the tip below the broth, leaving the wrist and shaft in front.
        ctx=self.window.ctx
        previous=ctx.scissor
        surface_y=542
        cutoff=max(0,min(self.window.height-1,int(self.xy(0,surface_y)[1])))
        try:
            ctx.scissor=(0,cutoff,self.window.width,self.window.height-cutoff)
            self.sprite(name,bounds)
        finally:
            ctx.scissor=previous

    def draw_tech_station(self):
        m=self.meal;p=m.phase
        # Mount stays fixed against the frontal backsplash. Never bob the wall plate.
        self.draw_robot_arm()

    def draw_console(self):
        m = self.meal
        p = m.phase
        if not draw_console_chrome(self):
            return

        # 1. TOP HEADER (Standard 4-tier layout matching BE)
        self.text('FUTURE LAB · CULINARY SYNTHESIZER', 1330, 830, 11, CYAN, center=True)
        titles = {
            'program': '00 / TRANSIT RATION OVERRIDE',
            'choose': '01 / SELECT RECIPE',
            'recipe': '02 / CONFIRM RECIPE',
            'water': '03 / DISPENSE WATER',
            'heat_water': '04 / HEAT WATER',
            'add_noodles': '05 / DISPENSE NOODLES',
            'cook_noodles': '06 / AUTOMATIC STIRRING',
            'add_egg': '07 / FRYING STATION',
            'crack_egg': '08 / CRACK THE EGG',
            'fry_egg': '09 / FRY THE EGG',
            'serve_broth': '10 / ASSEMBLE BROTH',
            'serve_noodles': '11 / ASSEMBLE NOODLES',
            'serve_egg': '12 / ASSEMBLE EGG',
            'presentation': '13 / FINAL PRESENTATION',
            'pickup': '14 / PREPARATION COMPLETE',
        }
        step_title = titles.get(p, STEPS.get(p, ('', ''))[0].split(' / ')[-1])
        self.text(step_title, 1330, 796, 17, WHITE, center=True)
        # Cyan divider line (identical to BE)
        self.box((1330, 775, 410, 2), (103, 231, 255, 120))

        # 2. CENTRAL CONTENT CARD (390 x 370, matching BE)
        card_border = GOLD if p in ('recipe', 'presentation') else CYAN
        self.box((1330, 545, 390, 370), (10, 30, 48, 160), card_border)

        label = None

        if p == 'program':
            self.text('MILITARY TRANSIT RATION', 1330, 702, 15, CYAN, center=True, bold=True, anchor_y='center')
            self.text('Active Formula: High-Density Nutrient Block', 1330, 680, 11, MUTED, center=True, anchor_y='center')
            self.box((1330, 580, 350, 96), (14, 34, 52, 200), (45, 78, 102))
            self.text('Default transit synthesis ready.', 1330, 600, 13, WHITE, center=True, anchor_y='center')
            self.text('Contains neurotoxin formulation for physical jump.', 1330, 565, 11, MUTED, center=True, anchor_y='center')
            self.box((1330, 480, 350, 34), (20, 55, 42, 220), GREEN)
            self.text('✓ NEURO-COMPOUND: EXCLUDED IN HOMESTYLE MODE', 1330, 480, 10, GREEN, center=True, bold=True, anchor_y='center')
            self.text('Skip military synthesis to cook your own warm meal with natural ingredients.', 1330, 410, 12, WHITE, center=True, width=330, anchor_y='center')
            label = 'SKIP NUTRIENT BLOCK'

        elif p == 'choose':
            # 1. Upper Section: Finished Dish Holographic Preview
            self.text('CHILDHOOD EGG NOODLE SOUP', 1330, 706, 15, GOLD, center=True, bold=True, anchor_y='center')
            self.text('ARCHIVE RECIPE: HOMESTYLE · UNALTERED', 1330, 690, 10, MUTED, center=True, anchor_y='center')

            # Finished Noodle Bowl Image Preview (compact size to prevent badge overlap)
            self.sprite('bowl_complete', (1330, 635, 130, 90))

            # Status Badge under Preview
            all_selected = (m.selected == {'water', 'noodles', 'egg'})
            if all_selected:
                self.box((1330, 576, 280, 20), (20, 55, 42, 220), GREEN)
                self.text('✓ NATURAL INGREDIENTS CONFIRMED', 1330, 576, 10, GREEN, center=True, bold=True, anchor_y='center')
            else:
                self.box((1330, 576, 280, 20), (28, 48, 64, 200), CYAN)
                self.text(f'SELECT INGREDIENTS ({len(m.selected)}/3)', 1330, 576, 10, CYAN, center=True, bold=True, anchor_y='center')

            # Subtle Divider Line between Preview and Components
            self.box((1330, 560, 360, 1), (45, 78, 102))

            # 2. Lower Section: 4 Interactive Component Slots (compact names to guarantee 40-70px gaps)
            slots = [
                ('water', 'SPRING WATER', 'RESERVOIR READY'),
                ('noodles', 'WHEAT NOODLES', 'NATURAL WHEAT'),
                ('egg', 'FARM EGG', 'ORGANIC PROTEIN'),
            ]
            slot_y = (535, 495, 455)
            for idx, (key, name, tag) in enumerate(slots):
                sy = slot_y[idx]
                selected = key in m.selected
                if selected:
                    bg = (20, 55, 42, 220)
                    border = GREEN
                    col_l = WHITE
                    col_r = GREEN
                    prefix = '[✓]'
                else:
                    bg = (14, 34, 52, 200)
                    border = (45, 80, 105)
                    col_l = MUTED
                    col_r = GOLD
                    prefix = '[○]'
                    tag = 'CLICK TO ADD'

                self.box((1330, sy, 360, 34), bg, border)
                self.text(f'{prefix}  0{idx + 1}. {name}', 1165, sy, 11, col_l, bold=True, anchor_y='center')
                self.text(tag, 1495, sy, 10, col_r, bold=selected, anchor_y='center', anchor_x='right')

            # Slot 4: Explicit Neuro-Compound Exclusion
            self.box((1330, 415, 360, 34), (16, 45, 42, 220), GREEN)
            self.text('[✕]  04. NEURO-COMPOUND', 1165, 415, 11, GREEN, bold=True, anchor_y='center')
            self.text('EXCLUDED · 0 mg', 1495, 415, 10, GREEN, bold=True, anchor_y='center', anchor_x='right')

            self.text('Click components to toggle • Pure organic rations', 1330, 380, 10, MUTED, center=True, anchor_y='center')
            label = 'CONFIRM RECIPE' if all_selected else 'SELECT ALL 3 INGREDIENTS'

        elif p == 'recipe':
            self.text('CHILDHOOD EGG NOODLE SOUP', 1330, 706, 15, GOLD, center=True, bold=True, anchor_y='center')
            self.text('ARCHIVE RECIPE: HOMESTYLE · UNALTERED', 1330, 690, 10, MUTED, center=True, anchor_y='center')

            self.sprite('bowl_complete', (1330, 635, 130, 90))

            self.box((1330, 576, 280, 20), (20, 55, 42, 220), GREEN)
            self.text('✓ BLUEPRINT CONFIRMED · READY', 1330, 576, 10, GREEN, center=True, bold=True, anchor_y='center')

            self.box((1330, 560, 360, 1), (45, 78, 102))

            # Quote box
            self.box((1330, 495, 360, 80), (14, 32, 48, 190), (45, 78, 102))
            self.text('"A bowl for the version of me sitting alone in the dark.\nEat first. We can work out tomorrow when it comes."',
                      1330, 495, 12, WHITE, center=True, width=340, anchor_y='center')

            # Formula components badge
            self.box((1330, 425, 360, 32), (16, 45, 42, 220), GREEN)
            self.text('• Spring Water  • Hand-pulled Noodles  • Farm Egg', 1330, 425, 11, GREEN, center=True, bold=True, anchor_y='center')

            self.text('Induction cooking modules ready for stockpot swap.', 1330, 380, 10, MUTED, center=True, anchor_y='center')
            label = 'BEGIN COOKING'

        elif p == 'water':
            self.text('BROTH VESSEL · WATER DISPENSER', 1330, 702, 14, CYAN, center=True)
            if self.station_swap is not None and self.station_swap < 2.45:
                prog = min(1.0, self.station_swap / 2.45)
                self.text('SWAPPING SYNTHESIZER MODULES...', 1330, 630, 15, CYAN, center=True)
                self.box((1330, 565, 310, 16), (30, 50, 66))
                self.box((1175 + 155 * prog, 565, 310 * prog, 16), CYAN)
                self.text('Transitioning from compression mold to induction stockpot.', 1330, 480, 12, MUTED, center=True, width=330)
            elif self.pour_stage == 'idle':
                self.text('AWAITING WATER CONTAINER', 1330, 630, 16, WHITE, center=True)
                self.text('Click button below to elevate pure water container from storage.', 1330, 540, 13, MUTED, center=True, width=330)
                label = 'DISPENSE WATER'
            elif self.pour_stage == 'ready':
                self.text(f'WATER LEVEL: {int(self.water_level * 100)}%', 1330, 640, 17, CYAN, center=True)
                ready = self.water_level >= 0.9
                bar_col = GREEN if ready else (60, 197, 224)
                self.box((1330, 565, 310, 20), (30, 50, 66))
                fill = 310 * min(1.0, self.water_level)
                if fill > 0:
                    self.box((1175 + fill / 2, 565, fill, 20), bar_col)
                self.box((1175 + 310 * 0.9, 565, 4, 28), GOLD)
                self.text('TARGET: 90% – 100% CAPACITY', 1330, 520, 11, GOLD if not ready else bar_col, center=True, bold=True)
                if self.pour_held:
                    label = 'RELEASE NOW' if ready else ('GET READY TO RELEASE' if self.water_level >= 0.72 else 'KEEP HOLDING...')
                else:
                    label = 'HOLD BUTTON TO POUR'
            else:
                self.text('WATER DISPENSED', 1330, 630, 16, GREEN, center=True)
                self.text('Water measured. Returning container to storage.', 1330, 540, 13, MUTED, center=True, width=330)

        elif p == 'heat_water':
            self.text('INDUCTION HEATING · STOCKPOT', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text(f'{m.temperature:.0f} °C', 1330, 648, 30, GREEN if (90 <= m.temperature <= 100) else WHITE, center=True, bold=True, anchor_y='center')
            self.text('TARGET: 90°C – 100°C (GENTLE SIMMER)', 1330, 608, 11, GOLD, center=True, bold=True, anchor_y='center')
            self.box(HB(SLIDER), (38, 62, 78))
            low, high, power_span = 90, 100, 100
            band_start = (low - 22) / power_span
            band_end = (high - 22) / power_span
            self.box(HB((1265 + 125 * (band_start + band_end), 444, 250 * (band_end - band_start), 20)), (40, 136, 106))
            self.box(HB((1265 + 250 * m.power, 444, 5, 32)), GOLD)
            self.text(f'POWER OUTPUT: {m.power:.0%}', 1330, 448, 12, WHITE, center=True, anchor_y='center')
            progress = m.boil_progress
            if 90 <= m.temperature <= 100:
                self.text(f'SIMMER PROGRESS: {progress:.1f} / 3.0 s', 1330, 410, 13, GREEN, center=True, bold=True, anchor_y='center')
            else:
                self.text('DRAG MARKER INTO GREEN ZONE TO SIMMER', 1330, 410, 11, MUTED, center=True, anchor_y='center')
            if self.pour_stage == 'idle':
                label = 'HEATING...' if m.heating else 'START HEATING'

        elif p == 'add_noodles':
            self.text('BROTH VESSEL · NOODLE DISPENSER', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text('HAND-PULLED FLOUR NOODLES', 1330, 635, 17, WHITE, center=True, anchor_y='center')
            self.text('Broth is at rolling simmer.\nReady to dispense noodles into pot.', 1330, 545, 13, MUTED, center=True, width=330, anchor_y='center')
            label = 'DISPENSE NOODLES'

        elif p == 'cook_noodles':
            self.text('MAGNETIC STIRRING CYCLE', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text(f'{m.noodle_progress:.1f} / 4.0 s', 1330, 635, 28, CYAN, center=True, bold=True, anchor_y='center')
            prog = min(1.0, m.noodle_progress / 4.0)
            self.box((1330, 565, 310, 16), (30, 50, 66))
            self.box((1175 + 155 * prog, 565, 310 * prog, 16), GREEN if prog >= 1.0 else CYAN)
            self.text('Robotic stirrer maintains gentle agitation to cook evenly without breakage.',
                      1330, 470, 12, MUTED, center=True, width=330, anchor_y='center')
            if self.pour_stage == 'idle':
                label = 'STIRRING...' if m.auto_stir else 'START ROBOTIC STIR'

        elif p == 'add_egg':
            self.text('PAN-FRY STATION · RIGHT INDUCTION', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text('FARM-FRESH EGG', 1330, 635, 17, WHITE, center=True, anchor_y='center')
            self.text('Frying pan ready on right induction surface.\nReady to dispense whole egg.', 1330, 545, 13, MUTED, center=True, width=330, anchor_y='center')
            label = 'DISPENSE EGG'

        elif p == 'crack_egg':
            self.text('CRACK THE EGG', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text(f'TAPS: {self.meal.egg_cracks} / 2', 1330, 635, 24, GOLD, center=True, bold=True, anchor_y='center')
            self.text('Tap the egg shell twice over the skillet.', 1330, 545, 13, MUTED, center=True, width=330, anchor_y='center')

        elif p == 'fry_egg':
            self.text('FRYING EGG · SUNNY-SIDE UP', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            self.text(f'{m.temperature:.0f} °C', 1330, 648, 30, GREEN if (130 <= m.temperature <= 165) else WHITE, center=True, bold=True, anchor_y='center')
            self.text('TARGET: 130°C – 165°C', 1330, 608, 11, GOLD, center=True, bold=True, anchor_y='center')
            self.box(HB(SLIDER), (38, 62, 78))
            low, high, power_span = 130, 165, 250
            band_start = (low - 22) / power_span
            band_end = (high - 22) / power_span
            self.box(HB((1265 + 125 * (band_start + band_end), 444, 250 * (band_end - band_start), 20)), (40, 136, 106))
            self.box(HB((1265 + 250 * m.power, 444, 5, 32)), GOLD)
            self.text(f'POWER OUTPUT: {m.power:.0%}', 1330, 448, 12, WHITE, center=True, anchor_y='center')
            progress = m.egg_progress
            if 130 <= m.temperature <= 165:
                self.text(f'FRY PROGRESS: {progress:.1f} / 5.0 s', 1330, 410, 13, GREEN, center=True, bold=True, anchor_y='center')
            else:
                self.text('DRAG MARKER INTO GREEN ZONE TO FRY', 1330, 410, 11, MUTED, center=True, anchor_y='center')
            if self.pour_stage == 'idle':
                label = 'FRYING...' if m.heating else 'START FRYING'

        elif p in SERVING:
            self.text('CULINARY ASSEMBLY', 1330, 702, 14, CYAN, center=True, anchor_y='center')
            step_names = {'serve_broth': 'STEP 1: SCOOP BROTH', 'serve_noodles': 'STEP 2: LIFT NOODLES', 'serve_egg': 'STEP 3: PLACE EGG'}
            self.text(step_names[p], 1330, 640, 16, GOLD, center=True, bold=True, anchor_y='center')
            self.text('Robotic arm transfers ingredients into the serving bowl.',
                      1330, 550, 13, MUTED, center=True, width=330, anchor_y='center')
            label = SERVING[p][0] if self.bowl_delivered else 'DISPENSE BOWL'

        elif p == 'presentation':
            self.text('SYSTEM ADVISORY · TOLERANCE CHECK', 1330, 702, 14, GOLD, center=True, bold=True, anchor_y='center')
            self.box((1330, 650, 350, 32), (45, 35, 18, 220), GOLD)
            self.text('⚠ IRREGULARITY: BROWNING DETECTED ON EGG EDGE', 1330, 650, 10, GOLD, center=True, bold=True, anchor_y='center')
            self.text('"The edge is uneven. The meal is already enough.\nNo need to force artificial perfection."',
                      1330, 580, 12, WHITE, center=True, width=340, anchor_y='center')
            self.box((1330, 530, 350, 1), (45, 78, 102))

            # Option 1: KEEP IT AS IT IS [ACCEPT] (comfortably inside card)
            self.box((1330, 475, 340, 44), (24, 100, 125), GREEN)
            self.text('KEEP IT AS IT IS  [ACCEPT]', 1330, 475, 13, WHITE, center=True, bold=True, anchor_y='center')

            # Option 2: KEEP ADJUSTING... [TRIM] (bottom edge at 396, well above card bottom 360)
            self.box((1330, 415, 340, 38), (25, 42, 55), (70, 95, 115))
            self.text('KEEP ADJUSTING... [TRIM]', 1330, 415, 11, MUTED, center=True, anchor_y='center')

        elif p == 'pickup':
            self.text('PREPARATION COMPLETE', 1330, 702, 15, GREEN, center=True, bold=True, anchor_y='center')
            self.text('CHILDHOOD EGG NOODLE SOUP', 1330, 650, 17, GOLD, center=True, bold=True, anchor_y='center')
            self.text('Hot soup with hand-pulled noodles and fried egg.\nSteaming, nourishing, and real.',
                      1330, 565, 13, WHITE, center=True, width=340, anchor_y='center')
            self.box((1330, 450, 350, 38), (16, 48, 62, 220), CYAN)
            self.text('CLICK THE STEAMING BOWL TO CARRY IT', 1330, 450, 11, CYAN, center=True, bold=True, anchor_y='center')

        # 3. LOWER STATUS MESSAGE BAR (Unified with BE at 1330, 290, 390, 60)
        self.box((1330, 290, 390, 60), (8, 26, 42, 220), (45, 78, 102))
        feedback = m.feedback or STEPS.get(p, ('', ''))[1]
        self.text(feedback, 1330, 290, 11, WHITE, center=True, width=360, anchor_y='center')

        # 4. PRIMARY ACTION BUTTON (Unified with BE at 1330, 215, 340, 50)
        if label:
            btn_box = (1330, 215, 340, 50)
            enabled = (p != 'choose' or m.selected == {'water', 'noodles', 'egg'})
            ready_green = (p == 'water' and self.pour_held and self.water_level >= 0.9) or (p in ('choose', 'recipe') and enabled)
            btn_bg = (32, 102, 72) if ready_green else ((24, 75, 105) if enabled else (25, 42, 55))
            btn_border = GREEN if ready_green else (CYAN if enabled else (50, 70, 85))
            self.box(btn_box, btn_bg, btn_border)
            self.text(label, btn_box[0], btn_box[1], 14, WHITE if enabled else MUTED, center=True, bold=True, anchor_y='center')

    def on_draw(self):
        self.clear((8,21,33))
        if self.mode=='lab':self.draw_lab()
        else:self.draw_counter()
        self.window.default_camera.use()
        if self.modal:
            self.box((800,470,1060,330),(7,23,35,250),GOLD)
            self.text('PHYSICAL ITEMS CANNOT BE TRANSFERRED',800,585,24,GOLD,True)
            self.text("I can't take the bowl with me. I can still leave it here.",800,510,20,WHITE,True)
            self.text('Place it on the central research table. Return empty-handed.',800,465,17,WHITE,True)
            self.box((800,365,360,54),(24,100,125),CYAN)
            self.text('I UNDERSTAND',800,358,18,WHITE,True)
        if self.meal.phase=='returning':
            w,h=self.window.width,self.window.height
            arcade.draw_rect_filled(arcade.XYWH(w/2,h/2,w,h),(255,255,255,int(min(1,self.return_time/1.8)*255)))
        self.draw_pause_overlay()

    def can_place_bowl(self):
        return self.meal.carrying and self.meal.warning_read

    def interact_lab(self):
        m=self.meal
        if self.nearest=='kitchen':
            if not m.carrying and not m.bowl_placed:self.mode='counter';self.keys.clear()
            else:m.feedback='The meal is finished. Let it be enough.'
        elif self.nearest=='chair':
            if m.carrying:self.modal='transfer';self.keys.clear()
            elif m.bowl_placed:
                self.do('return_empty');self.return_time=0.;self.keys.clear()
            else:m.feedback='Before returning, I want to make something warm.'
        elif self.nearest=='table' and self.can_place_bowl():
            if self.do('place_bowl'):self.audio.play('click')

    def on_key_press(self,key,modifiers):
        if key==arcade.key.F11:self.toggle_fullscreen();self.fit();return
        if self.handle_pause_key(key):self.keys.clear();self.stirring=False;self.cancel_hold();self.ignore_release=True;return
        if self.is_paused:return
        if self.modal:
            if key in (arcade.key.E,arcade.key.ENTER):
                self.do('read_warning');self.modal=None
            return
        if self.meal.phase=='returning':return
        if self.mode=='lab':
            if key==arcade.key.E:self.interact_lab()
            else:self.keys.add(key)
        elif self.console_open and key==arcade.key.ENTER and self.meal.phase=='cook_noodles' and self.pour_stage=='idle':
            self.do('start_stir')
    def on_key_release(self,key,modifiers):
        self.keys.discard(key)
        if key==arcade.key.SPACE:self.stirring=False
        move_keys = {arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                     arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT}
        if not (self.keys & move_keys):
            self.player.stop_footstep()
    def on_deactivate(self):
        self.keys.clear();self.stirring=False;self.cancel_hold();self.ignore_release=True

    def on_hide_view(self):
        self.keys.clear();self.stirring=False;self.cancel_hold();self.ignore_release=True
    def on_mouse_motion(self,x,y,dx,dy):
        self.mouse=((x-self.ox)/self.scale,(y-self.oy)/self.scale)
        if self.is_paused:self.handle_pause_mouse_motion(x,y)
    def on_mouse_drag(self,x,y,dx,dy,buttons,modifiers):
        if self.is_paused:return
        self.on_mouse_motion(x,y,dx,dy)
        if self.adjusting_power:
            sl=HB(SLIDER);self.meal.power=max(0,min(1,(self.mouse[0]-(sl[0]-sl[2]/2))/sl[2]))
        if self.press_origin and math.hypot(self.mouse[0]-self.press_origin[0],self.mouse[1]-self.press_origin[1])>6:
            self.dragging=True
    def on_mouse_press(self,x,y,button,modifiers):
        if self.is_paused:
            self.handle_pause_mouse_press(x,y,button);self.cancel_hold();self.ignore_release=True;return
        if button==arcade.MOUSE_BUTTON_RIGHT:
            self.cancel_hold();self.meal.feedback='Item returned. Choose the highlighted ingredient or tool.';return
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        self.ignore_release=False
        x,y=(x-self.ox)/self.scale,(y-self.oy)/self.scale
        self.mouse=(x,y);self.press_origin=(x,y);self.dragging=False
        if self.modal:
            if self.inside(x,y,(800,365,360,54)):
                self.do('read_warning');self.modal=None
            return
        if self.mode!='counter':return
        if self.meal.phase=='pickup' and self.inside(x,y,BOWL):
            if self.do('pick_up'):
                self.mode='lab'
                self.player.place(410, 350 + FEET_OFFSET)
                self.keys.clear()
            return
        if self.inside(x,y,SWITCH):
            self.console_open=not self.console_open
            self.console_hint=False
            self.audio.play('click')
            return
        if not self.console_open:return
        m=self.meal;p=m.phase
        if self.station_swap is not None and self.station_swap<2.45:return
        if p in ('water','add_noodles','add_egg'):
            if self.pour_stage=='idle' and self.inside(x,y,HB(NEXT)):
                self.arm_ingredient={'water':'water_jug','add_noodles':'dry_noodles','add_egg':'whole_egg'}[p]
                self.pour_stage='elevate'
                self.pour_clock=0.
                m.feedback='The ingredient lift is rising.'
            elif self.pour_stage=='ready' and self.inside(x,y,HB(NEXT)):
                self.pour_held=True
            return
        if p=='cook_noodles' and self.pour_stage=='idle' and self.inside(x,y,HB(NEXT)):
            self.do('start_stir');return
        if p=='fry_egg' and self.pour_stage!='idle':return
        if p in ('heat_water','fry_egg'):
            if self.inside(x,y,HB(SLIDER)):
                sl=HB(SLIDER);m.power=max(0,min(1,(x-(sl[0]-sl[2]/2))/sl[2]));self.adjusting_power=True;return
            if not m.heating and self.inside(x,y,HB(NEXT)):
                self.do('heat')
            return
        if p=='program':
            if self.inside(x,y,HB(NEXT)):
                self.do('close_program')
            return
        if p == 'choose':
            for name, b in (('water', (1330, 538, 360, 34)),
                            ('noodles', (1330, 496, 360, 34)),
                            ('egg', (1330, 454, 360, 34))):
                if self.inside(x, y, b):
                    self.do('select_' + name)
                    self.audio.play('click')
                    return
            if self.inside(x, y, (1330, 412, 360, 34)):
                m.feedback = 'Neurotoxin formula excluded. Pure natural nutrients only.'
                self.audio.play('click')
                return
            if self.inside(x, y, (1330, 645, 360, 140)):
                for name in ('water', 'noodles', 'egg'):
                    self.do('select_' + name)
                self.audio.play('click')
                return
            for name, b in zip(('water', 'noodles', 'egg'), CHOICES):
                if self.inside(x, y, HB(b)):
                    self.do('select_' + name)
                    return
            if self.inside(x, y, (1330, 215, 340, 50)) or self.inside(x, y, HB(NEXT)):
                if m.selected == {'water', 'noodles', 'egg'}:
                    self.do('confirm')
                else:
                    m.feedback = 'Select Water, Noodles, and Farm Egg to proceed.'
                    self.audio.play('click')
                return
            return
        if p == 'recipe' and (self.inside(x, y, (1330, 215, 340, 50)) or self.inside(x, y, HB(NEXT))):
            if self.do('begin'):
                self.station_swap = 0.
                m.feedback = STEPS['water'][1]
            return
        if p == 'presentation':
            if self.inside(x, y, (1330, 475, 340, 44)) or self.inside(x, y, HB(KEEP)):
                self.do('keep')
            elif self.inside(x, y, (1330, 415, 340, 38)) or self.inside(x, y, HB(ADJUST)):
                self.do('adjust')
            return
        if p in SERVING and self.inside(x,y,HB(NEXT)):
            self.start_serving()
            return
        if self.inside(x,y,HOLO_HIT):return
    def on_mouse_release(self,x,y,button,modifiers):
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        self.adjusting_power=False
        if self.ignore_release:
            self.ignore_release=False;return
        if self.is_paused or self.modal:return
        if self.pour_held:
            self.pour_held=False
            if self.water_level>=.9:
                self.pour_stage='return'
                self.pour_clock=0.
                self.meal.feedback='Water measured. Returning the jug.'
            else:
                self.meal.feedback='A little more water. Hold to top up.'
            return
    def finish(self):
        if self.meal.returned:return
        if not (self.meal.presentation_rejected and self.meal.bowl_placed and not self.meal.carrying):
            return
        self.meal.returned=True
        self.ending.he_bowl_left_in_future=True
        self.ending.h06_placed=True
        self.ending.presentation_rejected=True
        self.ending.stage='H07'
        self.ending.trigger_white_flash()
        self.window.show_view(self.ending)
