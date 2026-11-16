"""Physical kitchen exit and a short automatic hand-washing bridge."""
import math
import arcade


class RoyalDeparture:
    HALL_EXIT_DURATION = 2.2

    def __init__(self,v,assets):
        self.v=v
        self.tex={n:arcade.load_texture(assets/'departure_v1'/(n+'.png')) for n in ('spoon_rest','chef_urgent')}
        self.hall_walk = self.load_hall_walk(assets / 'departure_v1' / 'chef_urgent_hall_walk.png')
        self.urgent_walk = self.load_urgent_walk(assets / 'departure_v1' / 'chef_urgent_walk.png')
        self.urgent_walk_left = [frame.flip_left_right() for frame in self.urgent_walk]
        self.urgent_step = 0.0
        self.urgent_facing_right = True
        self.wash_scene = arcade.load_texture(assets / 'departure_v1' / 'chef_washing_hands.png')
        self.water=arcade.load_sound(assets/'departure_v1/water.wav')
        self.player=None;self.mode=None;self.time=0

    @staticmethod
    def load_hall_walk(path):
        sheet = arcade.load_texture(path)
        frames = []
        for index in range(3):
            left = round(index * sheet.width / 3)
            right = round((index + 1) * sheet.width / 3)
            cell = sheet.crop(left, 0, right - left, sheet.height)
            bounds = cell.image.getchannel("A").point(lambda a: 255 if a > 180 else 0).getbbox()
            x0, y0, x1, y1 = bounds
            frames.append(cell.crop(x0, y0, x1 - x0, y1 - y0))
        return frames

    @staticmethod
    def load_urgent_walk(path):
        sheet = arcade.load_texture(path)
        frames = []
        for index in range(2):
            left = round(index * sheet.width / 3)
            right = round((index + 1) * sheet.width / 3)
            cell = sheet.crop(left, 0, right - left, sheet.height)
            x0, y0, x1, y1 = cell.image.getchannel("A").getbbox()
            frames.append(cell.crop(x0, y0, x1 - x0, y1 - y0))
        opposite_step = arcade.load_texture(path.with_name('chef_urgent_walk_opposite.png'))
        x0, y0, x1, y1 = opposite_step.image.getchannel("A").getbbox()
        frames.append(opposite_step.crop(x0, y0, x1 - x0, y1 - y0))
        return frames

    def start(self):
        v=self.v
        self.spoon_start = v.spoon_rect()
        v.workstation.stop_input();v.walk_keys.clear();v.cook.leave()
        v.walker.door_open=False
        self.urgent_step = 0.0
        self.urgent_facing_right = True
        self.mode='putdown';self.time=0;v.page='departure'

    def near_door(self):
        return math.dist((self.v.walker.x,self.v.walker.y),(1175,360))<105

    def enter_door(self):
        if self.mode=='walk' and self.near_door():
            self.mode='exit';self.time=0
            self.exit_start=(self.v.walker.x,self.v.walker.y)
            self.v.walk_keys.clear()
            self.v.walker.door_open=True
            self.v.ping('click')

    def update(self,dt):
        v=self.v
        if v.page!='departure':return
        self.time+=dt
        if self.mode=='putdown' and self.time>=1.3:
            self.mode='urgent';self.time=0;v.walker.x=310;v.walker.y=330
            v.player.facing='right'
        elif self.mode=='urgent' and self.time>=1.1:
            self.mode='walk';self.time=0
            v.player.facing='right'
        elif self.mode=='walk':
            cur_x,cur_y = v.walker.x, v.walker.y
            target_x, target_y = 1175.0, 348.0
            if cur_x < 1130.0:
                dx = 1.0
                dy = (330.0 - cur_y) * 0.1
            else:
                dx = target_x - cur_x
                dy = target_y - cur_y
                dist_to_door = math.hypot(dx, dy)
                if dist_to_door < 28 or cur_x >= 1155.0:
                    v.walker.door_open = True
                    self.enter_door()
                    return

            length = math.hypot(dx, dy)
            if length > 0.001:
                ndx, ndy = dx / length, dy / length
            else:
                ndx, ndy = 1.0, 0.0

            # Urgent jog towards hallway restroom
            run_speed = 260.0
            step_dt = dt * (run_speed / v.walker.speed)
            previous_x, previous_y = v.walker.x, v.walker.y
            v.walker.move(ndx, ndy, step_dt)
            if v.walker.x != previous_x:
                self.urgent_facing_right = v.walker.x > previous_x
            if (v.walker.x, v.walker.y) != (previous_x, previous_y):
                self.urgent_step += dt
            else:
                self.urgent_step = 0.0
            v.player.x = v.walker.x
            v.player.y = v.walker.y + v.player.feet_offset
            v.player.facing = 'right'
            v.player.update(dt * 1.5, ndx, ndy, bounds=(0, 2000, 0, 2000))
        elif self.mode=='exit' and self.time>=self.HALL_EXIT_DURATION:
            self.begin_wash()
        elif self.mode=='wash' and self.time>=2.4:
            v.workstation.washed = 1.0
            self.mode = 'empty'
            self.time = 0
            v.returned()

    def begin_wash(self):
        self.mode = 'wash'
        self.time = 0
        self.player = arcade.play_sound(self.water, volume=.25, loop=True)

    def draw_spoon_putdown(self, destination):
        t = min(1, self.time / 1.1)
        start = self.spoon_start
        rect = arcade.XYWH(
            start.x + (destination.x - start.x) * t,
            start.y + (destination.y - start.y) * t,
            start.width + (destination.width - start.width) * t,
            start.height + (destination.height - start.height) * t,
        )
        arcade.draw_texture_rect(self.v.simmer_sprites['ladle'], rect)

    def draw(self, door_fully_open=False):
        from scenes.royal_view import image,text,box,W,H,LEFT_HOB,SY,SH,GOLD,WHITE
        v=self.v
        if self.mode=='putdown':
            v.fill_closeup(heating=True)
            return
        if self.mode=='wash' and v.page=='departure':
            v.ui_camera.use()
            v.workstation.regions.clear()
            image(self.wash_scene, W/2, H/2, W, H)
            return
        v.map_camera.use()
        ratio='16x9' if v.window.width/v.window.height>=1.77 else '16x10'
        open_door = door_fully_open or self.mode == 'exit' or v.walker.door_open
        texture = v.open_door_backgrounds[ratio] if open_door else v.map_backgrounds['prepared'][ratio]
        image(texture,W/2,H/2,W)
        x,y=LEFT_HOB[0],LEFT_HOB[1]-SY+(H-SH)/2
        v.vessel_draw(x,y)
        for i in range(5):
            p=(v.clock*.25+i*.17)%1
            arcade.draw_circle_filled(x+math.sin(i+v.clock)*12,y+25+p*55,3+p*5,(231,225,209,round((1-p)*60)))
        behind_table = self.mode in {'urgent','walk'} and v.walker.y >= 220
        if not behind_table and self.mode != 'carry':
            v.draw_prep_table()
        if self.mode in {'urgent','walk'}:
            if self.mode == 'urgent':
                pose = self.tex['chef_urgent']
                height = v.player.sprite.height * .82
                image(pose, v.walker.x, v.walker.y + height/2, height * pose.width/pose.height, height)
            else:
                frames = self.urgent_walk if self.urgent_facing_right else self.urgent_walk_left
                cycle = (0, 1, 0, 2)
                pose = frames[cycle[int(self.urgent_step / .09) % len(cycle)]]
                height = v.player.sprite.height * .82
                image(pose, v.walker.x, v.walker.y + height / 2, height * pose.width / pose.height)
            if behind_table:
                v.draw_prep_table()
            v.ui_camera.use()
            top = H/2 + v.window.height/v.canvas.scale/2
            box(440,top-71,560,49,(19,17,16,232),(122,93,56))
            message = "The soup is ready! Urgh... sudden urge! Need the restroom now!" if self.mode == 'urgent' else 'Rushing to the corridor restroom...'
            arcade.draw_text(message,720,top-47,WHITE,16,anchor_x='center',anchor_y='center')
            v.map_camera.use()
        elif self.mode=='exit' and v.page=='departure':
            v.draw_hall_exit(
                self.hall_walk, self.time, self.exit_start, v.player.sprite.height * .82,
            )
            v.ui_camera.use()
            top = H/2 + v.window.height/v.canvas.scale/2
            box(440,top-71,560,49,(19,17,16,232),(122,93,56))
            arcade.draw_text('Exiting through the hall door...',720,top-47,WHITE,16,anchor_x='center',anchor_y='center')
            v.map_camera.use()
        # During the existing empty-kitchen event the camera remains in this room.
        if v.page=='absence':
            v.ui_camera.use()
            None

    def stop(self):
        if self.player:
            arcade.stop_sound(self.player);self.player=None
