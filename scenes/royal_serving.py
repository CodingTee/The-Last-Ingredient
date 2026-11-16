"""Three physical ladlefuls followed by a separate dining-room delivery."""
import math
import arcade


class RoyalServing:
    TABLE_SOUP = (900, 382, 90, 65)
    CHEF_AT_TABLE = (808, 292)
    DINING_APPROACH = 2.5
    DINING_PLACE = .45

    def __init__(self,v,assets):
        self.v=v
        self.carry_frames = {}
        for direction, poses in v.player.textures.items():
            frames = []
            for pose in ('idle', 'walk1', 'idle', 'walk2'):
                texture = poses[pose]
                x0, y0, x1, y1 = texture.image.getchannel("A").point(
                    lambda alpha: 255 if alpha > 180 else 0,
                ).getbbox()
                frames.append(texture.crop(x0, y0, x1-x0, y1-y0))
            self.carry_frames[direction] = frames
        self.loaded_spoon = arcade.load_texture(assets / 'simmer_sprites_v1' / 'ladle_with_soup.png')
        self.bowl_frames = [arcade.load_texture(assets / 'departure_v1' / 'spoon_rest.png')]
        self.bowl_frames.extend(
            arcade.load_texture(assets / 'serving_v1' / f'bowl_soup_{count}.png')
            for count in range(1, 4)
        )
        source = arcade.load_texture(assets / 'dining_without_table.png')
        table = arcade.load_texture(assets / 'dining_table_foreground.png')
        crop_width = round(source.height * 1.6)
        crop = ((source.width - crop_width) // 2, 0, crop_width, source.height)
        self.dining = source.crop(*crop)
        self.table_front = table.crop(*crop)
        self.reset()

    def reset(self):self.mode='idle';self.time=0;self.selected=False;self.loaded=False

    @property
    def busy(self):return self.mode in {'scoop','pour','pack'}

    def update(self,dt):
        v=self.v;c=v.cook
        if v.page=='cooking' and c.stage=='serve' and self.busy:
            self.time+=dt
            if self.mode=='scoop' and self.time>=.65:self.loaded=True;self.mode='idle';self.time=0
            elif self.mode=='pour' and self.time>=.8:
                c.served=min(1,c.served+1/3);self.loaded=False;self.selected=c.served<1;self.mode='idle';self.time=0
                v.say('The bowl is full. Click the bowl to carry it.' if c.served>=1 else 'Scoop another ladleful from the pot.')
        elif v.page=='delivery':
            previous_time = self.time
            self.time+=dt
            if self.mode in {'exit', 'corridor'}:
                v.play_walk_step(previous_time, self.time, .13)
            elif self.mode == 'place':
                v.play_walk_step(min(previous_time, self.DINING_APPROACH), min(self.time, self.DINING_APPROACH), .13)
            if self.mode=='walk':
                k=v.walk_keys
                dx = int(bool(k & {arcade.key.D, arcade.key.RIGHT})) - int(bool(k & {arcade.key.A, arcade.key.LEFT}))
                dy = int(bool(k & {arcade.key.W, arcade.key.UP})) - int(bool(k & {arcade.key.S, arcade.key.DOWN}))
                x, y = v.walker.x, v.walker.y
                v.walker.move(dx, dy, dt)
                moved_x, moved_y = v.walker.x - x, v.walker.y - y
                if moved_x or moved_y:
                    if abs(moved_x) >= abs(moved_y):
                        self.carry_facing = 'right' if moved_x > 0 else 'left'
                    else:
                        self.carry_facing = 'up' if moved_y > 0 else 'down'
                    previous_step = self.carry_step
                    self.carry_step += dt
                    v.play_walk_step(previous_step, self.carry_step, .13)
                else:
                    self.carry_step = 0
                    v.audio.stop_footstep()
            elif self.mode=='exit' and self.time>=1.4:self.mode='corridor';self.time=0
            elif self.mode=='corridor' and self.time>=2.1:self.mode='place';self.time=0;v.location='dining'
            elif self.mode=='place' and self.time>=self.DINING_APPROACH + self.DINING_PLACE:
                self.mode='idle';self.time=0;v.deliver_story()

    def draw_bowl_at(self, x, y, width, height, interactive=False):
        count = min(3, max(0, round(self.v.cook.served * 3)))
        self.v.workstation.draw(
            'serve_bowl' if interactive else None, self.bowl_frames[count], x, y, width, height,
        )

    def draw_bowl(self, interactive=False):
        from scenes.royal_view import SPOON_REST_POS
        self.draw_bowl_at(*SPOON_REST_POS, 170, 75, interactive)

    def draw_spoon(self, head_x, head_y, width, loaded=False):
        spoon = self.loaded_spoon if loaded else self.v.simmer_sprites['ladle']
        height = width * spoon.height / spoon.width
        arcade.draw_texture_rect(spoon, arcade.XYWH(head_x + .32 * width, head_y + .30 * height, width, height))

    def draw(self):
        from scenes.royal_view import image, SPOON_REST_POS, RESTING_SPOON_RECT
        v=self.v;ws=v.workstation;ws.regions.clear()
        image(v.fill_background,720,450,1440,900)
        pot=v.sprites['royal_pot']
        mx,my,_,_=v.pot_renderer.draw(*v.CLOSEUP_POT)
        ws.regions.append(('serve_pot',pot,*v.CLOSEUP_POT,440/pot.width,0))
        for j in range(5):
            p=(v.clock*.25+j*.17)%1
            arcade.draw_circle_filled(v.CLOSEUP_POT[0]+math.sin(j+v.clock)*28,my+25+p*85,6+p*5,(230,224,207,round(45*(1-p))))
        self.draw_bowl(interactive=True)
        bowl_x, bowl_y = SPOON_REST_POS
        well_x = bowl_x - 24
        if self.mode == 'scoop':
            t = min(1, self.time / .65)
            arc = math.sin(math.pi * t)
            self.draw_spoon(mx, my + 110 * (1 - arc), 200, loaded=t > .52)
        elif self.mode == 'pour':
            t = min(1, self.time / .8)
            head_y = bowl_y + 78
            if .32 < t < .86:
                tail = min(1, (t - .32) / .18)
                arcade.draw_line(well_x, head_y - 8, well_x, head_y - 8 - 66 * tail, (211, 174, 96, 210), 4)
            self.draw_spoon(well_x, head_y, 200, loaded=t < .68)
        elif self.selected:
            self.draw_spoon(*v.mouse, 180, loaded=self.loaded)
        elif v.cook.served < 1:
            rect = RESTING_SPOON_RECT
            ws.draw('serve_ladle', v.simmer_sprites['ladle'], rect.x, rect.y, rect.width, rect.height)
        v.button('Back to kitchen',1170,828,220,40,'work_exit',not self.busy)

    def click(self,x,y,button):
        if self.busy:return
        v=self.v;c=v.cook;key=v.workstation.hit(x,y)
        if button==arcade.MOUSE_BUTTON_RIGHT:self.selected=False;self.loaded=False;return
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        if c.served>=1 and key=='serve_bowl':self.begin_delivery();return
        if key=='serve_ladle' and c.served<1:self.selected=True;return
        inside=v.pot_renderer.hit(x,y,*v.CLOSEUP_POT)
        if (key=='serve_pot' or inside) and self.selected and not self.loaded:
            self.mode='scoop';self.time=0
        elif key=='serve_bowl' and self.loaded:
            self.mode='pour';self.time=0

    def begin_delivery(self):
        v=self.v
        if v.cook.stage!='serve' or v.cook.served<1:return
        v.workstation.stop_input();self.selected=False;self.loaded=False
        self.mode='walk';self.time=0;v.page='delivery';v.walker.x=310;v.walker.y=330
        self.carry_facing = 'right'
        self.carry_step = 0
        v.departure.mode='carry';v.walk_keys.clear()

    def near_door(self):return math.dist((self.v.walker.x,self.v.walker.y),(1175,380))<105

    def enter_door(self):
        if self.mode=='walk' and self.near_door():
            self.mode='exit';self.time=0;self.exit_start=(self.v.walker.x,self.v.walker.y);self.v.walk_keys.clear()
            self.v.walker.door_open = True
            self.v.ping()

    def draw_carry(self, x, feet_y, height, facing, elapsed, alpha=255):
        from scenes.royal_view import image
        frame = self.carry_frames[facing][int(elapsed / .13) % 4]
        image(frame, x, feet_y + height/2, height * frame.width/frame.height, height, alpha)
        offset = {'right': .21, 'left': -.21, 'up': .22, 'down': 0}[facing]
        tray_x = x + height * offset
        tray_y = feet_y + height * (.44 + .008 * math.sin(elapsed * 24))
        image(self.v.sprites['tray'], tray_x, tray_y, height * .53, height * .18, alpha)
        image(self.bowl_frames[3], tray_x, tray_y + height * .035, height * .38, height * .13, alpha)

    def draw_dining_chef(self):
        from scenes.royal_view import image
        frame = self.carry_frames['right'][0]
        x, feet_y = self.CHEF_AT_TABLE
        image(frame, x, feet_y + 100, 200 * frame.width/frame.height, 200)

    def draw_delivery(self):
        from scenes.royal_view import image,text,box,GOLD,WHITE
        v=self.v
        if self.mode in {'walk','exit'}:
            v.departure.draw(door_fully_open=self.mode == 'exit')
            if self.mode=='walk':
                if v.walker.y < 220:
                    v.draw_prep_table()
                self.draw_carry(v.walker.x, v.walker.y, 200, self.carry_facing, self.carry_step)
                if v.walker.y >= 220:
                    v.draw_prep_table()
                None
                if self.near_door():
                    v._draw_world_prompt(
                        1195, 560, '[E] Exit to Dining Room',
                        highlight=True, action='delivery_door',
                    )
            else:
                v.draw_prep_table()
                t = min(1, self.time / 1.4)
                x, y = self.exit_start
                alpha = round(255 * min(1, (1 - t) / .25))
                self.draw_carry(x + (1177-x)*t, y + (463-y)*t, 200-70*t, 'up', self.time, alpha)
            return
        if self.mode == 'corridor':
            v.ui_camera.use()
            image(v.seasoning.corridor_scene, 720, 450, 1440, 900)
            t = min(1, self.time / 2.1)
            alpha = round(255 * min(1, t * 8, (1-t) * 7))
            self.draw_carry(812-92*t, 421-346*t, 112+222*t, 'down', self.time, alpha)
            return
        v.ui_camera.use()
        image(self.dining,720,450,1440,900)
        image(v.sprites['girl_seated'],900,469,200,198)
        chef_x, chef_feet = self.CHEF_AT_TABLE
        if self.time < self.DINING_APPROACH:
            progress = self.time / self.DINING_APPROACH
            x = 32 + (chef_x - 32) * progress
            feet_y = 352 + (chef_feet - 352) * min(1, progress * 3)
            self.draw_carry(x, feet_y, 170 + 30*progress, 'right', self.time)
            image(self.table_front, 720, 450, 1440, 900)
        else:
            self.draw_dining_chef()
            image(self.table_front, 720, 450, 1440, 900)
            progress = min(1, (self.time - self.DINING_APPROACH) / self.DINING_PLACE)
            x, y, width, height = self.TABLE_SOUP
            bowl_x, bowl_y = chef_x + 42, chef_feet + 95
            self.draw_bowl_at(
                bowl_x + (x - bowl_x) * progress, bowl_y + (y - bowl_y) * progress,
                76 + (width - 76) * progress, height,
            )
