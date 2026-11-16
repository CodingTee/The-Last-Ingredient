"""A physical last spoon of salt; narrative contamination remains predetermined."""
import math
import arcade


class RoyalSeasoning:
    def __init__(self,v,assets):
        self.v=v
        self.corridor_scene = arcade.load_texture(assets / 'departure_v1' / 'chef_return_corridor.png')
        self.peek_scene = arcade.load_texture(assets / 'departure_v1' / 'chef_peeks_into_kitchen.png')
        self.peek_left_scene = arcade.load_texture(assets / 'departure_v1' / 'chef_peeks_looking_left.png')
        self.salt_stream = arcade.load_texture(assets / 'seasoning_v1' / 'salt_stream.png')
        self.return_frames = {}
        for facing in ('up', 'down'):
            frames = []
            for pose in ('idle', 'walk1', 'walk2'):
                texture = v.player.textures[facing][pose]
                left, top, right, bottom = texture.image.getchannel("A").getbbox()
                frames.append(texture.crop(left, top, right-left, bottom-top))
            self.return_frames[facing] = frames
        self.tex = {}
        for n in ('salt_spoon_empty', 'salt_spoon_loaded'):
            p = assets / 'seasoning_v1' / (n + '_silver.png')
            if not p.exists():
                p = assets / 'seasoning_v1' / (n + '.png')
            self.tex[n] = arcade.load_texture(p)
        self.reset()

    def reset(self):
        self.mode='idle';self.time=0;self.loaded=False
        self.salt_collected = False

    SALT_POS = (548, 368)

    def near_salt(self):
        walker = self.v.walker
        x, _ = self.SALT_POS
        return abs(walker.x - x) <= 78 and 145 <= walker.y <= 345

    @property
    def busy(self):return self.mode in {'scoop','pour'}

    RETURN_STEP = .09
    WARP_POINT = 1 - 2 * RETURN_STEP
    SHAKE_DURATION = .28
    PEEK_TURN_TIME = .9
    PEEK_BLEND_DURATION = .18
    PEEK_DURATION = 2.0

    def begin_return(self):
        self.reset();self.mode='corridor';self.v.page='return_entry'
        self.return_progress = 0.0
        self.return_stride = 0.0
        self.return_facing = "up"
        self.return_moving = False
        self.warp_triggered = False
        self.shake_remaining = 0.0
        self.v.workstation.stop_input()

    def update(self,dt):
        v=self.v
        if v.page == 'return_entry':
            if self.mode == 'corridor':
                self.update_corridor(dt)
            elif self.mode == 'peek':
                self.time += dt
                if self.time >= self.PEEK_DURATION:
                    self.mode = 'idle'
                    v.walker.x, v.walker.y = 1175, 340
                    v.walker.door_open = True
                    v.returned_dialogue()
        elif self.busy and v.page=='cooking' and v.cook.stage=='returned':
            self.time+=dt
            if self.mode=='scoop' and self.time>=.85:
                self.mode='idle';self.loaded=True;self.time=0
                v.say('One spoon of salt. Click inside the pot to season.')
            elif self.mode=='pour' and self.time>=.9:
                self.mode='idle';self.loaded=False;self.time=0;v.season()

    def update_corridor(self, dt):
        v = self.v
        self.return_moving = False
        if self.shake_remaining > 0:
            self.shake_remaining = max(0, self.shake_remaining - dt)
            return
        forward = bool(v.walk_keys & {arcade.key.W, arcade.key.UP})
        backward = bool(v.walk_keys & {arcade.key.S, arcade.key.DOWN})
        if forward != backward:
            facing = 'up' if forward else 'down'
            if self.return_facing != facing:
                self.return_stride = 0.0
                self.return_facing = facing
        old = self.return_progress
        self.return_progress = min(1, max(0, old + (forward - backward) * dt * .34))
        if not self.warp_triggered and self.return_progress >= self.WARP_POINT:
            self.return_progress = self.WARP_POINT
            self.warp_triggered = True
            self.shake_remaining = self.SHAKE_DURATION
            self.return_stride = 0.0
            v.audio.play('time_warp', volume_scale=.7)
            return
        distance = abs(self.return_progress - old)
        self.return_moving = distance > 0
        previous_stride = self.return_stride
        self.return_stride += distance
        v.play_walk_step(previous_stride, self.return_stride, self.RETURN_STEP / 2)
        if not self.return_moving:
            v.audio.stop_footstep()
        if self.return_progress >= 1:
            self.mode = 'peek'
            self.time = 0
            v.walk_keys.clear()

    def draw_return(self):
        from scenes.royal_view import image, text, W, H, WHITE
        self.v.ui_camera.use()
        if self.mode == 'peek':
            blend = min(1, max(0, (self.time - self.PEEK_TURN_TIME) / self.PEEK_BLEND_DURATION))
            if blend < 1:
                image(self.peek_scene, W/2, H/2, W, H)
            if blend > 0:
                image(self.peek_left_scene, W/2, H/2, W, H, alpha=round(255 * blend))
            return

        remaining = self.shake_remaining
        strength = 7 * remaining / self.SHAKE_DURATION
        dx = math.sin(remaining * 155) * strength
        dy = math.cos(remaining * 118) * strength * .65
        scene = self.corridor_scene
        scale = max(W / scene.width, H / scene.height) * 1.02
        image(scene, W/2 + dx, H/2 + dy, scene.width * scale, scene.height * scale)

        progress = self.return_progress
        cycle = (0, 1, 0, 2)
        step = int(self.return_stride / (self.RETURN_STEP / 2)) % len(cycle)
        frame = self.return_frames[self.return_facing][cycle[step] if self.return_moving else 0]
        x = W/2 + 85 * progress
        y = 72 + 328 * progress
        height = 345 - 204 * progress
        image(frame, x + dx, y + height/2 + dy, height * frame.width/frame.height, height)
        text('Hold W or Up to walk toward the kitchen.', W/2, 32, 14, WHITE, anchor_x='center')

    def draw(self):
        from scenes.royal_view import image
        v=self.v;ws=v.workstation;ws.regions.clear()
        image(v.fill_background,720,450,1440,900)
        v.draw_spoon_rest()
        if v.hold != 'stir':
            v.draw_resting_spoon()
        pot=v.sprites['royal_pot']
        mx,my,_,_=v.pot_renderer.draw(*v.CLOSEUP_POT)
        ws.regions.append(('pot',pot,*v.CLOSEUP_POT,440/pot.width,0))
        for j in range(5):
            phase=(v.clock*.3+j*.17)%1
            arcade.draw_circle_filled(mx+math.sin(v.clock+j)*35,my+25+phase*90,6+phase*7,(230,223,209,round(45*(1-phase))))
        if v.hold == 'stir':
            arcade.draw_texture_rect(v.simmer_sprites['ladle'], v.spoon_rect())
        if v.cook.salted:
            v.button('Back to kitchen',1170,828,220,40,'work_exit')
            return
        ws.draw('salt',v.sprites['salt'],810,440,140,180)
        if self.mode=='scoop':
            t=min(1,self.time/.85)
            x=640+170*math.sin(t*math.pi);y=430+100*math.sin(t*math.pi)
            image(self.tex['salt_spoon_loaded' if t>.55 else 'salt_spoon_empty'],x,y,160,110)
        elif self.mode=='pour':
            t=min(1,self.time/.9)
            tex=self.tex['salt_spoon_empty' if t>.82 else 'salt_spoon_loaded']
            arcade.draw_texture_rect(tex,arcade.XYWH(650-180*min(1,t*1.5),500+180*min(1,t*1.5),160,160*tex.height/tex.width),angle=-30*max(0,min(1,(t-.55)/.25)))
            if t > .58:
                progress = (t - .58) / .42
                sx, sy, _, _ = v.pot_renderer.surface(v.cook.water, *v.CLOSEUP_POT)
                release_y = 656
                stream_top = release_y + (sy - release_y) * max(0, 2 * progress - 1)
                stream_bottom = release_y + (sy - release_y) * min(1, 2 * progress)
                if stream_top > stream_bottom:
                    arcade.draw_texture_rect(
                        self.salt_stream,
                        arcade.XYWH(sx - 17, (stream_top + stream_bottom) / 2, 12, stream_top - stream_bottom),
                        alpha=round(230 * min(1, 5 * (1 - progress))),
                    )
        elif self.loaded:
            image(self.tex['salt_spoon_loaded'],v.mouse[0]+65,v.mouse[1]+35,160,110)
        else:ws.draw('salt_spoon',self.tex['salt_spoon_empty'],650,430,160,110)
        v.button('Back to kitchen',1170,828,220,40,'work_exit',not self.busy)

    def click(self,x,y,button):
        v = self.v
        if v.cook.salted:
            from scenes.royal_view import RESTING_SPOON_RECT
            rect = RESTING_SPOON_RECT
            if (button == arcade.MOUSE_BUTTON_LEFT and rect.left <= x <= rect.right
                    and rect.bottom <= y <= rect.top):
                v.hold = 'stir'
                v.stir_angle = None
                v.stir_travel = 0
            return
        key = v.workstation.hit(x, y)
        if self.busy or not self.salt_collected:return
        if button==arcade.MOUSE_BUTTON_RIGHT:
            self.loaded=False;return
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        # The soup surface is a hole in the pot alpha sprite, so include its oval.
        inside=v.pot_renderer.hit(x,y,*v.CLOSEUP_POT)
        if (key=='pot' or inside) and self.loaded:
            self.mode='pour';self.time=0;v.hold=None;return
        if key in {'salt','salt_spoon'} and not self.loaded:
            self.mode='scoop';self.time=0;v.ping()
