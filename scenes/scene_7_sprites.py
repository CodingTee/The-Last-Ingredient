"""Scene 7 generated sprites, first-person workstations and registered input regions.

Only water/flame/steam effects are procedural; ingredients and utensils are PNGs.

"""

from pathlib import Path

import math

import arcade

from arcade.types import Color

from PIL import Image

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCENE_7_DIR

from core.player import FEET_OFFSET

from scenes.scene_7_interaction import CookingInteraction



SPRITES=('pot_empty','pan_empty','bowl_empty','noodles_dry','eggs_carton','oil_bottle',

 'egg_raw','egg_fried','shell_half','shell_fragment','ladle','chopsticks','spatula',

 'knife','cutting_board','shell_saucer','burner_knob','water_surface','noodles_cooked','bowl_soup','broth_surface','pot_noodles_block','pot_noodles_soft','pot_noodles_golden','pot_broth_golden','pan_oiled','bowl_broth','bowl_noodles','bowl_egg','bowl_broth_noodles','bowl_broth_egg','bowl_noodles_egg','eggs_carton_one','egg_whole','shell_pair','faucet_valve_closed','faucet_valve_open')

POT_FILL_FRAMES = ("pot_empty", *(f"pot_water_{index}" for index in range(1, 6)))


def make_kitchen_night_mask(door_open):

    # A low-resolution world light map is enough for smooth ambient gradients.

    width, height = 168, 94

    pixels = []

    for row in range(height):

        y = 937 * (1 - (row + 0.5) / height)

        for col in range(width):

            x = 1678 * (col + 0.5) / width

            def pool(cx, cy, rx, ry):

                return math.exp(-(((x - cx) / rx)**2 + ((y - cy) / ry)**2))



            moonlight = max(pool(625, 730, 150, 270), pool(1150, 730, 150, 270))

            doorway = pool(65, 390, 185, 220) if door_open else 0

            opacity = 204 - 50 * moonlight - 35 * doorway

            pixels.append((7, 12, 23, round(min(253, max(0, opacity)))))

    mask = Image.new("RGBA", (width, height))

    mask.putdata(pixels)

    return arcade.Texture(mask)





class KitchenSpriteRenderer:

    def __init__(self,view):

        self.view=view

        self.last_step=None;self.step_entered=0.0

        self.interaction=CookingInteraction(self)

        self.tex={n:arcade.load_texture(SCENE_7_DIR/'sprites'/(n+'.png')) for n in (*SPRITES, *POT_FILL_FRAMES[1:])}

        # Register water frames to the visible pot rather than their canvas padding.
        for name in POT_FILL_FRAMES:
            texture = self.tex[name]
            alpha = texture.image.getchannel('A')
            left, top, right, bottom = alpha.point(
                lambda value: 255 if value > 128 else 0
            ).getbbox()
            self.tex[name] = texture.crop(left, top, right - left, bottom - top)

        world_dir = SCENE_7_DIR / 'sprites' / 'world'

        self.world_tex = {}

        for n in ('pot_empty','pan_empty','cutting_board','knife','bowl_empty','oil_bottle','ladle','spatula'):

            wf = world_dir / f"{n}.png"

            if wf.exists():

                self.world_tex[n] = arcade.load_texture(str(wf))

        self.tex_shadow = arcade.load_texture(str(world_dir / 'contact_shadow.png')) if (world_dir / 'contact_shadow.png').exists() else None

        self.shadow_configs = {

            'pot_empty': (72, 16, 6, 175),

            'pan_empty': (98, 14, 5, 170),

            'cutting_board': (98, 14, 3, 160),

            'knife': (50, 8, 3, 130),

            'noodles_dry': (74, 10, 4, 150),

            'eggs_carton': (64, 14, 4, 160),

            'bowl_empty': (54, 12, 4, 155),

            'oil_bottle': (24, 8, 3, 150),

            'ladle': (36, 10, 3, 140),

            'spatula': (40, 10, 4, 140),

            'bowl_soup': (32, 8, 2, 130),

        }

        self.bg={n:arcade.load_texture(SCENE_7_DIR/'backgrounds'/(n+'.png')) for n in ('kitchen','sink_background','stove_background','prep_background','pantry_background','fridge_background')}

        valve_names = ('faucet_valve_closed', 'faucet_valve_open')
        bounds = []
        for name in valve_names:
            alpha = self.tex[name].image.getchannel('A')
            bounds.append(alpha.point(lambda value: 255 if value > 32 else 0).getbbox())
        left = min(box[0] for box in bounds)
        top = min(box[1] for box in bounds)
        right = max(box[2] for box in bounds)
        bottom = max(box[3] for box in bounds)
        for name in valve_names:
            self.tex[name] = self.tex[name].crop(left, top, right-left, bottom-top)
        self.bg['sink_background'] = arcade.load_texture(SCENE_7_DIR/'backgrounds/sink_right_valve_plate.png')
        self.bg['stove_background']=arcade.load_texture(SCENE_7_DIR/'backgrounds/stove_controls_blank.png')
        self.bg['kitchen']=arcade.load_texture(SCENE_7_DIR/'backgrounds/kitchen_refined.png')

        self.map_pass=False

        self.kitchen_closed = arcade.load_texture(SCENE_7_DIR / 'backgrounds/kitchen_door_closed.png')
        self.kitchen_door_leaf = arcade.load_texture(SCENE_7_DIR / 'sprites/kitchen_door_leaf.png')

        sw_file = SCENE_7_DIR / 'sprites/world/kitchen_wall_switch.png'
        glow_file = SCENE_7_DIR / 'sprites/world/kitchen_wall_switch_outline.png'
        self.light_switch = arcade.load_texture(str(sw_file if sw_file.exists() else SCENE_7_DIR / 'sprites/kitchen_wall_switch.png'))
        self.light_switch_glow = arcade.load_texture(str(glow_file)) if glow_file.exists() else None

        arrow_file = SCENE_7_DIR / 'sprites/world/switch_hint_arrow.png'
        if not arrow_file.exists():
            arrow_file = ROOT / 'assets/he_cooking/switch_hint_arrow.png'
        self.switch_hint_arrow = arcade.load_texture(str(arrow_file))

        self.kitchen_night_masks = {state: make_kitchen_night_mask(state) for state in (False, True)}

        self.targets = {
            'light_switch': (170, 318),
            'door': (110, 318),
            'pantry': (260, 318),
            'fridge': (415, 318),
            'sink': (625, 318),
            'knives': (815, 318),
            'stove': (1370, 318),
            'table': (900, 230),
            'exit': (145, 320),
        }

    def sprite(self,name,x,y,w,h,alpha=255,key=None,angle=0):

        self.interaction.record(name,x,y,w,h,key)

        if self.map_pass and self.tex_shadow and name in self.shadow_configs:

            sw, sh, sy_off, s_alpha = self.shadow_configs[name]

            arcade.draw_texture_rect(

                self.tex_shadow,

                arcade.XYWH(x, y - h / 2.0 + sy_off, sw, sh),

                color=Color(35, 20, 15, round(s_alpha * (alpha / 255.0)))

            )

        t = self.world_tex.get(name, self.tex[name]) if self.map_pass else self.tex[name]

        scale = min(w / t.width, h / t.height)

        arcade.draw_texture_rect(

            t,

            arcade.XYWH(x, y, t.width * scale, t.height * scale),

            color=Color(245, 240, 232, round(alpha)) if self.map_pass else Color(255, 255, 255, round(alpha)),
            angle=angle

        )

    def background(self,name):

        t=self.bg[name];scale=max(SCREEN_WIDTH/t.width,SCREEN_HEIGHT/t.height)

        arcade.draw_texture_rect(t,arcade.XYWH(640,360,t.width*scale,t.height*scale))

    def exploration_target(self):
        v = self.view
        x = v.player.x
        feet_y = v.player.y - v.player.feet_offset + 8
        nearby = []
        for key, (anchor_x, anchor_y) in self.targets.items():
            if key == 'light_switch' and v.kitchen_door_open:
                continue
            if key == 'exit':
                continue

            # Wooden door: triggers when approaching the door threshold or doorway
            if key == 'door':
                y_tol = 65 if v.kitchen_door_open else 80
                if abs(x - anchor_x) <= 85 and abs(feet_y - anchor_y) <= y_tol:
                    distance = math.hypot(x - anchor_x, feet_y - anchor_y)
                    nearby.append((distance, key))
                continue

            # Light switch: any wall-side stance below the switch, not one fixed spot.
            if key == 'light_switch':
                old_stance = abs(x - anchor_x) <= 45 and abs(feet_y - anchor_y) <= 30
                wall_stance = anchor_x - 90 <= x <= 190 and 348 < feet_y <= 495
                if old_stance or wall_stance:
                    distance = math.hypot(x - anchor_x, feet_y - anchor_y)
                    nearby.append((distance, key))
                continue

            # Counter workstations (fridge, pantry, sink, knives, stove):
            if key in ('fridge', 'pantry', 'sink', 'knives', 'stove'):
                x_tol = 85 if key == 'stove' else 65
                if abs(x - anchor_x) <= x_tol and (260 <= feet_y <= 520):
                    distance = math.hypot(x - anchor_x, min(50, abs(feet_y - 318)))
                    nearby.append((distance, key))
                continue

            radius = 160 if key == 'table' else 65
            distance = math.hypot(x - anchor_x, feet_y - anchor_y)
            if distance < radius:
                nearby.append((distance, key))

        return min(nearby)[1] if nearby else None

    def exploration(self):

        self.interaction.regions.clear()

        v=self.view

        if v.world_cam:

            v.world_cam.position=(v.cam_x,468.5);v.world_cam.use()

        t = self.bg['kitchen'] if v.kitchen_door_open else self.kitchen_closed

        scale = 1678 / t.width

        arcade.draw_texture_rect(t,arcade.XYWH(839,468.5,t.width*scale,t.height*scale))

        if not v.kitchen_door_open:

            self.draw_light_switch()

        self.map_pass=True

        # Movable cookware and ingredients remain independently addressable sprites.

        for name,x,y,w,h in [('pot_empty',1320,677,75,65),('spatula',1485,654,46,55),('pan_empty',1440,667,132,67),

          ('cutting_board',905,652,98,48),('knife',928,661,60,34),

          ('bowl_empty',1112,663,62,43),('oil_bottle',1205,670,22,53),

          ('ladle',1242,651,40,56)]:self.sprite(name,x,y,w,h)

        # Collected ingredients are shown by the HUD instead.

        v.dining.draw(highlight=self.exploration_target()=="table" and not v.dialogue.active)

        if v.dining.ready and not v.dining.eating:

            self.sprite("bowl_soup",v.player.x+26,v.player.y-35,34,26)

        self.map_pass=False

        # The leaf is drawn over the player only when his feet are behind it.
        if v.kitchen_door_open and v.player_behind_open_door:
            scale = 1678 / self.kitchen_door_leaf.width
            arcade.draw_texture_rect(
                self.kitchen_door_leaf,
                arcade.XYWH(839, 468.5, self.kitchen_door_leaf.width * scale, self.kitchen_door_leaf.height * scale)
            )

        darkness = 1.0 - v.kitchen_light_level

        if darkness > 0:

            arcade.draw_texture_rect(

                self.kitchen_night_masks[v.kitchen_door_open], arcade.XYWH(839,468.5,1678,937),

                color=Color(255,255,255,round(255 * darkness)),

            )

        # Yellow tailless hint arrow above the switch (from future scene) while light is OFF
        if not v.kitchen_light_on and not v.kitchen_door_open:
            pulse = 0.82 + 0.18 * math.sin(v.t * 4.2)
            alpha = round(255 * pulse)
            bob = 5.0 * math.sin(v.t * 4.2)
            arcade.draw_texture_rect(
                self.switch_hint_arrow,
                arcade.XYWH(101, 665.0 + bob, 32.0, 22.4),
                color=Color(255, 255, 255, alpha)
            )

        target=self.exploration_target() if not v.dialogue.active and not v.dining.eating else None

        if target:

            x,y=self.targets[target]

            stove_prompt = '[E] Cook Egg Noodle Soup'
            if len(v.collected_ingredients) < 2:
                stove_prompt = '[E] Check Ingredients'
            if v.dining.ready:
                stove_prompt = '[E] Take Bowl to Kitchen Table'
            texts = {
                'fridge': '[E] Open Refrigerator',
                'pantry': '[E] Search Pantry Cupboard',
                'sink': '[E] Check Water Supply',
                'knives': "[E] Inspect Chef's Knives",
                'stove': stove_prompt,
                'table': '[E] Sit & Eat' if v.dining.ready else '[E] Kitchen Table',
                'exit': '[E] Return to Living Room'
            }

            if target == 'door':
                action = 'Close' if v.kitchen_door_open else 'Open'
                door_px = 145 if v.player.x < 170 else 185; v._draw_world_prompt(door_px, max(v.player.y + 75, 410), f'[E] {action} Kitchen Door', highlight=True)
            elif target == 'light_switch':
                action = 'Turn Off' if v.kitchen_light_on else 'Turn On'
                v._draw_world_prompt(175, 670, f'[E] {action} Kitchen Light', highlight=True)
            elif target in ('fridge', 'pantry', 'sink', 'knives', 'stove'):
                if not v.kitchen_light_on:
                    v._draw_world_prompt(x, max(v.player.y + 75, 540), '[E] Need light first', highlight=False)
                else:
                    v._draw_world_prompt(x, max(v.player.y + 75, 540), texts[target], highlight=(target == 'stove'))
            else:
                v._draw_world_prompt(x, y + 110, texts[target], highlight=False)



    def draw_light_switch(self):

        v = self.view

        is_active = (self.exploration_target() == 'light_switch' and not v.dialogue.active)

        w = 21.2

        h = 57.2

        if is_active and self.light_switch_glow:

            pulse = 0.5 + 0.5 * math.sin(v.t * 5.0)

            alpha = round(150 + 90 * pulse)

            arcade.draw_texture_rect(self.light_switch_glow, arcade.XYWH(101, 610, w, h), color=Color(255, 255, 255, alpha))

        arcade.draw_texture_rect(self.light_switch, arcade.XYWH(101, 610, w, h))



    def draw_ingredient_storage(self):
        view = self.view
        if view.ui_cam:
            view.ui_cam.use()
        self.interaction.regions.clear()
        pantry = view.storage_target == "pantry"
        item = "noodles_dry" if pantry else "eggs_carton"
        self.background("pantry_background" if pantry else "fridge_background")
        collected = item in view.collected_ingredients
        if not collected:
            self.sprite(item, 640, 325 if pantry else 290, 180, 100)
        hint = "Already collected." if collected else (
            "Click the wide noodle block to take it." if pantry else "Click the egg carton to take it."
        )
        self.title("PANTRY CUPBOARD" if pantry else "REFRIGERATOR", hint)
        arcade.draw_rect_filled(arcade.XYWH(640, 70, 270, 40), (22, 28, 37, 235))
        arcade.draw_text("[B / E] Back to kitchen", 640, 70, (246, 219, 163), 14,
                         anchor_x="center", anchor_y="center")

    def action_button(self,label):

        self.interaction.overlay()

    def title(self, text, subtitle='', progress=''):
        sub = subtitle
        if hasattr(self, 'view') and getattr(self.view, 'mode', None) == 1:
            if hasattr(self, 'interaction') and getattr(self.interaction, 'message', None):
                sub = self.interaction.message or subtitle
            v = self.view
            if not progress:
                if v.cook_step == 0:
                    progress = f"WATER  {round(v.water_level * 100)}%"
                elif v.cook_step in (1, 2):
                    if v.water_boiling:
                        progress = "WATER  100% (BOILING)"
                    elif v.stove_ignited:
                        progress = f"WATER  {round(min(1.0, v.boil_timer / 3.0) * 100)}% (HEATING)"
                    else:
                        progress = "WATER  100%"
                elif v.cook_step >= 3:
                    noodle_p = round(v.noodle_cook_progress * 100)
                    egg_p = round(v.egg_cooked_progress * 100)
                    progress = f"NOODLES  {noodle_p}%   |   EGG  {egg_p}%"

        arcade.draw_rect_filled(arcade.XYWH(640, 674, 1040, 68), (18, 22, 30, 235))
        arcade.draw_text(text, 640, 689, (246, 219, 163), 15, anchor_x='center', anchor_y='center', bold=True)
        if progress:
            arcade.draw_text(progress, 1120, 689, (255, 230, 150), 12, anchor_x='right', anchor_y='center', bold=True)
        arcade.draw_text(sub, 640, 659, (228, 225, 215), 11, anchor_x='center', width=980, align='center')

    def draw_egg_carton(self, x, y, width, height):
        name = 'eggs_carton_one' if self.interaction.eggs_remaining == 1 else 'eggs_carton'
        self.sprite(name, x, y, width, height, key='eggs_carton')

    def pot_fill_stage(self):
        return min(5, max(0, int(self.view.water_level * 5 + 1e-9)))

    def filled_pot_name(self):
        return POT_FILL_FRAMES[self.pot_fill_stage()]

    def draw_filled_pot(self, x, y, width, height):
        level = min(5.0, max(0.0, self.view.water_level * 5))
        stage = int(level)
        blend = level - stage
        if blend > 0:
            self.sprite(POT_FILL_FRAMES[stage], x, y, width, height, key='pot_empty')
            self.sprite(POT_FILL_FRAMES[stage + 1], x, y, width, height,
                        alpha=round(255 * blend), key='pot_empty')
        else:
            self.sprite(POT_FILL_FRAMES[stage], x, y, width, height, key='pot_empty')

    def effects(self):

        v=self.view

        for fp in v.flame_particles:

            arcade.draw_circle_filled(fp[0],fp[1],fp[4],(*fp[5],max(0,min(255,int(fp[6])))))

        for bb in v.boil_bubbles:

            arcade.draw_circle_filled(bb[0],bb[1],bb[2],(240,237,218,max(0,min(180,int(bb[4])))))

        for sp in v.steam_puffs:

            arcade.draw_circle_filled(sp[0],sp[1],sp[4],(231,229,215,max(0,min(100,int(sp[5])))))

        for ss in v.sizzle_sparks:

            arcade.draw_circle_filled(ss[0],ss[1],2,(245,202,112,max(0,min(190,int(ss[4]*500)))))

    def cooking(self):

        v=self.view;i=self.interaction

        if v.ui_cam:v.ui_cam.use()

        i.regions.clear()

        if v.cook_step==0:

            self.background('sink_background')

            valve_name = 'faucet_valve_open' if v.is_filling_water else 'faucet_valve_closed'
            self.sprite(valve_name, 565, 456, 58, 50, key='faucet_valve')
            self.draw_filled_pot(435, 340, 300, 235)

            self.draw_egg_carton(970,342,180,115);self.sprite('noodles_dry',1090,410,200,75)

            if v.is_filling_water:

                impact_heights = (325, 328, 341, 349, 357, 365)
                level = min(5.0, max(0.0, v.water_level * 5))
                stage = min(4, int(level))
                impact_y = impact_heights[stage] + (
                    impact_heights[stage + 1] - impact_heights[stage]
                ) * (level - stage)
                arcade.draw_line(435,482,435,impact_y,(150,195,222,200),7)

                for j in range(6):

                    yy=impact_y+((v.t*135+j*14)%(482-impact_y));arcade.draw_circle_filled(435,yy,2,(216,235,246,150))

            arcade.draw_rect_filled(arcade.XYWH(670,335,14,160),(28,35,40,200))

            if v.water_level>0:arcade.draw_rect_filled(arcade.XYWH(670,255+80*v.water_level,9,160*v.water_level),(117,173,205,230))

            self.title('FILL THE POT',i.hint());i.overlay();return

        if i.prep:

            i.assembly();i.overlay();return

        self.background('stove_background')

        # Both burner emitters are independent; precisely aligned to physical burners at (448, 268) and (848, 268)

        pot_cx = 420
        pan_cx = 854
        pan_sprite_x = 940
        shell_x = 814

        for cx,on in ((pot_cx,v.stove_ignited),(pan_cx,i.right_on)):

            if on:

                for j in range(12):

                    a=j*math.tau/12;xx=cx+65*math.cos(a);yy=268+15*math.sin(a)

                    arcade.draw_ellipse_filled(xx,yy,8,16+4*math.sin(v.t*16+j),(70,175,255,210))

        if not i.pot_placed:

            arcade.draw_ellipse_outline(pot_cx,268,215,65,(255,214,110,210),3)

            if i.selected!='pot_empty' and not (i.motion and i.motion['name']=='pot_empty'):

                self.draw_filled_pot(150, 365, 245, 200)

        else:

            if v.noodles_added:
                if v.noodle_cook_progress >= 1.0:
                    frame = 'pot_noodles_golden'
                elif v.noodle_cook_progress >= 0.5:
                    frame = 'pot_noodles_soft'
                else:
                    frame = 'pot_noodles_block'
                self.sprite(frame, pot_cx, 370, 310, 242, key='noodles_cooked')
            else:
                self.draw_filled_pot(pot_cx, 370, 310, 242)

            if v.water_boiling and v.stove_ignited:

                for j in range(8):

                    xx=pot_cx+math.sin(j*4.2+v.t)*72;yy=422+math.sin(v.t*5+j)*17

                    arcade.draw_circle_outline(xx,yy,2+(v.t*10+j)%5,(231,238,239,160),1)

                for j in range(5):

                    yy=455+(v.t*32+j*22)%110

                    arcade.draw_circle_filled(pot_cx+math.sin(v.t+j)*25,yy,9,(230,231,234,35))

        pan_frame = 'pan_oiled' if v.oil_poured else 'pan_empty'
        self.sprite(pan_frame, pan_sprite_x, 355, 450, 240, key='pan_empty')

        # Oil is part of the generated pan sprite.

        if v.egg_cracked:

            # A single food state is pickable, even during the crossfade.

            self.sprite('egg_raw',pan_cx,345,160,110,max(0,255-v.egg_cooked_progress*255),key='egg_raw')

            if v.egg_cooked_progress>0:self.sprite('egg_fried',pan_cx,345,160,110,min(255,v.egg_cooked_progress*255))

            if i.right_on:

                for j in range(5):

                    xx=pan_cx+math.sin(v.t*7+j*3)*65;yy=345+math.cos(v.t*8+j)*24

                    arcade.draw_circle_filled(xx,yy,1.5,(255,220,130,170))

        # Positions match the five physical knobs in stove_background.png.
        controls = (
            ('left_knob', 328, 'LEFT HOB'),
            ('oven_mode', 484, 'OVEN MODE'),
            ('oven_temperature', 642, 'OVEN TEMP'),
            ('oven_timer', 802, 'OVEN TIMER'),
            ('right_knob', 957, 'RIGHT HOB'),
        )
        for key, x, label in controls:
            enabled = (key == 'left_knob' and v.stove_ignited) or (key == 'right_knob' and i.right_on)
            self.sprite('burner_knob', x, 92, 58, 58, key=key, angle=-40 if enabled else 0)
            arcade.draw_text(label, x, 41, (246, 224, 184), 9, anchor_x='center')

        self.sprite('oil_bottle',1180,400,46,110)

        if not v.noodles_added:self.sprite('noodles_dry',130,200,150,86)

        self.draw_egg_carton(1170,280,140,95)

        self.sprite('shell_saucer',1170,180,110,48)

        if v.egg_cracked:
            if i.shell_disposed:
                self.sprite('shell_pair',1170,196,64,39,key='shell_half')
            elif not v.eggshell_removed:
                holding_shell = i.selected == 'shell_half' or (i.motion and i.motion['name'] == 'shell_half')
                if holding_shell:
                    self.sprite('shell_half',1170,220,50,39,key='shell_remainder')
                else:
                    self.sprite('shell_pair',1170,220,64,39,key='shell_half')

        if v.eggshell_present and not v.eggshell_removed:

            self.sprite('shell_fragment',shell_x,355,27,24)

            arcade.draw_circle_outline(shell_x,355,20+2*math.sin(v.t*5),(245,204,108,190),1)

        if v.cook_step>=5:self.sprite('bowl_empty',630,185,140,95)

        titles={1:'PLACE THE POT & HEAT WATER',2:'ADD THE NOODLES',3:'HEAT THE SKILLET & FRY AN EGG',4:'REMOVE THE EGGSHELL',5:'FINISH COOKING & SWITCH OFF'}

        self.title(titles.get(v.cook_step,'COOK YOUR SOUP'),i.hint())



        i.overlay()

    def tarot_table(self):

        self.background('prep_background');self.sprite('bowl_soup',640,120,210,155)

        self.sprite('chopsticks',810,125,90,150)

