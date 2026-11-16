"""Sprite-based S11-S13 cooking, handoff and fixed-memory staging.

All physical objects are loaded sprites. UI and particles are the only drawn shapes.
The village owns the meal, so changing views never restarts the recipe.
"""
import math
import random
from pathlib import Path
import arcade
from arcade.types.rect import LRBT
from core.base_view import BaseGameView
from core.audio import AudioManager
from core.prehistoric_meal import RoastMeal

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / 'assets' / 'prehistoric' / 'cooking_v2'
RACK_CENTER = (640., 325.)
RACK_WIDTH = 720.
RACK_SPREAD = 55.  # Move each unchanged-size support outward.
ROAST_SCALE = .70
SPIT_EXTENSION = 75.  # Expose the collar beyond the front fork lip.
RACK_FORK_PIXELS = ((280, 141), (1230, 148))
PLATE_POS = (160., 145.)
SLAB_POS = (1125., 100.)
FAN_REST = (1150., 285.)
KNIFE_REST = (1165., 360.)

INSTRUCTIONS = {
    'place': ('01  /  ONTO THE SPIT', 'Drag the raw meat from the left platter onto the wooden spit.'),
    'roast_a': ('02  /  ROAST & ROTATE', 'Sweep the fan to stoke the fire. Click the crank to flip sides before they scorch!'),
    'turn': ('02  /  ROAST & ROTATE', 'Click the crank to flip the roast and balance both sides.'),
    'roast_b': ('02  /  ROAST & ROTATE', 'Sweep the fan to stoke the fire. Click the crank to flip sides before they scorch!'),
    'lift': ('03  /  OFF THE FIRE', 'Both sides are golden! Drag the roast onto the stone cutting slab.'),
    'carve': ('04  /  CUT THE FIRST SERVINGS', 'Click the stone cutting slab to enter the carving closeup.'),
    'plate': ('05  /  THE GUARDS EAT FIRST', 'Click the stone cutting slab to finish plating the first servings.'),
    'carry': ('06  /  TO THE ENTRANCE', 'Pick up the loaded platter, then walk to the two entrance guards.'),
    'return_fire': ('07  /  THE NEXT BATCH', 'The guards are eating. Drag the next raw roast onto the spit for the others.'),
    'burned': ('XX  /  CHARRED OVER', 'The meat scorched! Click the roast to discard it and skewer a fresh one.'),
}


class BBQCookingView(BaseGameView):
    def __init__(self, return_view=None, saved=None, meal=None, mode='cook'):
        super().__init__()
        self.return_view = return_view
        self.meal = meal or RoastMeal.restore(saved)
        self.mode = mode
        self.t = 0.
        self.elapsed = 0.
        self.drag = None
        self.mouse = (640., 360.)
        self.start = self.mouse
        self.stroke = 0.
        self.fan_energy = 0.
        self.last_fan_stroke = -100.
        self.knife_held = False
        self.notice = ''
        self.notice_t = 0.
        self.dialogue = mode == 'cook' and self.meal.stage == 'place'
        self.handoff_done = False
        self.next_batch_t = None
        self.turn_running = False
        self.events = set()
        self.particles = []
        self.audio = AudioManager()
        self.sprites = {}
        self.layers = arcade.SpriteList()
        self.texts = {}
        for name in ('plate', 'knife', 'fan', 'slab', 'raw', 'half', 'done', 'slices',
                     'spit', 'whistle', 'beast', 'hands', 'guard_accept', 'guard_eat',
                     'guard_kneel', 'guard_down', 'wound', 'clock', 'beast_card', 'crown_card'):
            self.add_sprite(name, ART / (name + '.png'))
        self.add_sprite('spit_supports', ART / 'spit_supports.png')
        self.add_sprite('spit_fork_front', ART / 'spit_fork_front.png')
        for name in ('empty','raw_a','half_a','done_a','turn_45','turn_90','turn_135','raw_b','half_b','done_b'):
            self.add_sprite('mounted_' + name, ART / ('mounted_' + name + '.png'))
        self.setup_rack_parts()
        self.setup_roast_materials()
        self.add_sprite('plate_slices', ART / 'slices.png')
        self.add_sprite('drag_slices', ART / 'slices.png')
        for name in ('guard_b_accept','guard_b_eat','guard_b_kneel','guard_b_down'):
            path = ART / (name + '.png')
            if path.exists(): self.add_sprite(name,path)
        # Same locations as Scene 11: face north from the hearth; south at the gate.
        # Backgrounds are empty plates; all cooking props remain independent sprites.
        for name in ('camp', 'gate'):
            self.add_sprite(name, ART / (name + '_village_bg.png'))
        self.add_sprite('home', ROOT / 'assets' / 'Scene 6' / 'Background Dark.png')
        self.fire = []
        for i, path in enumerate(sorted((ROOT/'assets/prehistoric/campfire_frames').glob('frame_*.png'))):
            name = 'fire_' + str(i)
            self.add_sprite(name, path)
            self.fire.append(name)

    def add_sprite(self, name, path):
        sprite = arcade.Sprite(str(path))
        self.sprites[name] = sprite
        self.layers.append(sprite)

    def on_show_view(self):
        super().on_show_view()
        self.window.push_handlers(on_deactivate=self.stop_input)

    def on_hide_view(self):
        self.stop_input()
        self.window.remove_handlers(on_deactivate=self.stop_input)

    def stop_input(self):
        self.turn_running = False
        self.drag = None
        self.fan_energy = 0.
        self.last_fan_stroke = -100.
        self.knife_held = False

    def update_camera(self):
        # One uniform camera scale, with a little more vertical view on 16:10.
        if self.camera and self.window:
            aspect = self.window.width / max(1, self.window.height)
            self.view_height = 1280 / aspect
            self.camera.viewport = LRBT(0,self.window.width,0,self.window.height)
            self.camera.projection = LRBT(-640,640,-self.view_height/2,self.view_height/2)
            self.camera.position = (640,360)

    def coords(self,x,y):
        aspect=self.window.width/max(1,self.window.height)
        vh=1280/aspect
        return x/self.window.width*1280, 360-vh/2+y/self.window.height*vh

    def show(self,name,x,y,width,angle=0,alpha=255):
        s=self.sprites[name]
        s.scale=width/s.texture.width
        s.position=(x,y)
        s.angle=angle
        s.alpha=max(0,min(255,int(alpha)))
        s.visible=True
        return s

    def add_texture_sprite(self, name, texture):
        sprite = arcade.Sprite(texture)
        self.sprites[name] = sprite
        self.layers.append(sprite)

    def setup_rack_parts(self):
        """Crop native textures into independently sized supports, roast and shaft.

        No component is stretched. Thin repeated shaft sections extend the exposed
        wood while the central roast can shrink independently of crank and supports.
        """
        self.rack_back_names = []
        self.rack_front_names = []
        for source, prefix, names in [('spit_supports','rack_back',self.rack_back_names),
                                      ('spit_fork_front','rack_front',self.rack_front_names)]:
            tex = self.sprites[source].texture
            split = tex.width // 2
            for side, x, width in [('left',0,split),('right',split,tex.width-split)]:
                name = prefix + '_' + side
                self.add_texture_sprite(name,tex.crop(x,0,width,tex.height))
                names.append(name)
        self.rack_moving_names = []
        self.rack_hardware_names = []
        self.rack_hardware_start = {}
        self.rack_meat_offsets = {}
        for key in ('empty','raw_a','half_a','done_a','turn_45','turn_90','turn_135','raw_b','half_b','done_b'):
            tex = self.sprites['mounted_' + key].texture
            # Only the external collar and crank belong in front of the fork.
            # Find the collar after the thin exposed shaft, excluding the roast.
            alpha = tex.image.getchannel('A')
            shaft_seen = False
            hardware_start = round(tex.width * .80)
            for column in range(round(tex.width*.55),round(tex.width*.94)):
                rows = [y for y in range(tex.height) if alpha.getpixel((column,y))>150]
                if not rows: continue
                span = max(rows)-min(rows)
                if span <= tex.height*.06:
                    shaft_seen = True
                elif shaft_seen:
                    hardware_start = max(0,column-2)
                    break
            self.rack_hardware_start[key] = hardware_start
            front_name = 'rack_' + key + '_hardware_front'
            self.add_texture_sprite(front_name,tex.crop(hardware_start,0,tex.width-hardware_start,tex.height))
            self.rack_hardware_names.append(front_name)
            for part, left, right in [('tip',0,100/512),('crank',400/512,1),('meat',90/512,400/512)]:
                if key == 'empty' and part == 'meat': continue
                x, end = round(left*tex.width),round(right*tex.width)
                if part == 'meat':
                    # Stop at the exposed thin shaft before the crank collar.
                    # Otherwise shrinking the roast also copies a floating collar fragment.
                    alpha = tex.image.getchannel('A')
                    for column in range(round(tex.width*.55),round(tex.width*.82)):
                        rows = [y for y in range(tex.height) if alpha.getpixel((column,y))>150]
                        if rows and max(rows)-min(rows) <= tex.height*.06:
                            end = column+1
                            break
                    self.rack_meat_offsets[key] = (x+end)/2-tex.width*.49
                name = 'rack_' + key + '_' + part
                self.add_texture_sprite(name,tex.crop(x,0,end-x,tex.height))
                self.rack_moving_names.append(name)
        patch = self.sprites['mounted_raw_a'].texture.crop(75,140,20,20)
        scale = RACK_WIDTH / 512
        self.shaft_start = RACK_CENTER[0]-RACK_WIDTH/2+100/512*RACK_WIDTH-RACK_SPREAD-SPIT_EXTENSION-8
        shaft_end = RACK_CENTER[0]-RACK_WIDTH/2+400/512*RACK_WIDTH+RACK_SPREAD+SPIT_EXTENSION+10
        self.shaft_tiles = []
        x = self.shaft_start
        while x < shaft_end:
            width = min(patch.width, math.ceil((shaft_end-x)/scale))
            name = 'rack_shaft_' + str(len(self.shaft_tiles))
            self.add_texture_sprite(name,patch.crop(0,0,width,patch.height))
            self.shaft_tiles.append((name,x,width*scale))
            x += width*scale-.5
            if shaft_end-x < .6: break

    def rack_axle(self):
        """Shared axle seated in the two support cradles after spreading the bases."""
        tex = self.sprites['spit_supports'].texture
        scale = RACK_WIDTH / tex.width
        joints = []
        for i,(x,y) in enumerate(RACK_FORK_PIXELS):
            joints.append((RACK_CENTER[0]+(x-tex.width/2)*scale+(-RACK_SPREAD if i==0 else RACK_SPREAD),
                           RACK_CENTER[1]+(tex.height/2-y)*scale))
        left,right = joints
        radius = 6.5
        slope = (right[1]-left[1])/(right[0]-left[0])
        axis_y = left[1]+radius+(RACK_CENTER[0]-left[0])*slope
        return (RACK_CENTER[0],axis_y,math.degrees(math.atan(slope))), (left,right),radius

    def axis_point(self,x):
        (cx,cy,angle),_,_ = self.rack_axle()
        return x,cy+(x-cx)*math.tan(math.radians(angle))

    def show_support_halves(self):
        tex = self.sprites['spit_supports'].texture
        scale = RACK_WIDTH/tex.width
        split = tex.width//2
        for i,(x,width) in enumerate(((0,split),(split,tex.width-split))):
            side = 'left' if i==0 else 'right'
            cx = RACK_CENTER[0]+(x+width/2-tex.width/2)*scale+(-RACK_SPREAD if i==0 else RACK_SPREAD)
            for prefix in ('rack_back_','rack_front_'):
                self.show(prefix+side,cx,RACK_CENTER[1],width*scale)

    def setup_roast_materials(self):
        self.roast_material_names = []
        for side in ('a','b'):
            for state in ('raw','half','done'):
                name = 'stable_meat_' + side + '_' + state
                self.add_sprite(name, ART / (name + '.png'))
                self.roast_material_names.append(name)
        self.rack_moving_names.extend(self.roast_material_names)
        # Foreground shaft noses enter/exit the visible end faces of the meat.
        shaft = self.sprites['mounted_raw_a'].texture.crop(75,140,20,20)
        for name in ('rack_meat_entry_shaft','rack_meat_exit_shaft'):
            self.add_texture_sprite(name,shaft)
            self.rack_moving_names.append(name)

    def show_roast_material(self, side, progress):
        """Only the meat's surface blends during cooking; no hardware frame changes."""
        progress = max(0.,min(1.,progress))
        axis_x,axis_y = self.axis_point(RACK_CENTER[0])
        angle = self.rack_axle()[0][2]
        theta = math.radians(angle)
        width = RACK_WIDTH * ROAST_SCALE * .58
        texture = self.sprites['stable_meat_'+side+'_raw'].texture
        scale = width/texture.width
        # Register the illustrated bore, not the bounding-box center, to the axis.
        bore_x,bore_y = 35.,168.
        offset = (bore_y-texture.height/2)*scale
        x,y = axis_x-math.sin(theta)*offset,axis_y+math.cos(theta)*offset
        self.show('stable_meat_'+side+'_raw',x,y,width,angle)
        if progress>0:
            self.show('stable_meat_'+side+'_half',x,y,width,angle,255*min(1.,progress*2))
        if progress>.5:
            self.show('stable_meat_'+side+'_done',x,y,width,angle,255*(progress-.5)*2)
        scorch = getattr(self.meal,'scorch_'+side)
        char = max(0.,(scorch-.2)/.8)**1.5
        for state in ('raw','half','done'):
            self.sprites['stable_meat_'+side+'_'+state].color = (
                int(255-185*char),int(255-200*char),int(255-210*char))
        # The shaft is continuous behind the roast. These short foreground pieces
        # cross each end-face contour, stopping inside the entry bore / emerging
        # at the exit, rather than drawing a wooden stripe across the meat surface.
        stub_width = 20*(RACK_WIDTH/512)
        entry = axis_x+(bore_x-texture.width/2)*scale*math.cos(theta)
        exit = axis_x+(620.-texture.width/2)*scale*math.cos(theta)
        self.show('rack_meat_entry_shaft',*self.axis_point(entry-stub_width/2+3),stub_width,angle)
        self.show('rack_meat_exit_shaft',*self.axis_point(exit+stub_width/2-2),stub_width,angle)

    def show_mounted(self,name):
        key = name.removeprefix('mounted_')
        # The only allowed mechanical changes are the player's explicit half-turn.
        # Every raw/half/done state of one side uses the SAME canonical crank/collar.
        if key.startswith('turn_'):
            hardware_key = key
        elif key.endswith('_b') or (key=='empty' and self.meal.turn>=180) or self.next_batch_t is not None:
            hardware_key = 'raw_b'
        else:
            hardware_key = 'raw_a'
        _,_,angle = self.rack_axle()[0]
        tip_tex = self.sprites['mounted_empty'].texture
        tip_scale = RACK_WIDTH/tip_tex.width
        tip_end = round(100/512*tip_tex.width)
        center = RACK_CENTER[0]+(tip_end/2-tip_tex.width/2)*tip_scale-RACK_SPREAD-SPIT_EXTENSION
        self.show('rack_empty_tip',*self.axis_point(center),tip_end*tip_scale,angle)
        tex = self.sprites['mounted_'+hardware_key].texture
        scale = RACK_WIDTH/tex.width
        x = round(400/512*tex.width)
        center = RACK_CENTER[0]+(x+(tex.width-x)/2-tex.width/2)*scale+RACK_SPREAD+SPIT_EXTENSION
        self.show('rack_'+hardware_key+'_crank',*self.axis_point(center),(tex.width-x)*scale,angle)
        for tile,x,width in self.shaft_tiles:
            self.show(tile,*self.axis_point(x+width/2),width,angle)
        start = self.rack_hardware_start[hardware_key]
        center = RACK_CENTER[0]+start/2*scale+RACK_SPREAD+SPIT_EXTENSION
        self.show('rack_'+hardware_key+'_hardware_front',*self.axis_point(center),(tex.width-start)*scale,angle)
        if key == 'empty': return
        if key.startswith('turn_'):
            meat = self.sprites['rack_'+key+'_meat'].texture
            center = RACK_CENTER[0]+self.rack_meat_offsets[key]*scale*ROAST_SCALE
            self.show('rack_'+key+'_meat',*self.axis_point(center),meat.width*scale*ROAST_SCALE,angle)
        else:
            side = 'b' if key.endswith('_b') else 'a'
            progress = self.meal.side_b if side=='b' else self.meal.side_a
            if self.next_batch_t is not None:progress=0.
            self.show_roast_material(side,progress)

    def background(self,name):
        s=self.sprites[name]
        vh=1280/(self.window.width/self.window.height)
        scale=max(1280/s.texture.width,vh/s.texture.height)
        self.show(name,640,360,s.texture.width*scale)

    def label(self,key,text,x,y,size=14,color=(241,227,200),anchor='left',width=None):
        if key not in self.texts:
            self.texts[key]=arcade.Text('',x,y,color,size,font_name='Segoe UI',anchor_y='center',anchor_x=anchor)
        obj=self.texts[key]
        obj.text=text
        obj.position=(x,y)
        obj.font_size=size
        obj.color=color
        if width:
            obj.width=width
            obj.multiline=True
        obj.draw()

    def message(self,text):
        self.notice=text
        self.notice_t=3.

    def sound(self,name,volume=.7):
        self.audio.play(name,volume_scale=volume)

    def actively_fanning(self):
        return self.drag=='fan' and self.fan_energy>.05 and self.t-self.last_fan_stroke<=.12

    def on_update(self,dt):
        if self.is_paused: return
        dt=min(.05,dt)
        self.t+=dt
        self.notice_t=max(0,self.notice_t-dt)
        self.fan_energy=max(0,self.fan_energy-dt*1.5)
        before=self.meal.stage
        if self.mode=='cook' and not self.dialogue:
            self.meal.tick(dt,self.actively_fanning())
            if before!=self.meal.stage:
                self.stop_input()
                self.sound('clue_match')
                self.message({'lift': 'Both sides are golden! Drag the roast onto the slab.',
                              'burned': 'Too charred to serve! Click the roast to skewer a fresh one.'}.get(self.meal.stage, ''))
            if before in ('roast_a','roast_b','turn') and self.meal.heat>.22:
                if random.random()<dt*(2+8*self.meal.heat):
                    self.particles.append([random.uniform(490,790),RACK_CENTER[1]+70,random.uniform(-18,18),random.uniform(35,75),1.2,'smoke'])
                if random.random()<dt*(.5+3.5*self.meal.heat):
                    self.particles.append([random.uniform(540,740),RACK_CENTER[1]+105,0,-120,.8,'fat'])
        if self.mode=='cook' and not self.dialogue and self.meal.stage in ('roast_a','roast_b','turn','lift','burned'):
            scorch = getattr(self.meal,'scorch_'+self.meal.exposed_side)
            if (self.meal.heat_warning or scorch>.15 or self.meal.stage=='burned') and random.random()<dt*16:
                self.particles.append([random.uniform(535,745),self.rack_axle()[0][1]+25,
                                       random.uniform(-15,15),random.uniform(45,85),1.2,'char_smoke'])
        if self.next_batch_t is not None and self.mode=='cook':
            self.next_batch_t -= dt
            if self.next_batch_t <= 0:
                self.mode='alarm'
                self.elapsed=0.
                self.next_batch_t=None
        if self.mode=='alarm':
            self.elapsed+=dt
            for time,key,sound in ((0,'impact','car_crash_impact'),(3,'whistle','click'),(6,'mother','thunder'),(11,'wake','clock_chime')):
                if self.elapsed>=time and key not in self.events:
                    self.events.add(key)
                    self.sound(sound)
            if self.elapsed>=12:
                from scenes.scene_13_view import Scene13View

                self.meal.stage = 'wake'
                self.window.bbq_done = True
                self.window.bbq_progress = self.meal.save()
                self.window.show_view(Scene13View())
                return
        for p in self.particles:
            p[0]+=p[2]*dt
            p[1]+=p[3]*dt
            p[4]-=dt
            if p[5]=='fat' and p[1]<RACK_CENTER[1]+20:
                p[4]=0
                self.sound('sizzle',.08+.32*self.meal.heat)
        self.particles=[p for p in self.particles if p[4]>0]
        self.window.bbq_progress=self.meal.save()

    def hit(self,x,y,cx,cy,w,h):
        return abs(x-cx)<w/2 and abs(y-cy)<h/2

    def on_mouse_press(self,x,y,button,modifiers):
        if self.handle_pause_mouse_press(x,y,button): return
        if button!=arcade.MOUSE_BUTTON_LEFT: return
        x,y=self.coords(x,y)
        self.mouse=(x,y)
        self.start=(x,y)
        self.stroke=0.
        if self.mode=='wake':
            if self.hit(x,y,865,365,205,310): self.advance()
            return
        if self.mode=='alarm': return
        if self.dialogue:
            self.dialogue=False
            return
        if self.hit(x,y,100,674,150,48):
            self.leave()
            return
        if self.mode=='handoff':
            if self.handoff_done:
                self.leave()
            elif self.hit(x,y,640,255,330,160): self.drag='delivery'
            return
        stage=self.meal.stage
        if stage=='burned' and (self.hit(x,y,640,self.rack_axle()[0][1],420,200) or self.hit(x,y,PLATE_POS[0],PLATE_POS[1]+30,260,150)):
            self.meal.retry()
            self.sound('paper_slide')
            self.stop_input()
            self.message('Skewered a fresh roast. Keep both sides balanced!')
            return
        if stage in ('place','return_fire') and self.next_batch_t is None and self.hit(x,y,PLATE_POS[0],PLATE_POS[1]+30,260,150): self.drag='raw'
        elif stage in ('roast_a','roast_b','turn') and self.hit(x,y,945+RACK_SPREAD+SPIT_EXTENSION,self.rack_axle()[0][1]-25,170,200):
            if self.meal.toggle_turn():
                self.sound('paper_slide')
        elif stage in ('roast_a','roast_b','turn') and self.hit(x,y,FAN_REST[0],FAN_REST[1],200,260): self.drag='fan'
        elif stage=='lift' and self.hit(x,y,640,self.rack_axle()[0][1],420,200): self.drag='roast'
        elif stage in ('carve','plate','carry') and self.hit(x,y,SLAB_POS[0],SLAB_POS[1],280,190):
            self.open_board()
        elif stage=='carry' and self.hit(x,y,PLATE_POS[0],PLATE_POS[1]+20,280,180): self.leave()

    def on_mouse_drag(self,x,y,dx,dy,buttons,modifiers):
        if self.is_paused: return
        x,y=self.coords(x,y)
        oldx,oldy=self.mouse
        self.mouse=(x,y)
        if self.drag=='fan':
            # Movement, rather than holding the button motionless, feeds the fire.
            if abs(x-oldx)>1:
                self.last_fan_stroke=self.t
                self.fan_energy=min(1,self.fan_energy+abs(x-oldx)/100)
                if random.random()<.4:
                    self.particles.append([640,RACK_CENTER[1]+10,random.uniform(-100,100),random.uniform(100,210),.7,'spark'])
                self.sound('footstep',.18)
        elif self.drag=='cut': self.stroke+=max(0,oldy-y)

    def on_mouse_motion(self,x,y,dx,dy):
        if self.handle_pause_mouse_motion(x,y): return
        self.mouse=self.coords(x,y)

    def on_mouse_release(self,x,y,button,modifiers):
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        if self.is_paused:
            self.stop_input()
            return
        x,y=self.coords(x,y)
        drag=self.drag
        self.drag=None
        if drag=='fan':
            self.fan_energy=0.
            self.last_fan_stroke=-100.
        valid=False
        if drag=='raw' and self.hit(x,y,640,self.rack_axle()[0][1]-30,420,200):
            if self.meal.stage=='return_fire':
                self.next_batch_t=.9
                valid=True
            else: valid=self.meal.place()
        elif drag=='roast' and self.hit(x,y,SLAB_POS[0],SLAB_POS[1],280,190):
            valid=self.meal.lift()
            if valid: self.message('The roast is on the slab. Click it to enter the carving closeup.')
        elif drag=='delivery' and self.hit(x,y,640,365,550,400):
            valid=self.meal.deliver()
            self.handoff_done=valid
            self.elapsed=0
        if valid:
            self.sound('paper_slide')
        elif drag in ('raw','roast','portion','delivery'):
            self.message('Bring it to the highlighted destination, then release. Your progress is kept.')

    def open_board(self):
        if self.meal.stage not in ('carve','plate','carry'): return
        self.stop_input()
        self.window.bbq_progress = self.meal.save()
        from scenes.prehistoric_board_view import CarvingBoardView
        self.window.show_view(CarvingBoardView(self))

    def on_key_press(self,key,modifiers):
        if key==arcade.key.F11:
            self.stop_input()
            self.toggle_fullscreen()
            return
        if self.handle_pause_key(key):
            self.stop_input()
            return
        if key==arcade.key.R and self.mode=='cook' and not self.is_paused:
            if self.meal.retry(): self.stop_input()
            return
        if key in (arcade.key.ENTER,arcade.key.SPACE,arcade.key.E):
            if self.dialogue:self.dialogue=False
            elif self.mode=='handoff' and self.handoff_done:self.leave()
            elif self.mode=='wake':self.advance()

    def leave(self):
        self.stop_input()
        self.window.bbq_progress=self.meal.save()
        rv=self.return_view
        if rv is None:
            from scenes.scene_11_view import Scene11View
            rv=Scene11View()
        elif isinstance(rv,type):rv=rv()
        rv.held_keys.clear()
        self.window.show_view(rv)

    def advance(self):
        self.window.bbq_done=True
        self.window.bbq_progress=self.meal.save()
        from scenes.royal_view import RoyalKitchenView
        self.window.show_view(RoyalKitchenView())

    def on_draw(self):
        self.clear((15,19,17))
        self.use_game_camera()
        for s in self.sprites.values():s.visible=False
        if self.mode=='cook':self.compose_cooking()
        elif self.mode in ('handoff','alarm'):self.compose_gate()
        elif self.mode=='wake':self.compose_wake()
        self.layers.draw()
        if self.mode=='cook':
            self.draw_particles()
            self.cooking_hud()
        elif self.mode=='handoff':
            self.caption('THE FIRST SERVING',
                         '"At last. Something worth eating tonight."\nThe others are still preparing dinner. Return to the hearth for the next batch.\n[Click / E] Return to the village' if self.handoff_done else
                         'Two guards watch the entrance, bone whistles at their waists.\nDrag the loaded platter into their hands.')
        elif self.mode=='alarm':self.alarm_hud()
        elif self.mode=='wake':
            self.label('time','03:00',640,655,35,anchor='center')
            self.caption('THREE IN THE MORNING',
                         'You wake at the modern table, clutching your throat.\n"The guards... They did not even get to sound the alarm."\nThe Beast has faded. The Crown catches the candlelight.\n[Click the Crown / Enter] Continue the royal memory')
        if self.mode=='alarm' and self.elapsed>10:
            arcade.draw_rect_filled(arcade.XYWH(640,360,1280,900),(0,0,0,min(255,int((self.elapsed-10)*130))))
        self.draw_pause_overlay()

    def compose_cooking(self):
        self.background('camp')
        # Sprite order is fixed by insertion order, so physically overlapping props
        # use separate lists sorted below before the draw call.
        self.show('slab',SLAB_POS[0],SLAB_POS[1],260)
        self.show('plate',PLATE_POS[0],PLATE_POS[1],300)
        mounted = self.meal.stage in ('roast_a','turn','roast_b','lift','burned') and self.drag != 'roast'
        mounted = mounted or self.next_batch_t is not None
        self.show_support_halves()
        if not mounted: self.show_mounted('mounted_empty')
        if self.fire:
            heat = max(0., min(1., self.meal.heat))
            # Fixed size and anchor: heat changes light, never moves the logs.
            fire = self.fire[int(self.t*(6+8*heat))%len(self.fire)]
            sprite = self.show(fire,640,RACK_CENTER[1]+55,274)
            sprite.color = (int(170+85*heat),int(140+115*heat),int(110+145*heat))
        stage=self.meal.stage
        if stage in ('place','return_fire') and self.drag!='raw' and self.next_batch_t is None:
            self.show('raw',PLATE_POS[0],PLATE_POS[1]+32,200)
        if self.next_batch_t is not None: self.show_mounted('mounted_raw_a')
        if stage in ('roast_a','roast_b','turn','lift','burned') and self.drag!='roast':
            angle = self.meal.turn
            if angle < 22.5:
                name = 'raw_a'
            elif angle < 67.5:
                name = 'turn_45'
            elif angle < 112.5:
                name = 'turn_90'
            elif angle < 157.5:
                name = 'turn_135'
            else:
                name = 'raw_b'
            self.show_mounted('mounted_' + name)
        if stage=='carve':
            self.show('done',SLAB_POS[0],SLAB_POS[1]+15,175)
        if stage=='plate':
            self.show('slices',SLAB_POS[0],SLAB_POS[1]+15,170 if self.meal.portions==0 else 120)
        if stage in ('plate', 'carry') and not self.meal.served and self.meal.portions > 0:
            self.show('plate_slices',PLATE_POS[0],PLATE_POS[1]+30,150+30*self.meal.portions)
        if stage in ('roast_a','roast_b','turn'):
            mx,my=self.mouse
            self.show('fan',mx if self.drag=='fan' else FAN_REST[0],my if self.drag=='fan' else FAN_REST[1],180,
                      math.sin(self.t*20)*20 if self.actively_fanning() else -10)
        elif stage in ('place','lift','burned'):self.show('fan',FAN_REST[0],FAN_REST[1],155,-12)
        for drag,name,width in (('raw','raw',210),('roast','done',300),('portion','drag_slices',160)):
            if self.drag==drag:self.show(name,*self.mouse,width)
        # Deliberately sorted rendering of sprite layers, never stretch textures.
        order = (['camp'] + self.rack_back_names + self.fire +
                 [name for name,_,_ in self.shaft_tiles] + self.rack_moving_names +
                 self.rack_front_names + self.rack_hardware_names + ['slab','plate','raw','half','done','slices',
                                          'plate_slices','drag_slices','fan','knife'])
        self.order(order)

    def order(self,names):
        # SpriteList order is updated only when the view changes composition.
        desired=[self.sprites[n] for n in names if n in self.sprites]
        desired += [s for s in self.sprites.values() if s not in desired]
        if list(self.layers)!=desired:
            self.layers.clear()
            self.layers.extend(desired)

    def compose_gate(self):
        self.background('gate')
        e=self.elapsed
        if self.mode=='handoff':
            pose='guard_eat' if self.handoff_done else 'guard_accept'
            self.show(pose,490,370,245)
            # A second instance is needed: each guard has its own sprite.
            if 'guard_second' not in self.sprites:
                self.add_sprite('guard_second',ART/(pose+'.png'))
            second=self.sprites['guard_second']
            second.texture=self.sprites.get('guard_b_eat' if self.handoff_done else 'guard_b_accept',self.sprites[pose]).texture
            self.show('guard_second',805,365,235)
            self.show('whistle',400,260,46,10)
            if not self.handoff_done:
                self.show('hands',640,85,500)
                x,y=self.mouse if self.drag=='delivery' else (640,255)
                self.show('plate',x,y,330)
                self.show('slices',x,y+28,225)
        else:
            pose='guard_kneel' if e<3 else 'guard_down'
            self.show(pose,470,290 if e<3 else 210,350)
            if 'guard_second' not in self.sprites:self.add_sprite('guard_second',ART/'guard_kneel.png')
            self.sprites['guard_second'].texture=self.sprites.get('guard_b_kneel',self.sprites['guard_kneel']).texture
            self.show('guard_second',800,310,270, max(0,e-2)*2)
            if 2<=e<6:
                fall=min(1,(e-2)/1.2)
                self.show('whistle',740+fall*60 if e<3.2 else 640,325-fall*110 if e<3.2 else 325,75 if e<3.2 else 220,-fall*135)
            if e>=6:
                self.show('beast',650,430,920,alpha=min(255,(e-6)*150))
                self.sprites['beast'].color=(40,46,40)
        self.order(['gate','beast','guard_accept','guard_eat','guard_kneel','guard_down','guard_second','whistle','hands','plate','slices'])

    def compose_wake(self):
        self.background('home')
        self.show('clock',640,530,160)
        self.show('beast_card',425,360,190, -8,130)
        self.show('crown_card',865,360,200,5,220+35*math.sin(self.t*3))
        self.order(['home','clock','beast_card','crown_card'])

    def mini_meter(self, cx, cy, title, value, scorch=0., is_active=True):
        val = max(0.0, min(1.0, value))
        bar_w, bar_h = 100, 6
        if title == 'FIRE':
            if val < 0.22:
                val_str = 'LOW (FAN)'
                txt_color = (160, 185, 215)
                fill_color = (90, 120, 150)
            elif val < 0.70:
                val_str = f'{int(val * 100)}%'
                txt_color = (245, 215, 160)
                fill_color = (226, 171, 83)
            else:
                val_str = f'TURBO {int(val * 100)}%'
                txt_color = (255, 130, 50)
                fill_color = (255, 110, 40)
            label_text = f'{title} {val_str}'
        else:
            arrow = '▼ ' if is_active else '▲ '
            if scorch >= 0.20:
                val_str = f'CHAR {int(scorch * 100)}%!'
                txt_color = (255, 80, 70)
                fill_color = (235, 60, 50)
            elif val >= 1.0:
                val_str = 'READY'
                txt_color = (130, 235, 160)
                fill_color = (115, 215, 145)
            else:
                val_str = f'{int(val * 100)}%'
                txt_color = (245, 225, 190) if is_active else (180, 185, 190)
                fill_color = (226, 171, 83) if is_active else (160, 140, 95)
            label_text = f'{arrow}{title} {val_str}'

        self.label('m_txt_' + title, label_text, cx, cy + 9, 9, color=txt_color, anchor='center')
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 8, bar_w, bar_h), (30, 36, 40, 230))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy - 8, bar_w, bar_h), (80, 95, 105, 140), 1)
        if scorch >= 0.20 and title != 'FIRE':
            scorch_fill = min(1.0, scorch)
            arcade.draw_rect_filled(arcade.XYWH(cx - bar_w / 2 + (bar_w * scorch_fill) / 2, cy - 8, bar_w * scorch_fill, bar_h), fill_color)
        elif val > 0:
            arcade.draw_rect_filled(arcade.XYWH(cx - bar_w / 2 + (bar_w * val) / 2, cy - 8, bar_w * val, bar_h), fill_color)

    def step_meter(self, cx, cy, title, current, total):
        self.label('m_txt_' + title, f'{title}  {current} / {total}', cx, cy + 9, 10, color=(240, 218, 160), anchor='center')
        bar_w, bar_h = 120, 6
        val = min(1.0, current / max(1, total))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 8, bar_w, bar_h), (30, 36, 40, 230))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy - 8, bar_w, bar_h), (80, 95, 105, 140), 1)
        if val > 0:
            fill_color = (115, 215, 145) if current >= total else (226, 171, 83)
            arcade.draw_rect_filled(arcade.XYWH(cx - bar_w / 2 + (bar_w * val) / 2, cy - 8, bar_w * val, bar_h), fill_color)

    def cooking_hud(self):
        _, instruction = INSTRUCTIONS[self.meal.stage]
        destination = {'raw': (640, self.rack_axle()[0][1], 390, 150),
                       'roast': (SLAB_POS[0], SLAB_POS[1], 340, 200),
                       'portion': (PLATE_POS[0], PLATE_POS[1] + 20, 280, 180)}.get(self.drag)
        if destination:
            x, y, w, h = destination
            arcade.draw_ellipse_outline(x, y, w, h, (255, 213, 128, 190), 2)
        if self.meal.stage in ('roast_a', 'roast_b'):
            self.label('fan_hint', 'HOLD + SWEEP', FAN_REST[0], FAN_REST[1] - 85, 11, anchor='center')

        # Back button
        arcade.draw_rect_filled(arcade.XYWH(100, 674, 150, 48), (18, 22, 30, 235))
        arcade.draw_rect_outline(arcade.XYWH(100, 674, 150, 48), (110, 180, 245, 140), 1.2)
        self.label('back', '< BACK TO VILLAGE', 100, 674, 11, color=(200, 220, 240), anchor='center')

        # Instruction panel (left) and roasting-progress panel (right) are kept as
        # two separate bars with a gap, so the hint text can never run under the
        # meters regardless of how wide the resolved font renders.
        arcade.draw_rect_filled(arcade.XYWH(475, 674, 490, 48), (18, 22, 30, 235))
        arcade.draw_rect_outline(arcade.XYWH(475, 674, 490, 48), (110, 180, 245, 140), 1.2)
        self.label('instruction', instruction, 250, 674, 12, color=(240, 232, 215), anchor='left', width=455)

        # Roasting progress meters live in their own panel on the right, with a
        # clear 60px gap (720 -> 780) so the hint never crowds the meters.
        arcade.draw_rect_filled(arcade.XYWH(995, 674, 430, 48), (18, 22, 30, 235))
        arcade.draw_rect_outline(arcade.XYWH(995, 674, 430, 48), (110, 180, 245, 140), 1.2)
        if self.meal.stage in ('roast_a', 'roast_b', 'turn', 'lift', 'burned'):
            self.mini_meter(835, 674, 'SIDE A', self.meal.side_a, self.meal.scorch_a, is_active=(self.meal.active_side=='a'))
            self.mini_meter(970, 674, 'FIRE', self.meal.heat)
            self.mini_meter(1105, 674, 'SIDE B', self.meal.side_b, self.meal.scorch_b, is_active=(self.meal.active_side=='b'))
        elif self.meal.stage == 'carve':
            self.step_meter(1000, 674, 'CUTS', self.meal.cuts, 3)
        elif self.meal.stage == 'plate':
            self.step_meter(1000, 674, 'SERVINGS', self.meal.portions, 2)

        if self.meal.stage in ('roast_a', 'roast_b', 'turn'):
            is_turning = abs(self.meal.turn - self.meal.target_turn) > 1.0
            turn_label = 'FLIPPING...' if is_turning else '[CLICK] FLIP SPIT'
            self.label('turn', turn_label,
                       945 + RACK_SPREAD + SPIT_EXTENSION, self.rack_axle()[0][1] + 90, 12, anchor='center')
        if self.meal.stage in ('carve','plate','carry'):
            self.label('board_entry','[CLICK] CUTTING BOARD',SLAB_POS[0],SLAB_POS[1]+120,11,anchor='center')
        if self.meal.stage == 'carry':
            self.label('take', '[CLICK PLATTER]  CARRY TO GUARDS', PLATE_POS[0], PLATE_POS[1] - 85, 11, anchor='center')
        if self.meal.stage == 'burned':
            self.label('heat_warning','CHARRED BLACK - CLICK ROAST TO RETRY FRESH',640,605,14,(255,90,80),'center')
        elif self.meal.stage in ('roast_a','roast_b','turn') and getattr(self.meal, 'scorch_' + self.meal.active_side) >= 0.15:
            self.label('heat_warning','OVERHEATING! CLICK CRANK TO FLIP NOW!',640,605,14,(255,100,70),'center')
        elif self.meal.stage in ('roast_a','roast_b','turn') and self.meal.heat < 0.22:
            self.label('heat_warning','FIRE IS TOO COLD TO COOK - SWEEP THE FAN',640,605,13,(170,200,225),'center')
        if self.notice_t > 0:
            self.label('notice', self.notice, 640, 95, 13, (255, 218, 145), 'center')

        if self.dialogue:
            self.caption('THE GUARDS EAT FIRST',
                         'Tribesperson: "Give the guards theirs first. They have got the whole night ahead of them."\n'
                         'The rest of the tribe is still preparing dinner.\n[Click / Enter] Begin cooking')

    def caption(self,title,text):
        arcade.draw_rect_filled(arcade.XYWH(640,108,1190,175),(11,17,16,235))
        self.label('caption_title',title,80,171,17,(237,190,112))
        self.label('caption_body',text,80,104,14,width=1120)

    def alarm_hud(self):
        e=self.elapsed
        if e<3:
            self.caption('A DULL IMPACT AT THE ENTRANCE','You turn from the next batch. One guard drops to his knees.\nThe other grips his throat and reaches for the whistle at his waist.')
        elif e<6:
            self.caption('THE SILENT WHISTLE','His fingers lose their grip. The bone whistle falls into the dust.\nIt makes no call. No alarm sounds.')
        else:
            self.caption('A SHADOW AT THE GATE','The mother has followed the trail and scent of her juvenile.\nShe sees the remains beside the fire. A low growl. The tribe finally looks up.\n"The meat was cooked... What happened?"')

    def draw_particles(self):
        for x,y,vx,vy,life,kind in self.particles:
            if kind=='char_smoke':arcade.draw_circle_filled(x,y,10+(1.2-life)*17,(55,49,43,int(95*life)))
            elif kind=='smoke':arcade.draw_circle_filled(x,y,9+(1.2-life)*13,(180,166,142,int(35*life)))
            elif kind=='fat':arcade.draw_circle_filled(x,y,2,(255,203,115,150))
            elif kind=='meat_juice':
                alpha = round(230*min(1., life/.18))
                arcade.draw_line(x, y, x-vx*.035, y-vy*.035, (137, 27, 23, alpha), 2.2)
                arcade.draw_circle_filled(x, y, 2.3, (174, 43, 34, alpha))
            elif kind=='cut_spark':arcade.draw_circle_filled(x,y,2.8,(255,215,120,int(min(255,950*life))))
            else:arcade.draw_circle_filled(x,y,2,(255,184,64,int(230*life)))
