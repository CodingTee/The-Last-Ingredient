"""Independent B05: arrival, exploration, contamination and recall.

Reuses the integrated Royal kitchen and original chef/astronaut walk frames.
Approaching the range automatically plays the illustrated contamination and recall sequence.
"""
import math
import random
import arcade
from arcade.types.rect import LRBT
from core.base_view import BaseGameView
from core.constants import ASSETS_DIR
from core.audio import AudioManager
from scenes.royal_exploration import KitchenWalker
from scenes.royal_model import Cooking
from scenes.royal_view import RoyalKitchenView, LEFT_HOB, SY, SH
from scenes.b05_cinematic import B05Cinematic

W,H=1440,900


def cropped(path):
    tex=arcade.load_texture(path)
    bounds=tex.image.getchannel('A').point(lambda a:255 if a>64 else 0).getbbox()
    if bounds:
        x,y,r,b=bounds
        tex=tex.crop(x,y,r-x,b-y)
    return tex


class SceneB05View(BaseGameView):
    """All timing freezes on pause; R replays the complete opening."""
    def __init__(self, truth_understood=False, story_mode=False, on_return=None):
        super().__init__()
        self.truth_understood = truth_understood
        self.on_return = on_return
        self.story_mode = story_mode
        self.royal = RoyalKitchenView()
        self.actors = {'astronaut': {
            facing: [cropped(ASSETS_DIR/'characters'/'astronaut'/f'char_{facing}_{frame}.png')
                     for frame in ('idle','walk1','idle','walk2')]
            for facing in ('up','down','left','right')
        }}
        pose_dir = ASSETS_DIR / 'Scene B05'
        self.film_poses = {
            pose: cropped(pose_dir / f'hero_pose_{pose}.png')
            for pose in ('listen', 'reach')
        }
        self.film_poses['take'] = cropped(pose_dir / 'hero_pose_take_high_hob.png')
        self.camera_native=None
        self.audio=AudioManager()
        self.loop=None
        # No looping boil sound: keep the quiet empty kitchen free of drone.
        self.texts={}
        self.film=B05Cinematic(self)
        self.restart()

    def restart(self):
        if hasattr(self,'film'):self.film.restart()
        self.phase='leaving'
        self.age=self.clock=0.
        self.keys=set()
        self.walker = KitchenWalker(1175., 345.)
        if self.royal._loaded:
            self._start_royal_departure()
        self.facing='down'
        self.walking=False
        self.step_clock=0.
        rng=random.Random(505)
        self.sparks=[(rng.uniform(0,math.tau),rng.uniform(28,80),rng.uniform(0,200),
                      rng.uniform(30,70),rng.uniform(1.1,2.8)) for _ in range(100)]

    def _start_royal_departure(self):
        royal = self.royal
        royal.departure.stop()
        royal.cook = Cooking(stage='away', cuts={'carrot': 10, 'onion': 10},
                            onion_turned=True, carrot_turned=True,
                            ingredients={'carrot','onion','barley'}, water=.75,
                            temperature=80, softness=1.)
        royal.seasoning.reset()
        royal.pot_pos = LEFT_HOB
        royal.departure.start()
        # B05 opens on the urgent reaction, after the cooking close-up.
        royal.departure.time = 1.3
        royal.departure.update(0)

    def on_show_view(self):
        super().on_show_view()
        self.royal.window = self.window
        if not self.royal._loaded:
            self.royal._load_royal_assets()
            self.royal._loaded = True
        self._start_royal_departure()

    def on_hide_view(self):
        self.royal.departure.stop()
        self.film.stop()
        self.keys.clear()
        if self.loop:
            arcade.stop_sound(self.loop);self.loop=None

    def on_deactivate(self):
        self.keys.clear()

    def _phase(self,name):
        self.phase=name;self.age=0.;self.keys.clear()
        if name=='arrival':
            self.audio.play('b03_arrival_warp',volume_scale=.5)

    def on_update(self,dt):
        self.film.set_paused(self.is_paused)
        if self.is_paused:return
        dt=min(dt,.05);self.age+=dt;self.clock+=dt
        if self.phase=='cinematic':
            self.film.update(dt)
            if self.film.done:
                self._finish_scene()
            return
        self.royal.clock = self.clock
        if self.phase=='leaving':
            self.royal.departure.update(dt)
            if self.royal.departure.mode == 'wash':
                self.royal.departure.stop()
                self.royal.walker.door_open = False
                self._phase('empty')
        elif self.phase=='empty' and self.age>=1.2:
            self._phase('arrival')
        elif self.phase=='arrival' and self.age>=3.2:
            self._phase('explore')
        elif self.phase=='explore':
            dx=int(bool(self.keys&{arcade.key.D,arcade.key.RIGHT}))-int(bool(self.keys&{arcade.key.A,arcade.key.LEFT}))
            dy=int(bool(self.keys&{arcade.key.W,arcade.key.UP}))-int(bool(self.keys&{arcade.key.S,arcade.key.DOWN}))
            before=(self.walker.x,self.walker.y)
            self.walker.move(dx,dy,dt)
            self.walking=math.dist(before,(self.walker.x,self.walker.y))>.01
            if self.walking:
                self.facing=('right' if dx>0 else 'left') if abs(dx)>=abs(dy) else ('up' if dy>0 else 'down')
                self.step_clock = getattr(self, "step_clock", 0.0) + dt
                if self.step_clock >= 0.24:
                    self.step_clock = 0.0
                    self.audio.play("Normal Walk", min_interval=0.18, volume_scale=0.5)
            if self.walker.near('range') and self.walker.y >= 265:
                self._begin_film()

    def _finish_scene(self):
        if self.on_return:
            self.on_return()
        else:
            from scenes.future_nutrient_view import TransitDepartureView

            TransitDepartureView.open_modern_return(self.window, self.truth_understood)

    def _begin_film(self):
        self.walking=False
        self.facing='up'
        self._phase('cinematic')
        self.film.restart()


    def _actor(self,char,x,foot,facing,moving=False,alpha=255):
        frame=int(self.clock/.14)%4 if moving else 0
        tex=self.actors[char][facing][frame]
        height=178 if char=='chef' else 184
        width=height*tex.width/tex.height
        arcade.draw_ellipse_filled(x,foot+1,53,12,(15,12,12,int(alpha*.3)))
        arcade.draw_texture_rect(tex,arcade.XYWH(x,foot+height/2,width,height),alpha=alpha)

    def _arrival_fx(self,x,y,behind,residual=False):
        t=self.age if self.phase=='arrival' else self.age+3.2
        energy=max(0,1-t/3.2)
        if not residual:
            ceiling=230*max(0,1-max(0,t-.65)/2.3)
            for i in range(3):
                height=35+i*65
                if height>ceiling:continue
                points=[]
                start=0 if behind else math.pi
                for n in range(25):
                    a=start+n*math.pi/24+t*.3
                    points.append((x+math.cos(a)*79,y+math.sin(a)*20+height))
                arcade.draw_line_strip(points,(83,225,255,int(180*energy)),2)
            for a,r,h,speed,life in self.sparks:
                angle=a+t*.35
                if (math.sin(angle)>0)!=behind:continue
                height=(h+t*speed)%225
                if height>ceiling:continue
                sx=x+math.cos(angle)*r;sy=y+math.sin(angle)*r*.25+height
                alpha=int(200*energy)
                arcade.draw_circle_filled(sx,sy,6,(52,212,255,int(alpha*.12)))
                arcade.draw_circle_filled(sx,sy,2,(160,245,255,alpha))
        # Sparse boot-level residue, with consistent front/back depth.
        for i in range(15):
            a=i*math.tau/15+self.clock*.15
            if (math.sin(a)>0)!=behind:continue
            age=(self.clock+i*.23)%2.3
            alpha=int(115*min(1,age/.2)*(1-age/2.3))
            sx=x+math.cos(a)*60;sy=y+math.sin(a)*17+age*10
            arcade.draw_circle_filled(sx,sy,2,(125,233,255,alpha))

    def _label(self,key,s,x,y,size=16,color=(242,231,210,255)):
        sig=(s,size,color)
        if key not in self.texts or self.texts[key][0]!=sig:
            self.texts[key]=(sig,arcade.Text(s,x,y,color,size,
                 anchor_x='center',anchor_y='center',font_name='Arial'))
        obj=self.texts[key][1];obj.x=x;obj.y=y;obj.draw()

    def _draw_royal_room(self):
        self.royal.draw_kitchen_map_base(include_table=False)
        px, py = LEFT_HOB[0], LEFT_HOB[1] - SY + (H-SH)/2
        for i in range(6):
            progress = (self.clock*.24+i*.17)%1
            arcade.draw_circle_filled(px+math.sin(self.clock+i)*10,
                py+24+progress*55, 3+progress*5, (233,227,212,int(37*(1-progress))))
        if self.phase == 'empty' or self.walker.y < 220:
            self.royal.draw_prep_table()

    def draw_cinematic_room(self, name, progress):
        self.royal.resize_canvas(self.window.width,self.window.height)
        self._draw_royal_room()
        salt_x, _ = self.royal.seasoning.SALT_POS
        stove_x, stove_y = LEFT_HOB[0] + 45, 360
        impact_x, impact_y = salt_x - 34, 289
        x, y = impact_x, impact_y
        height = 205
        if name == 'take':
            x, y = stove_x, stove_y
            height = 268
        elif name == 'listen':
            # Recoil ends at the salt-side corner; subsequent shots share that mark.
            blend = max(0., min(1., (progress * 1.1 - .13) / (.78 - .13)))
            blend = blend * blend * (3 - 2 * blend)
            x = stove_x + (impact_x - stove_x) * blend
            y = stove_y + (impact_y - stove_y) * blend
        if name == 'recall':
            self.film._recall_layer(progress*1.15, True, anchor=(x,y), scale=.42)
        if name != 'empty':
            alpha = round(255*max(0.,1-progress*1.3)) if name=='recall' else 255
            pose = self.film_poses['reach' if name == 'recall' else name]
            width = height * pose.width / pose.height
            arcade.draw_ellipse_filled(x, y, 52, 11, (15, 12, 12, alpha // 4))
            arcade.draw_texture_rect(
                pose, arcade.XYWH(x, y + height / 2, width, height), alpha=alpha,
            )
        if name == 'recall':
            self.film._recall_layer(progress*1.15,False,anchor=(x,y),scale=.42)
        if self.walker.y >= 220:
            self.royal.draw_prep_table()
        if name == 'recall':
            flash = int(175*max(0.,1-abs(progress-.60)/.20))
            if flash:
                arcade.draw_rect_filled(arcade.XYWH(W/2,H/2,W,H),(186,241,255,flash))

    def on_draw(self):
        self.clear((15,15,19))
        w,h=self.window.width,self.window.height
        scale=max(w/W,h/H)
        if self.camera_native is None:self.camera_native=arcade.camera.Camera2D(window=self.window)
        cam=self.camera_native
        cam.viewport=LRBT(0,w,0,h)
        cam.projection=LRBT(-w/(2*scale),w/(2*scale),-h/(2*scale),h/(2*scale))
        cam.position=(W/2,H/2);cam.use()
        if self.phase=='cinematic':
            self.film.draw()
            self.draw_pause_overlay()
            return
        self.royal.resize_canvas(w,h)
        if self.phase == 'leaving':
            self.royal.departure.draw()
            self.draw_pause_overlay()
            return
        self._draw_royal_room()
        if self.phase in ('arrival','explore'):
            x,y=self.walker.x,self.walker.y
            self._arrival_fx(x,y,True,self.phase!='arrival')
            opacity=int(255*min(1,self.age/.45)) if self.phase=='arrival' else 255
            self._actor('astronaut',x,y,self.facing,self.walking,opacity)
            self._arrival_fx(x,y,False,self.phase!='arrival')
            if y >= 220:
                self.royal.draw_prep_table()
            if self.phase=='arrival':
                flash=int(90*max(0,1-self.age/.65)**2)
                if flash:arcade.draw_rect_filled(arcade.XYWH(W/2,H/2,W,H),(160,233,255,flash))
        # Captions use the same world canvas, inside both aspect ratios.
        line=''
        if self.phase=='explore':
            line='She is still waiting. If I take the soup away…'
        if line:
            arcade.draw_rect_filled(arcade.XYWH(W/2,112,1200,60),(14,16,20,215))
            self._label('line',line,W/2,112,17)
        if self.phase=='explore':
            if self.walker.near('range'):
                self._label('prompt','Approach the soup',330,580,15,(244,218,159,255))
            self._label('controls','WASD / ARROWS Move     Approach the range     R Replay     Esc Pause',W/2,69,12,(189,186,175,255))
        self.draw_pause_overlay()

    def on_key_press(self,key,modifiers):
        if key==arcade.key.F11:self.toggle_fullscreen();return
        if self.handle_pause_key(key):self.keys.clear();return
        if self.is_paused:return
        if key==arcade.key.R:self.restart();return
        if self.phase=='explore':
            self.keys.add(key)
            if key==arcade.key.E and self.walker.near('range'):
                self._begin_film()

    def on_key_release(self,key,modifiers):
        self.keys.discard(key)

    def on_mouse_press(self,x,y,button,modifiers):
        if self.is_paused:self.handle_pause_mouse_press(x,y,button)
