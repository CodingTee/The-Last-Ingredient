"""Scene 7: The Old Home Kitchen & Immersive Cooking Counter (S06 - S08)







Implements:







1. Kitchen Exploration Mode (Dedicated 1800px Walkable Kitchen):







   - Player enters through the left entrance door from the living room.







   - Dark, atmospheric kitchen with checkered tile flooring, stainless steel counters, and moonlit windows.







   - Interactive landmarks:







     * Pantry Cupboard & Fridge: Search for ingredients (finds noodles & eggs).







     * Commercial Double Sink: Test water pressure (faucet groans and flows).







     * Chef's Prep Table & Knife Block: Inspect razor-sharp culinary knives.







     * Central Stove Range: High-priority cooking station prompt.







2. Zoomed-In Cooking Mama Style Cooking Counter (S06):







   - Step 1: Fill water into the pot from the faucet with flow audio and gauge.







   - Step 2: Ignite burner knob, dancing blue flame particles, water simmers and boils.







   - Step 3: Drop noodles into boiling broth and stir gently.







   - Step 4: Fry sunny-side-up egg in adjacent skillet with sizzling sound and popping oil sparks.







   - Step 5: S07 Eggshell Memory: Scoop out fallen eggshell fragment, triggering childhood relative's advice.







   - Step 6: Assemble hot noodle soup with golden egg on top.







3. S08 Midnight Tarot Cards:







   - Three cards materialize on the table: The Beast, The Crown, The Gear.







   - Interactive inspection, selecting The Beast triggers time warp into Chapter Two (Prehistoric Cave).







"""







import math







import random







import sys







from pathlib import Path















# Add project root to path for standalone execution







ROOT_DIR = Path(__file__).resolve().parent.parent







if str(ROOT_DIR) not in sys.path:







    sys.path.insert(0, str(ROOT_DIR))















import arcade







from arcade.types.rect import LRBT







from core.constants import (







    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,







    ASSETS_DIR, START_FULLSCREEN







)







from core.player import Player







from core.dialogue import DialogueBox







from core.audio import AudioManager







from core.base_view import BaseGameView







from scenes.scene_7_sprites import KitchenSpriteRenderer







from scenes.scene_7_dining import KitchenDining

from scenes.scene_7_door import (
    LEAF_X_MAX,
    LEAF_X_MIN,
    is_behind_open_door,
    open_door_leaf_bottom_y,
    open_door_max_feet_y,
    open_door_min_x,
    open_door_obstacles,
)















KITCHEN_WORLD_WIDTH = 1678.0







FLOOR_Y_MIN = 140.0







FLOOR_Y_MAX = 565.0















# Scene Modes







MODE_EXPLORE_KITCHEN = 0







MODE_COOKING_MAMA = 1







MODE_SERVE_TRANSITION = 2



MODE_INGREDIENT_STORAGE = 3















# Cooking Mama Steps







COOK_STEP_FILL_WATER = 0







COOK_STEP_IGNITE_STOVE = 1







COOK_STEP_ADD_NOODLES = 2







COOK_STEP_FRY_EGG = 3







COOK_STEP_EGGSHELL_MEMORY = 4







COOK_STEP_ASSEMBLE_DISH = 5







COOK_STEP_FINISHED = 6


def get_closed_door_min_x(feet_y: float) -> float:
    if feet_y <= 248.0:
        return 22.0
    elif feet_y <= 260.0:
        return 22.0 + (feet_y - 248.0) / 1.5
    elif feet_y <= 342.0:
        return 30.0 + (feet_y - 260.0) / 1.82
    elif feet_y <= 422.0:
        return 75.0 + (feet_y - 342.0) / 1.45
    elif feet_y <= 436.0:
        return 130.0 + (feet_y - 422.0) / 0.933
    elif feet_y <= 488.0:
        return 145.0 + (feet_y - 436.0) / 1.733
    else:
        return 175.0


def get_closed_door_max_feet_y(x: float) -> float:
    if x <= 22.0:
        return 248.0
    elif x <= 30.0:
        return 248.0 + (x - 22.0) * 1.5
    elif x <= 75.0:
        return 260.0 + (x - 30.0) * 1.82
    elif x <= 130.0:
        return 342.0 + (x - 75.0) * 1.45
    elif x <= 145.0:
        return 422.0 + (x - 130.0) * 0.933
    elif x <= 175.0:
        return 436.0 + (x - 145.0) * 1.733
    elif x <= 1530.0:
        return 488.0
    else:
        return max(340.0, 488.0 - (x - 1530.0) * 2.5)


# Open-door leaf geometry lives in scenes/scene_7_door.py.
























class KitchenView(BaseGameView):







    """Scene 7 View: Dedicated Dark Kitchen Exploration & Zoomed-in Cooking Mama Minigame."""















    def __init__(self):







        super().__init__()







        self.audio = AudioManager()







        self.t = 0.0







        self.kitchen_door_open = False
        self.player_behind_open_door = False







        self.kitchen_light_on = False







        self.kitchen_light_level = 0.0















        # Mode State







        self.mode = MODE_EXPLORE_KITCHEN







        self.cook_step = COOK_STEP_FILL_WATER















        # Cameras







        self.world_cam = None







        self.ui_cam = None







        self.cam_x = 839.0















        # Dialogue System







        self.dialogue = DialogueBox()















        # Exploration Player: Modern Chef (enters from left doorway)







        self.player = Player(x=185, y=350, char_id="modern")







        self.player.speed = 210.0







        self.dust_particles = []















        self.sprite_renderer = KitchenSpriteRenderer(self)







        self.dining = KitchenDining(self)















        # Key Input States







        self.key_left = False







        self.key_right = False







        self.key_up = False







        self.key_down = False















        # Exploration Landmarks







        self.storage_target = None



        self.collected_ingredients = []
        self.ingredients_hud_dismissed = False







        self.examined_sink = False







        self.examined_knives = False















        # Character Portraits







        scene1_dir = ASSETS_DIR / "Scene 1"







        self.portrait_chef = arcade.load_texture(str(scene1_dir / "Modern Chief.png"))







        self.portrait_thinking = arcade.load_texture(str(scene1_dir / "Chief Thinking.png"))















        # Floating steam motes in kitchen







        self.kitchen_motes = [







            {







                "x": random.uniform(50, KITCHEN_WORLD_WIDTH - 50),







                "y": random.uniform(100, 600),







                "vx": random.uniform(-6, 6),







                "vy": random.uniform(-4, 4),







                "r": random.uniform(1.5, 3.0),







                "alpha": random.randint(30, 90)







            }







            for _ in range(30)







        ]















        # ---------------------------------------------------------------------







        # Cooking Mama Minigame State







        # ---------------------------------------------------------------------







        self.water_level = 0.0          # 0.0 to 1.0







        self.is_filling_water = False







        self.stove_ignited = False







        self.water_boiling = False







        self.boil_timer = 0.0







        self.noodles_added = False







        self.noodle_cook_progress = 0.0 # 0.0 to 1.0















        self.oil_poured = False







        self.egg_cracked = False







        self.egg_cooked_progress = 0.0  # 0.0 to 1.0







        self.eggshell_present = False







        self.eggshell_removed = False















        # Particle Systems for Cooking







        self.boil_bubbles = []          # list of [x, y, r, vy, alpha]







        self.steam_puffs = []           # list of [x, y, vx, vy, size, alpha]







        self.flame_particles = []       # list of [x, y, vx, vy, r, col, alpha]







        self.sizzle_sparks = []         # list of [x, y, vx, vy, life]















        # Serving transition; card inspection belongs exclusively to Scene 8.







        self.transitioning_to_scene_8 = False







        self.fade_alpha = 0.0















        # Start opening narrative in kitchen







        self._trigger_intro_dialogue()















    def _trigger_intro_dialogue(self):







        script = [







            (







                "Old Kitchen",







                "He pushes open the wooden door and enters the darkened kitchen.\nStainless steel counters reflect the pale moonlight, and the air smells faintly of dry herbs and old cast iron.",







                (210, 175, 120)







            ),







            (







                "Chef",







                "\"Everything is where I left it. The pantry, the sink, the stove...\"\n\"Let's see what there is to eat.\"",







                (230, 210, 160),







                self.portrait_chef,







                "left"







            ),







            (







                "Tutorial",







                "[ Walk right to explore the kitchen. Approach the cupboard and refrigerator and press [E] to look inside. ]",







                COLOR_GOLD







            )







        ]







        self.dialogue.start_dialogue(script)















    def on_show_view(self):







        super().on_show_view()







        if self.world_cam is None and self.window:







            self.world_cam = arcade.camera.Camera2D(window=self.window)







            self.ui_cam = arcade.camera.Camera2D(window=self.window)







            self._update_all_cameras()















    def on_hide_view(self):







        self.sprite_renderer.interaction.cancel()







        self.key_left=self.key_right=self.key_up=self.key_down=False















    def on_deactivate(self):







        self.sprite_renderer.interaction.cancel()







        self.key_left=self.key_right=self.key_up=self.key_down=False























    def on_resize(self, width: int, height: int):







        super().on_resize(width, height)







        self._update_all_cameras()















    def to_cooking_coords(self,x,y):







        vx,vy=super().to_virtual_coords(x,y)







        if self.window:







            ratio=(self.window.width/self.window.height)/(SCREEN_WIDTH/SCREEN_HEIGHT)







            vx=(vx-SCREEN_WIDTH/2)*ratio+SCREEN_WIDTH/2







        return vx,vy















    def _update_all_cameras(self):







        if not self.window:







            return







        w = self.window.width







        h = self.window.height







        if self.world_cam:







            self.world_cam.viewport = LRBT(0, w, 0, h)







            self.world_cam.projection = LRBT(-937*w/h/2, 937*w/h/2, -468.5, 468.5)







        if self.ui_cam:







            self.ui_cam.viewport = LRBT(0, w, 0, h)







            self.ui_cam.projection = LRBT(-SCREEN_HEIGHT*w/h/2, SCREEN_HEIGHT*w/h/2, -SCREEN_HEIGHT/2, SCREEN_HEIGHT/2)







            self.ui_cam.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)















    # =========================================================================







    # UPDATE LOGIC







    # =========================================================================







    def on_update(self, dt: float):







        if self.is_paused:







            return















        self.t += dt
        if self.mode == MODE_COOKING_MAMA:
            self.ingredients_hud_dismissed = True







        light_target = float(self.kitchen_light_on)







        light_step = dt / 0.5







        self.kitchen_light_level += max(







            -light_step, min(light_step, light_target - self.kitchen_light_level)







        )















        # Update Dialogue







        if self.dialogue.active:







            self.dialogue.update(dt)















        # ---------------------------------------------------------------------







        # 1. Update Exploration Mode







        # ---------------------------------------------------------------------







        if self.mode == MODE_EXPLORE_KITCHEN:







            self.dining.update()







            if not self.dialogue.active and not self.dining.eating:







                move_x = (1 if self.key_right else 0) - (1 if self.key_left else 0)







                move_y = (1 if self.key_up else 0) - (1 if self.key_down else 0)







            else:







                move_x = 0







                move_y = 0















            # =================================================================



            # 2.5D left wall and dual-state door collision mechanics:



            # Base wall follows room authentic 2.5D perspective bounds:



            # - When feet_y <= 230, ground is open up to screen edge (x = 25.0)



            # - When feet_y > 230, follows left baseboard perspective slope (x = 25.0 + (feet_y - 230.0) * 0.628)



            # =================================================================



            prev_x = self.player.x
            prev_feet_y = self.player.y - self.player.feet_offset + 8.0

            if self.kitchen_door_open:
                # Open door: own bounds + leaf contact wall; doorway is off limits.
                door_min_x = open_door_min_x(prev_feet_y)
                max_feet_y = open_door_max_feet_y(prev_x)
                floor_y_min = FLOOR_Y_MIN + self.player.feet_offset - 8.0
                floor_y_max = max_feet_y + self.player.feet_offset - 8.0
                door_obstacles = list(self.dining.obstacles) + open_door_obstacles()
            else:
                # Closed door: original contour, unchanged.
                door_min_x = get_closed_door_min_x(prev_feet_y)
                max_feet_y = get_closed_door_max_feet_y(prev_x)
                floor_y_min = FLOOR_Y_MIN
                floor_y_max = max_feet_y + self.player.feet_offset - 8.0
                door_obstacles = self.dining.obstacles

            self.player.update(
                dt, move_x, move_y,
                dust_particles=self.dust_particles,
                bounds=(door_min_x, 1540.0, floor_y_min, floor_y_max),
                obstacles=door_obstacles
            )

            # Clamp post-step in case of diagonal move across boundary slope
            px = self.player.x
            post_feet_y = self.player.y - self.player.feet_offset + 8.0

            if self.kitchen_door_open:
                post_wall_x = open_door_min_x(post_feet_y)
                if self.player.x < post_wall_x:
                    self.player.x = post_wall_x
                mf_y = open_door_max_feet_y(self.player.x)
                max_allowed_py = mf_y + self.player.feet_offset - 8.0
                if self.player.y > max_allowed_py:
                    self.player.y = max_allowed_py
                self.player_behind_open_door = is_behind_open_door(self.player.x, post_feet_y)
            else:
                post_wall_x = get_closed_door_min_x(post_feet_y)
                if self.player.x < post_wall_x:
                    self.player.x = post_wall_x
                mf_y = get_closed_door_max_feet_y(self.player.x)
                max_allowed_py = mf_y + self.player.feet_offset - 8.0
                if self.player.y > max_allowed_py:
                    self.player.y = max_allowed_py
                self.player_behind_open_door = False

            # Post clamp moves the logical position; keep the sprite in sync.
            self.player.sprite.center_x = self.player.x
            self.player.sprite.center_y = self.player.y















            if self.dining.eaten and self.kitchen_door_open and not self.dialogue.active:
                exit_x, exit_y = self.sprite_renderer.targets['exit']
                feet_y = self.player.y - self.player.feet_offset + 8.0
                if math.hypot(self.player.x - exit_x, feet_y - exit_y) < 65:
                    self.mode = MODE_SERVE_TRANSITION
                    self.transitioning_to_scene_8 = True
                    self.fade_alpha = 0
                    return

            # Camera Smooth Tracking







            half=min(KITCHEN_WORLD_WIDTH/2,937*(self.window.width/self.window.height)/2) if self.window else 839







            target_cam = max(half, min(KITCHEN_WORLD_WIDTH-half, self.player.x))







            self.cam_x += (target_cam - self.cam_x) * min(1.0, dt * 5.0)















            # Drift Kitchen Motes







            for km in self.kitchen_motes:







                km["x"] += km["vx"] * dt







                km["y"] += km["vy"] * dt







                if km["x"] < 50: km["x"] = KITCHEN_WORLD_WIDTH - 50







                elif km["x"] > KITCHEN_WORLD_WIDTH - 50: km["x"] = 50







                if km["y"] < 80: km["y"] = 620







                elif km["y"] > 620: km["y"] = 80















        # ---------------------------------------------------------------------







        # 2. Update Cooking Mama Mode







        # ---------------------------------------------------------------------







        elif self.mode == MODE_COOKING_MAMA:







            self.sprite_renderer.interaction.update(dt)







            # Water Filling







            if self.is_filling_water and self.water_level < 1.0:







                self.water_level = min(1.0, self.water_level + dt * 0.45)







                if self.water_level >= 1.0:







                    self.is_filling_water = False







                    self.cook_step = COOK_STEP_IGNITE_STOVE







                    self.audio.play("click")







                    self.dialogue.start_dialogue([







                        ("Pot Filled", "The stainless steel pot is filled with fresh water.\nPick up the pot, then click the left burner to place it. Turn its brass knob to heat the water.", (200, 220, 240))







                    ])















            # Stove Burning & Boiling Water







            if self.stove_ignited:







                # Add flame particles under pot







                for _ in range(3):







                    fx = random.uniform(448 - 55, 448 + 55)







                    fy = 265 + random.uniform(0, 8)







                    fvy = random.uniform(25, 55)







                    col = random.choice([(60, 160, 240), (80, 200, 255), (140, 220, 255)])







                    self.flame_particles.append([fx, fy, random.uniform(-4, 4), fvy, random.uniform(4, 9), col, 200])















                if not self.water_boiling:







                    self.boil_timer += dt







                    if self.boil_timer >= 2.5:







                        self.water_boiling = True







                        self.audio.play("boil")







                        if self.cook_step == COOK_STEP_IGNITE_STOVE:







                            self.cook_step = COOK_STEP_ADD_NOODLES















            if not self.stove_ignited and not self.noodles_added:







                self.water_boiling=False







                self.boil_timer=0.0







                if self.cook_step==COOK_STEP_ADD_NOODLES:







                    self.cook_step=COOK_STEP_IGNITE_STOVE















            # Boiling Bubbles & Steam







            if self.water_boiling:







                if random.random() < 0.35:







                    self.boil_bubbles.append([







                        random.uniform(448 - 60, 448 + 60),







                        415 + random.uniform(0, 10),







                        random.uniform(3, 7),







                        random.uniform(35, 70),







                        200







                    ])







                if random.random() < 0.25:







                    self.steam_puffs.append([







                        random.uniform(448 - 50, 448 + 50),







                        445,







                        random.uniform(-10, 10),







                        random.uniform(40, 75),







                        random.uniform(12, 22),







                        140







                    ])















            # Noodles cooking progress







            if self.noodles_added and self.stove_ignited and self.noodle_cook_progress < 1.0:







                self.noodle_cook_progress = min(1.0, self.noodle_cook_progress + dt * 0.25)















            # Egg frying







            if self.egg_cracked and self.sprite_renderer.interaction.right_on and self.egg_cooked_progress < 1.0:







                self.egg_cooked_progress = min(1.0, self.egg_cooked_progress + dt * 0.20)







                if random.random() < 0.4:







                    self.sizzle_sparks.append([







                        random.uniform(848 - 55, 848 + 55),







                        345 + random.uniform(-15, 15),







                        random.uniform(-15, 15),







                        random.uniform(20, 50),







                        0.35







                    ])















            # Particle Updates







            for fp in self.flame_particles[:]:







                fp[0] += fp[2] * dt







                fp[1] += fp[3] * dt







                fp[6] -= dt * 350







                fp[4] = max(1.0, fp[4] - dt * 4.0)







                if fp[6] <= 0:







                    self.flame_particles.remove(fp)















            for bb in self.boil_bubbles[:]:







                bb[1] += bb[3] * dt







                bb[4] -= dt * 150







                if bb[1] > 340 or bb[4] <= 0:







                    self.boil_bubbles.remove(bb)















            for sp in self.steam_puffs[:]:







                sp[0] += sp[2] * dt







                sp[1] += sp[3] * dt







                sp[4] += dt * 16.0







                sp[5] -= dt * 90.0







                if sp[5] <= 0:







                    self.steam_puffs.remove(sp)















            for ss in self.sizzle_sparks[:]:







                ss[0] += ss[2] * dt







                ss[1] += ss[3] * dt







                ss[4] -= dt







                if ss[4] <= 0:







                    self.sizzle_sparks.remove(ss)















        # ---------------------------------------------------------------------







        # 3. Update Tarot Cards Mode (S08)







        # ---------------------------------------------------------------------







        elif self.mode == MODE_SERVE_TRANSITION:







            if self.transitioning_to_scene_8 and not self.dialogue.active:







                self.fade_alpha = min(255.0, self.fade_alpha + dt * 180.0)







                if self.fade_alpha >= 255.0:







                    self._return_to_dining_room()















    def _return_to_dining_room(self):







        """Transition into Scene 8: S08 Three Cards at Midnight."""







        from scenes.scene_8_view import Scene8View







        self.transitioning_to_scene_8=False







        self.window.show_view(Scene8View(meal_finished=True))















    # =========================================================================







    # DRAW LOGIC







    # =========================================================================







    def on_draw(self):







        self.clear(color=(12, 14, 20))















        if self.mode == MODE_EXPLORE_KITCHEN:







            self._draw_kitchen_exploration()







        elif self.mode == MODE_COOKING_MAMA:







            self._draw_cooking_mama()







        elif self.mode == MODE_INGREDIENT_STORAGE:



            self.sprite_renderer.draw_ingredient_storage()







        elif self.mode == MODE_SERVE_TRANSITION:







            self.sprite_renderer.exploration()







            if self.ui_cam:self.ui_cam.use()







            arcade.draw_rect_filled(arcade.XYWH(640,360,1500,800),(0,0,0,int(self.fade_alpha)))















        # UI Overlay







        if self.ui_cam:







            self.ui_cam.use()















        # Dialogue







        if self.dialogue.active:







            self.dialogue.draw()















        # Pause Overlay







        if self.mode == MODE_EXPLORE_KITCHEN and not self.ingredients_hud_dismissed:
            self._draw_collected_ingredients_hud()

        self.draw_pause_overlay()















    # -------------------------------------------------------------------------







    # 1. RENDER: Kitchen Exploration Mode







    # -------------------------------------------------------------------------







    def _draw_kitchen_exploration(self):







        self.sprite_renderer.exploration()















    def _draw_collected_ingredients_hud(self):
        """Stack collected ingredient cards at the top-right in pickup order."""
        tex = self.sprite_renderer.tex
        labels = {"noodles_dry": "NOODLES", "eggs_carton": "EGGS"}
        card_w, card_h, gap = 156.0, 54.0, 8.0
        cx = SCREEN_WIDTH - 22.0 - card_w / 2.0
        top = SCREEN_HEIGHT - 22.0
        for i, item in enumerate(self.collected_ingredients):
            cy = top - card_h / 2.0 - i * (card_h + gap)
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, card_w, card_h), (18, 22, 30, 226))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, card_w, card_h), COLOR_GOLD, 2.0)
            t = tex.get(item)
            if t is not None:
                scale = min(46.0 / t.width, 38.0 / t.height)
                arcade.draw_texture_rect(
                    t, arcade.XYWH(cx - card_w / 2.0 + 34.0, cy, t.width * scale, t.height * scale)
                )
            arcade.draw_text(labels.get(item, item.upper()), cx - card_w / 2.0 + 66.0, cy,
                             (240, 220, 170), 13, anchor_y="center", bold=True)


    def _draw_world_prompt(self, wx, wy, text, scale=1.0, highlight=False):







        bw = max(240.0, (len(text) * 9.2 + 40.0)) * scale







        bh = 44 * scale







        bg_col = (180, 70, 50, 220) if highlight else (25, 32, 45, 210)







        border_col = COLOR_GOLD if highlight else (110, 180, 245)







        arcade.draw_rect_filled(arcade.XYWH(wx, wy, bw, bh), bg_col)







        arcade.draw_rect_outline(arcade.XYWH(wx, wy, bw, bh), border_col, 2.0 if highlight else 1.2)







        arcade.draw_text(text, wx, wy - 6 * scale, (255, 255, 255) if highlight else (230, 240, 255),







                         int(11 * scale), anchor_x="center", bold=True)















    # -------------------------------------------------------------------------







    # 2. RENDER: Cooking Mama Interactive Countertop Mode







    # -------------------------------------------------------------------------







    def _draw_cooking_mama(self):







        self.sprite_renderer.cooking()















    def _draw_cook_button(self, bx, by, bw, bh, text, col, highlight=False):







        pulse = 1.0 + (0.05 * math.sin(self.t * 6.0) if highlight else 0.0)







        w = bw * pulse







        h = bh * pulse







        arcade.draw_rect_filled(arcade.XYWH(bx, by, w, h), col)







        arcade.draw_rect_outline(arcade.XYWH(bx, by, w, h), COLOR_GOLD if highlight else (255, 255, 255), 2)







        arcade.draw_text(text, bx, by - 6, (255, 255, 255), 13, anchor_x="center", bold=True)















    # -------------------------------------------------------------------------







    # 3. RENDER: S08 Midnight Tarot Cards







    # -------------------------------------------------------------------------







    def on_key_press(self, key, modifiers):







        if self.handle_pause_key(key):







            return















        if key == arcade.key.F11:







            self.toggle_fullscreen()







            return















        if self.dialogue.active:







            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):







                self.dialogue.advance()







            return















        if self.mode == MODE_INGREDIENT_STORAGE:



            if key in (arcade.key.B, arcade.key.E):



                self.close_ingredient_storage()



            return







        if self.mode == MODE_COOKING_MAMA and key == arcade.key.B:







            interaction=self.sprite_renderer.interaction







            if not interaction.motion:







                interaction.cancel()







                self.mode=MODE_EXPLORE_KITCHEN







                self.key_left=self.key_right=self.key_up=self.key_down=False







            return















        if self.mode == MODE_EXPLORE_KITCHEN:







            if key in (arcade.key.A, arcade.key.LEFT):







                self.key_left = True







            elif key in (arcade.key.D, arcade.key.RIGHT):







                self.key_right = True







            elif key in (arcade.key.W, arcade.key.UP):







                self.key_up = True







            elif key in (arcade.key.S, arcade.key.DOWN):







                self.key_down = True















            elif key == arcade.key.E:







                self._handle_kitchen_interact()















    def on_key_release(self, key, modifiers):







        if key in (arcade.key.A, arcade.key.LEFT):







            self.key_left = False







        elif key in (arcade.key.D, arcade.key.RIGHT):







            self.key_right = False







        elif key in (arcade.key.W, arcade.key.UP):







            self.key_up = False







        elif key in (arcade.key.S, arcade.key.DOWN):







            self.key_down = False















    def _handle_kitchen_interact(self):







        px = self.player.x







        target = self.sprite_renderer.exploration_target()







        interaction=self.sprite_renderer.interaction







        if target == 'door':







            self.kitchen_door_open = not self.kitchen_door_open







            self.audio.play("click")







            # Closing while behind the leaf pushes the player back in front of it.
            if not self.kitchen_door_open:
                self.player_behind_open_door = False
                fy = self.player.y - self.player.feet_offset + 8.0
                if self.player.x <= LEAF_X_MAX + 8.0 and is_behind_open_door(self.player.x, fy):
                    cx = min(LEAF_X_MAX, max(LEAF_X_MIN, self.player.x))
                    fy = open_door_leaf_bottom_y(cx) - 18.0
                    self.player.y = fy + self.player.feet_offset - 8.0

                closed_max_fy = get_closed_door_max_feet_y(self.player.x)
                if fy > closed_max_fy:
                    self.player.y = closed_max_fy + self.player.feet_offset - 8.0
                    fy = closed_max_fy

                min_x = get_closed_door_min_x(fy)
                if self.player.x < min_x:
                    self.player.x = min_x







            return







        if target == 'light_switch':







            self.kitchen_light_on = not self.kitchen_light_on







            self.audio.play("click")







            return







        if target=='table':







            self.dining.interact()







            return







        if target=='exit' and self.dining.eaten:







            self.mode=MODE_SERVE_TRANSITION







            self.transitioning_to_scene_8=True







            self.fade_alpha=0







            return







        if self.dining.ready or self.dining.eaten:







            self.dialogue.start_dialogue([('Chef','The meal is ready. I should eat at the kitchen table.' if self.dining.ready else 'The meal is finished. I should return to the living room.',(230,210,175),self.portrait_chef)])







            return







        if not self.kitchen_light_on and target in ('sink', 'knives', 'stove', 'fridge', 'pantry'):
            self.dialogue.start_dialogue([
                ("Chef", "It's too dark to cook. I need to turn on the kitchen light first.", (220, 205, 180), self.portrait_chef)
            ])
            return

        if target in ('sink','knives','stove') and (self.water_level>0 or self.cook_step>0):







            self.mode=MODE_COOKING_MAMA







            interaction.say(interaction.hint())







            return







        if target in ("fridge", "pantry"):



            self.audio.play("click")



            self.storage_target = target



            self.key_left = self.key_right = self.key_up = self.key_down = False



            self.mode = MODE_INGREDIENT_STORAGE



            return







        elif target == "sink":







            self.audio.play("boil")







            self.dialogue.start_dialogue([







                ("Kitchen Sink", "He turns the bronze valve. The old pipes shudder, then clean water flows steadily into the steel basin.", (180, 215, 245)),







                ("Chef", "\"The emergency utility line is still pressurized. Good.\"", (220, 205, 180), self.portrait_chef)







            ])







        # 3. Knife Block & Prep Table







        elif target == "knives":







            self.audio.play("click")







            self.dialogue.start_dialogue([







                ("Japanese Santoku Knife", "His forged Damascus steel knife resting on the wooden block. Still well-oiled and razor sharp.", (215, 180, 140)),







                ("Chef", "\"A knife meant for precision and life... not for abandonment.\"", (230, 210, 175), self.portrait_thinking)







            ])







        # 4. Stove Station (Enter Zoomed-in Cooking Mama Minigame!)







        elif target == "stove":



            if len(self.collected_ingredients) < 2:



                self.dialogue.start_dialogue([



                    ("Chef", "I should see what is in the cupboard and refrigerator first.", COLOR_GOLD, self.portrait_chef)



                ])



                return







            self.audio.play("click")







            self.mode = MODE_COOKING_MAMA







            self.dialogue.start_dialogue([







                ("Stove Range", "He stands before the gas range. The pot and skillet rest in position.\nFill the pot at the sink before moving it to the stove.", (210, 175, 120)),







                ("Step 1", "Turn the right brass valve to fill the pot with clean water.", COLOR_GOLD)







            ])















    def close_ingredient_storage(self):



        self.storage_target = None



        self.sprite_renderer.interaction.regions.clear()



        self.mode = MODE_EXPLORE_KITCHEN







    def take_storage_ingredient(self, x, y):



        item = "noodles_dry" if self.storage_target == "pantry" else "eggs_carton"



        if abs(x - 640) <= 135 and abs(y - 70) <= 20:



            self.close_ingredient_storage()



            return



        if item in self.collected_ingredients or self.sprite_renderer.interaction.hit(x, y) != item:



            return



        self.collected_ingredients.append(item)



        self.audio.play("click")



        self.close_ingredient_storage()



        if len(self.collected_ingredients) == 2:



            line = "Wide noodles and two eggs. I'll make a bowl of egg noodle soup. [Approach the stove and press E.]"



        elif item == "noodles_dry":



            line = "A block of dried wide noodles. I'll check the refrigerator too."



        else:



            line = "Two fresh eggs. Let's see what is in the cupboard."



        self.dialogue.start_dialogue([("Chef", line, COLOR_GOLD, self.portrait_chef)])







    def on_mouse_motion(self, x, y, dx, dy):







        if self.handle_pause_mouse_motion(x, y):







            return















        vx, vy = self.to_cooking_coords(x, y)















        self.sprite_renderer.interaction.pointer=(vx,vy)















    def on_mouse_press(self, x, y, button, modifiers):







        if self.handle_pause_mouse_press(x, y, button):







            return















        vx, vy = self.to_cooking_coords(x, y)















        if self.dialogue.active:







            self.dialogue.advance()







            return















        # ---------------------------------------------------------------------







        # Cooking Mama Clicks







        # ---------------------------------------------------------------------







        if self.mode == MODE_INGREDIENT_STORAGE:



            if button == arcade.MOUSE_BUTTON_LEFT:



                self.take_storage_ingredient(vx, vy)



            return







        if self.mode == MODE_COOKING_MAMA:







            point = self.sprite_renderer.interaction.click(vx, vy, button)







            if point is None:







                return







            vx, vy = point







            # The completed dish goes to the dining room. Scene 8 owns the ONLY card choice.







            if self.cook_step == COOK_STEP_ASSEMBLE_DISH:







                if abs(vx-SCREEN_WIDTH/2)<=160 and abs(vy-80)<=28:







                    self.cook_step=COOK_STEP_FINISHED







                    self.stove_ignited=False







                    self.sprite_renderer.interaction.right_on=False







                    self.mode=MODE_EXPLORE_KITCHEN







                    self.dining.ready=True







                    self.player.place(1370,385)







                    self.audio.play('achievement')







                    self.dialogue.start_dialogue([







                        ('A Bowl of Noodles','A warm bowl, made by his own hands. He carries it to the small kitchen table. [Approach the table and press E.]',(220,205,180))







                    ])







                    return























# Standalone runner for direct testing







if __name__ == "__main__":







    window = arcade.Window(







        SCREEN_WIDTH,







        SCREEN_HEIGHT,







        "Scene 7: The Old Home Kitchen & Immersive Cooking (S06 - S08)",







        resizable=False,







        fullscreen=START_FULLSCREEN







    )







    if START_FULLSCREEN:







        window.set_fullscreen(True)







    view = KitchenView()







    window.show_view(view)







    arcade.run()







