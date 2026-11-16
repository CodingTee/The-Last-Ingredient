"""Dedicated first-person stone-board station for the prehistoric meal."""
import math
import arcade
from scenes.prehistoric_bbq_view import BBQCookingView, ART
from scenes.prehistoric_knife import show_spine, draw_knife_slot

BOARD_CENTER = (700., 350.)
BOARD_ROAST = (700., 380.)
BOARD_PLATE = (160., 250.)
BOARD_KNIFE = (1120., 420.)
CUT_X = (585., 702., 827.)
SERVING_POS = ((570., 380.), (830., 380.))


class CarvingBoardView(BBQCookingView):
    """Shares the recipe with the hearth; returning never resets knife cuts."""

    def __init__(self, hearth_view):
        self.cut_anim = 0.
        self.cut_pending = False
        self.cut_cursor = (0., 0.)
        self.serving_index = None
        self.shake_t = 0.
        self.shake_amp = 0.
        self.cut_vibe_t = 0.
        self.vibe_clock = 0.
        self.last_vibe_sound = -1.
        super().__init__(return_view=hearth_view.return_view, meal=hearth_view.meal, mode='board')
        self.add_sprite("knife_edge", ART / "knife_rough_branch_spine_v1.png")
        self.add_sprite("board_knife_rest",ART / "knife_rough_branch_normal_v1.png")
        self.hearth_view = hearth_view
        self.dialogue = False
        # The ground is a downward-looking crop of the exact same village plate.
        ground = self.sprites['camp'].texture
        y = round(ground.height * .34)
        self.add_texture_sprite('board_ground', ground.crop(0, y, ground.width, ground.height-y))
        for i in range(4):
            self.add_sprite('board_carve_' + str(i), ART / ('board_carve_' + str(i) + '.png'))
        cut = self.sprites['board_carve_3'].texture
        split = cut.width // 2
        for i, (x, width) in enumerate(((0, split), (split, cut.width-split))):
            texture = cut.crop(x, 0, width, cut.height)
            for prefix in ('board_serving_', 'board_plated_', 'board_drag_'):
                self.add_texture_sprite(prefix + str(i), texture)

    def trigger_shake(self, amp=6.0, duration=0.20):
        self.shake_amp = amp
        self.shake_t = duration

    def stop_input(self):
        super().stop_input()
        self.cut_anim = 0.
        self.cut_pending = False
        self.serving_index = None
        self.shake_t = 0.
        self.cut_vibe_t = 0.

    def check_cutting_motion(self, x, y, old_x, old_y):
        if self.meal.stage != 'carve' or not self.knife_held or self.cut_anim > 0:
            return False
        target_x = CUT_X[self.meal.cuts]
        dist_x = abs(x - target_x)
        if dist_x > 45 or y < 270 or y > 490:
            return False
        move_y = y - old_y
        return move_y < -0.4

    def feed_cut_vibration(self):
        self.cut_vibe_t = 0.14
        import random
        if len(self.particles) < 40:
            mx, my = self.mouse
            self.particles.append([
                mx + random.uniform(-4, 4), my + random.uniform(-4, 4),
                random.uniform(-55, 55), random.uniform(20, 85),
                0.22, 'cut_spark'
            ])
        if self.t - self.last_vibe_sound > 0.09:
            self.last_vibe_sound = self.t
            self.sound('meat_slice', 0.35)

    def on_update(self, dt):
        if self.is_paused:
            return
        super().on_update(dt)
        self.vibe_clock += dt
        self.cut_vibe_t = max(0., self.cut_vibe_t - dt)
        self.shake_t = max(0., self.shake_t - dt)
        dt = min(.05, dt)
        if self.cut_anim > 0:
            previous = self.cut_anim
            self.cut_anim = max(0., self.cut_anim-dt)
            if self.cut_pending and previous > .11 >= self.cut_anim:
                self.cut_pending = False
                if self.meal.cut():
                    self.sound('chop')
                    self.trigger_shake(4.0, 0.18)
                    if self.meal.stage == 'plate':
                        self.knife_held = False
                        self.message('Four cooked slices. Divide them into the guards\' two servings.')
            if self.cut_anim == 0:
                self.cut_pending = False
        self.window.bbq_progress = self.meal.save()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        x, y = self.coords(x, y)
        self.mouse = self.start = (x, y)
        self.stroke = 0.
        if self.cut_anim > 0:
            return
        if self.hit(x, y, 100, 674, 150, 48):
            self.back_to_hearth()
            return
        if self.meal.stage == 'carve':
            if self.hit(x, y, *BOARD_KNIFE, 140, 260):
                self.knife_held = True
                self.drag = 'knife_pickup'
                self.message('Drag to the top of the bright line, then swipe down.')
            elif self.hit(x, y, *BOARD_ROAST, 520, 250):
                if self.knife_held:
                    self.drag = 'cut'
                else:
                    self.message('Pick up the flint knife on the right first.')
        elif self.meal.stage == 'plate':
            for i, pos in enumerate(SERVING_POS):
                if not self.meal.portion_mask & (1 << i) and self.hit(x, y, *pos, 250, 220):
                    self.drag = 'portion'
                    self.serving_index = i
                    return
        elif self.meal.stage == 'carry' and self.hit(x, y, *BOARD_PLATE, 300, 220):
            self.carry_to_village()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return
        x, y = self.coords(x, y)
        oldx, oldy = self.mouse
        self.mouse = (x, y)
        if self.knife_held and self.meal.stage == 'carve' and not self.drag:
            if self.check_cutting_motion(x, y, oldx, oldy):
                self.feed_cut_vibration()
            elif math.hypot(x - oldx, y - oldy) > 2.0:
                self.cut_vibe_t = 0.

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.is_paused or self.cut_anim > 0:
            return
        x, y = self.coords(x, y)
        oldx, oldy = self.mouse
        self.mouse = (x, y)
        if self.drag=='knife_pickup':
            target=CUT_X[self.meal.cuts]
            if abs(x-target)<45 and 410<=y<=490:
                self.drag='cut';self.start=(x,y);self.stroke=0.
            return
        if self.meal.stage == 'carve' and self.knife_held and not self.drag and (buttons & arcade.MOUSE_BUTTON_LEFT):
            self.drag = 'cut'; self.start = (oldx, oldy); self.stroke = 0.
        if self.check_cutting_motion(x, y, oldx, oldy):
            self.feed_cut_vibration()
        elif math.hypot(x - oldx, y - oldy) > 2.0:
            self.cut_vibe_t = 0.
        if self.drag == 'cut':
            self.stroke += max(0, oldy - y)
            target = CUT_X[self.meal.cuts]
            if self.stroke >= 90 and abs(x - target) < 45 and y <= 315:
                self.cut_cursor = (target, 350)
                self.cut_anim = .24
                self.cut_pending = True
                self.drag = None
                self.cut_vibe_t = 0.
                self.trigger_shake(1.5, 0.10)

    def on_mouse_release(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.is_paused:
            self.stop_input()
            return
        x, y = self.coords(x, y)
        drag = self.drag
        self.drag = None
        if drag=='knife_pickup':
            self.knife_held=self.hit(x,y,*BOARD_ROAST,520,270)
        elif drag == 'cut' and self.meal.stage == 'carve':
            target = CUT_X[self.meal.cuts]
            if (self.stroke >= 90 and abs(self.start[0]-target) < 45 and
                    abs(x-target) < 55 and self.start[1] >= 410 and y <= 345):
                self.cut_cursor = (target, 350)
                self.cut_anim = .24
                self.cut_pending = True
                self.trigger_shake(1.5, 0.10)
            else:
                self.message('Start above the highlighted line; swipe down through the roast.')
        elif drag == 'portion':
            if self.hit(x, y, *BOARD_PLATE, 300, 220):
                if self.meal.portion(self.serving_index):
                    self.sound('paper_slide')
                    if self.meal.stage == 'carry':
                        self.message('Both servings are ready. Pick up the platter.')
            else:
                self.message('Release the serving over the stone platter on the left.')
            self.serving_index = None
        self.window.bbq_progress = self.meal.save()

    def back_to_hearth(self):
        self.stop_input()
        self.window.bbq_progress = self.meal.save()
        self.hearth_view.meal = self.meal
        self.window.show_view(self.hearth_view)

    def carry_to_village(self):
        if self.meal.stage == 'carry':
            super().leave()

    def leave(self):
        # A station's back control returns to its originating hearth closeup.
        self.back_to_hearth()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.B and not self.is_paused and self.cut_anim == 0:
            self.back_to_hearth()
            return
        super().on_key_press(key, modifiers)

    def knife_at_cursor(self, x, y, dip=0, angle=0):
        show_spine(self,'knife_edge',x,y,dip,angle)

    def on_draw(self):
        self.clear((31, 34, 24))
        ox, oy = 0., 0.
        if self.shake_t > 0:
            decay = self.shake_t / 0.22
            ox += math.sin(self.shake_t * 68.0) * self.shake_amp * decay
            oy += math.cos(self.shake_t * 85.0) * self.shake_amp * 0.75 * decay
        if self.cut_vibe_t > 0:
            vibe_strength = min(1.0, self.cut_vibe_t / 0.05)
            ox += math.sin(self.vibe_clock * 95.0) * 1.0 * vibe_strength
            oy += math.cos(self.vibe_clock * 125.0) * 0.7 * vibe_strength
        if self.camera:
            self.camera.position = (640. + ox, 360. + oy)
        self.use_game_camera()
        for sprite in self.sprites.values():
            sprite.visible = False
        self.background('board_ground')
        self.show('slab', *BOARD_CENTER, 820)
        self.show('plate', *BOARD_PLATE, 290)
        if self.meal.stage == 'carve':
            self.show('board_carve_' + str(self.meal.cuts), *BOARD_ROAST, 520)
        elif self.meal.stage in ('plate', 'carry'):
            for i, pos in enumerate(SERVING_POS):
                if not self.meal.portion_mask & (1 << i) and self.serving_index != i:
                    self.show('board_serving_' + str(i), *pos, 260)
        for i in (0, 1):
            if self.meal.portion_mask & (1 << i):
                self.show('board_plated_' + str(i), 90+i*135, 274, 125)
        if self.drag == 'portion' and self.serving_index is not None:
            self.show('board_drag_' + str(self.serving_index), *self.mouse, 220)
        if self.cut_anim > 0:
            progress = 1-self.cut_anim/.24
            x, y = self.cut_cursor
            strength = math.sin(math.pi * progress)
            x += 1.5 * strength * math.sin(self.vibe_clock * 84)
            angle = 1.5 * strength * math.cos(self.vibe_clock * 84)
            self.knife_at_cursor(x, y, 30*abs(2*progress-1), angle=angle)
        elif self.knife_held:
            kx = self.mouse[0]
            ky = self.mouse[1]
            k_angle = 0.0
            if self.cut_vibe_t > 0:
                vibe_strength = min(1.0, self.cut_vibe_t / 0.05)
                kx += math.sin(self.vibe_clock * 145.0) * 1.8 * vibe_strength
                ky += math.cos(self.vibe_clock * 185.0) * 1.2 * vibe_strength
                k_angle = math.sin(self.vibe_clock * 125.0) * 1.8 * vibe_strength
            self.knife_at_cursor(kx, ky, angle=k_angle)
        else:
            self.show('board_knife_rest', *BOARD_KNIFE, 210, -90)
        self.order(['board_ground','slab','plate'] + ['board_carve_'+str(i) for i in range(4)] +
                   ['board_serving_0','board_serving_1','board_plated_0','board_plated_1',
                    'board_drag_0','board_drag_1','knife','board_knife_rest','knife_edge'])
        self.layers.draw()
        self.draw_particles()
        self.draw_board_hud()
        draw_knife_slot(self,BOARD_KNIFE,'board_knife_rest')
        self.draw_pause_overlay()
        if self.camera:
            self.camera.position = (640., 360.)

    def draw_board_hud(self):
        for x, width in ((100,150),(720,980)):
            arcade.draw_rect_filled(arcade.XYWH(x,674,width,48),(18,22,30,235))
            arcade.draw_rect_outline(arcade.XYWH(x,674,width,48),(110,180,245,140),1.2)
        self.label('board_back','< BACK TO FIRE',100,674,11,(200,220,240),'center')
        stage = self.meal.stage
        instruction = {'carve': 'Drag the right-hand knife to a bright line, then swipe down.',
                       'plate': 'Drag each pair of cooked slices onto the stone platter.',
                       'carry': 'The guards\' meal is ready. Click the loaded platter to carry it.'}[stage]
        self.label('board_instruction',instruction,250,674,12)
        self.step_meter(1070,674,'CUTS' if stage=='carve' else 'SERVINGS',
                        self.meal.cuts if stage=='carve' else self.meal.portions,3 if stage=='carve' else 2)
        self.label('board_title','THE STONE CUTTING BOARD',700,600,13,(245,224,182),'center')
        if stage == 'carve':
            for i in range(self.meal.cuts,3):
                x = CUT_X[i]
                if i == self.meal.cuts and self.cut_vibe_t > 0:
                    arcade.draw_line(x,470,x,292,(255,160,60,160),8)
                    arcade.draw_line(x,470,x,292,(255,245,210,255),5)
                else:
                    arcade.draw_line(x,470,x,292,(255,220,145,230 if i==self.meal.cuts else 70),2)
            if self.knife_held and self.cut_vibe_t > 0:
                vibe_strength = min(1.0, self.cut_vibe_t / 0.05)
                mx = self.mouse[0] + math.sin(self.vibe_clock * 145.0) * 1.8 * vibe_strength
                my = self.mouse[1] + math.cos(self.vibe_clock * 185.0) * 1.2 * vibe_strength
                r = 14.0 + 3.5 * math.sin(self.vibe_clock * 110.0)
                arcade.draw_circle_outline(mx, my, r, (255, 235, 150, 235), 2.5)
                arcade.draw_circle_outline(mx, my, r + 5.0, (255, 150, 70, 150), 1.5)
                arcade.draw_circle_filled(mx, my, 4.0, (255, 245, 200, 240))

        elif stage == 'plate':
            self.label('plate_hint','PLACE BOTH SERVINGS HERE',160,125,11,anchor='center')
        elif stage == 'carry':
            arcade.draw_ellipse_outline(*BOARD_PLATE,300,210,(242,207,122,160),2)
            self.label('take_hint','[CLICK] CARRY THE PLATTER',160,125,11,anchor='center')
        if self.notice_t > 0:
            self.label('board_notice',self.notice,700,44,12,(255,218,145),'center')
        self.label('board_footer','B  Return to fire     /     Esc  Pause',700,15,10,(215,208,189),'center')
