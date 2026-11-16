"""First-person dinosaur preparation. All food, tools and blood are sprites."""
import math
import arcade
from core.prehistoric_meal import PEEL_PIECES
from scenes.prehistoric_bbq_view import BBQCookingView, ART, RACK_CENTER
from scenes.prehistoric_knife import draw_knife_slot

BOARD=(700.,350.)
KNIFE=(1130.,400.)
TRAY=(180.,210.)
CUT_PATHS=(((855.,382.),(725.,312.)),((855.,382.),(725.,312.)))
CUT_X=tuple((a[0]+b[0])/2 for a,b in CUT_PATHS)
PEEL_GRIP=(818.,380.)
PEEL_TRAVEL=160.
BONE_SOCKET=(607.,308.)
BONE_AXIS=(math.cos(math.pi/6), .5)
BONE_WIDTH=210.
BONE_EXPOSED=62.
BONE_TRAVEL=145.
BONE_STRAIN_START=70.
BONE_RELEASE_TIME=.30
BONE_STRETCH_TIME=.08
BONE_STRETCH_POSE=(657.,311.,442.)
BONE_GRIP=tuple(point-axis*BONE_EXPOSED for point, axis in zip(BONE_SOCKET, BONE_AXIS))
BONE_END=tuple(point-axis*BONE_TRAVEL for point, axis in zip(BONE_GRIP, BONE_AXIS))
# Deboning drag pose: tilt the pulled-out bone toward bottom-left
# (left end down, right end up). In arcade a POSITIVE angle rotates the
# sprite clockwise (right end dips down), so the desired left-end-down
# tilt needs a NEGATIVE angle. The bone art already leans this way a
# little, so this adds on top of its native tilt.
BONE_LEAN=-30.
MEAT_WIDTH=370.
SKEWER_TARGET=(945.,350.)
PREP_TEXT=(
 'Pick up the flint knife. Follow the diagonal cut across the marked joint.',
 'Drag the separated thigh onto the stone cutting board on the left.',
 'Grip the hide with the wooden tongs. Pull right to remove one section at a time.',
 'Grab the exposed bone and pull it down and left.',
 'Drag the clean meat rightward along the pointed wooden spit.',
 'Lift the loaded spit onto the small rack on the right.',
)

class DinosaurPrepView(BBQCookingView):
    def __init__(self,return_view=None,saved=None,meal=None):
        self.bone_release=0.
        self.last_prep_drag_sound=-1.
        self.cut_anim=0.
        self.cut_pending=None
        self.cut_cursor=(0.,0.)
        self.cut_segment=((0.,0.),(0.,0.))
        self.cut_deviation=0.
        self.shake_t=0.
        self.shake_amp=0.
        self.cut_vibe_t=0.
        self.vibe_clock=0.
        self.last_vibe_sound=-1.
        super().__init__(return_view=return_view,saved=saved,meal=meal,mode='prep')
        self.dialogue=False
        tex=arcade.load_texture(ART/'dinosaur_prep_atlas_v1.png')
        for i in range(3):
            self.add_texture_sprite('prep_body_'+str(i),tex.crop(i*512,140,512,280))
        for i,name in enumerate(('prep_thigh',None,'prep_blood')):
            if name:
                self.add_texture_sprite(name,tex.crop(i*512,632,512,320))
        ground=self.sprites['camp'].texture
        y=round(ground.height*.34)
        self.add_texture_sprite('prep_ground',ground.crop(0,y,ground.width,ground.height-y))
        self.add_sprite('prep_peel_tool',ART/'peel_tongs_v1.png')
        self.add_sprite('prep_knife',ART/'knife_rough_branch_perspective_v1.png')
        peel_atlas = arcade.load_texture(ART/'prep_thigh_peel_atlas_v2.png')
        cell_width, cell_height = peel_atlas.width // 3, peel_atlas.height // 2
        self.peel_frames = tuple(f'peel_frame_{i}' for i in range(4))
        for i, name in enumerate((*self.peel_frames, 'prep_deboned')):
            self.add_texture_sprite(name, peel_atlas.crop(
                (i % 3)*cell_width, (i // 3)*cell_height, cell_width, cell_height))
        self.add_sprite('prep_socket_stretch', ART/'prep_socket_stretch_v1.png')
        self.bone_texture = peel_atlas.crop(1114, 702, 340, 165)
        self.bone_crops = {}
        self.add_texture_sprite('prep_bone', self.bone_texture)
        meat = self.sprites['prep_deboned'].texture
        # Reuse the meat's own pixels so the foreground lip matches the base.
        scale = MEAT_WIDTH / meat.width
        self.bone_lip_layout = []
        for row in range(20):
            # Shape the inner lip around the socket with aligned texture strips.
            lip_y = 268 + row*6
            lip_x = round(119 + 17*((row-9.5)/9.5)**2)
            lip_width = 154-lip_x
            name = f'prep_bone_lip_{row}'
            self.add_texture_sprite(name, meat.crop(lip_x, lip_y, lip_width, 6))
            self.bone_lip_layout.append((
                name,
                BOARD[0] + (lip_x + lip_width/2 - meat.width/2)*scale,
                BOARD[1] + (meat.height/2 - lip_y - 3)*scale,
                lip_width*scale,
            ))
        self.add_sprite('prep_knife_rest',ART/'knife_rough_branch_normal_v1.png')
        self.add_texture_sprite('prep_rack',self.sprites['spit_supports'].texture)

    def trigger_shake(self, amp=6.0, duration=0.20):
        self.shake_amp = amp
        self.shake_t = duration

    def stop_input(self):
        super().stop_input()
        self.cut_anim=0.
        self.cut_pending=None
        self.shake_t=0.
        self.cut_vibe_t=0.

    def commit(self,action):
        old_step=self.meal.prep_step
        if self.meal.prepare(action):
            if self.meal.prep_step!=old_step:self.notice_t=0.
            cue, volume = {
                'cut': ('chop', .65), 'portion': ('table_slam', .24),
                'peel': ('paper_slide', .68), 'debone': ('lock_unlock', .52),
                'skewer': ('meat_slice', .48), 'mount': ('lock_click', .55),
            }[action]
            self.sound(cue, volume)
            if action == 'debone':
                self.bone_release = BONE_RELEASE_TIME
                self.trigger_shake(2.5, .14)
            self.window.bbq_progress=self.meal.save()
            if self.meal.prepared:
                self.stop_input()
                self.window.show_view(BBQCookingView(return_view=self.return_view,meal=self.meal))
            return True
        return False

    def check_cutting_motion(self, x, y, old_x, old_y):
        step = self.meal.prep_step
        if step not in (0, 3) or not self.knife_held or self.cut_anim > 0:
            return False
        a, b = self.cut_guide()
        dx, dy = b[0] - a[0], b[1] - a[1]
        line_len_sq = dx * dx + dy * dy
        if line_len_sq < 1:
            return False
        t = ((x - a[0]) * dx + (y - a[1]) * dy) / line_len_sq
        t_clamped = max(0., min(1., t))
        px = a[0] + t_clamped * dx
        py = a[1] + t_clamped * dy
        dist = math.hypot(x - px, y - py)
        if dist > 45 or t < -0.15 or t > 1.15:
            return False
        move_x = x - old_x
        move_y = y - old_y
        line_len = math.sqrt(line_len_sq)
        dot = (move_x * dx + move_y * dy) / line_len
        return (dot > 0.4 or move_y < -0.4) and (move_y <= 0.4)

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

    def on_update(self,dt):
        if self.is_paused:return
        super().on_update(dt)
        previous_release = self.bone_release
        self.bone_release = max(0., previous_release-dt)
        release_threshold = BONE_RELEASE_TIME-BONE_STRETCH_TIME
        if previous_release > release_threshold >= self.bone_release:
            for vx, vy, life in ((-95, 55, .29), (-60, 90, .35), (-24, 72, .32),
                                 (24, 55, .28), (53, 38, .24), (-80, -22, .22)):
                self.particles.append([*BONE_SOCKET, vx, vy, life, 'meat_juice'])
        self.vibe_clock += dt
        if self.shake_t>0:
            self.shake_t=max(0.,self.shake_t-dt)
        if self.cut_vibe_t>0:
            self.cut_vibe_t=max(0.,self.cut_vibe_t-dt)
        if self.cut_anim>0:
            old=self.cut_anim
            self.cut_anim=max(0.,self.cut_anim-min(.05,dt))
            if self.cut_pending and old>.11>=self.cut_anim:
                action=self.cut_pending;self.cut_pending=None
                self.commit(action)
                self.trigger_shake(4.0,0.18)
        self.window.bbq_progress=self.meal.save()

    def peel_grip(self):
        return PEEL_GRIP[0] + self.meal.prep_peels * 21, PEEL_GRIP[1]

    def cut_guide(self):
        return CUT_PATHS[min(1,self.meal.prep_cuts)]

    def distance_to_cut(self,x,y):
        a,b=self.cut_guide();dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)

    def on_mouse_press(self,x,y,button,modifiers):
        if self.handle_pause_mouse_press(x,y,button):return
        if self.is_paused or button!=arcade.MOUSE_BUTTON_LEFT:return
        x,y=self.coords(x,y);self.mouse=self.start=(x,y);self.stroke=0.;self.cut_deviation=0.
        if self.cut_anim>0:return
        if self.hit(x,y,100,674,150,48):self.leave();return
        step=self.meal.prep_step
        if step==0 and self.hit(x,y,*KNIFE,140,260):
            self.sound('click', .32)
            self.knife_held=True;self.drag='knife_pickup'
            self.message('Drag to the bright start dot, then follow the arrow.');return
        if step==0 and self.hit(x,y,*BOARD,660,330):
            if self.knife_held:self.drag='cut'
            else:self.message('Pick up the flint knife on the right first.')
        elif step==1 and self.hit(x,y,805,345,220,190):self.drag='portion'
        elif step==2 and self.hit(x,y,*self.peel_grip(),100,130):self.drag='peel'
        elif step==3 and self.hit(x,y,*BONE_GRIP,110,100):self.drag='debone'
        elif step==4 and self.bone_release <= 0 and self.hit(x,y,*BOARD,MEAT_WIDTH,180):self.drag='skewer'
        elif step==5 and self.hit(x,y,680,340,720,230):self.drag='mount'

    def on_mouse_motion(self,x,y,dx,dy):
        if self.handle_pause_mouse_motion(x,y):return
        x,y=self.coords(x,y);old=self.mouse;self.mouse=(x,y)
        if self.knife_held and self.meal.prep_step==0 and not self.drag:
            if self.check_cutting_motion(x,y,old[0],old[1]):
                self.feed_cut_vibration()
            elif math.hypot(x-old[0],y-old[1])>2.0:
                self.cut_vibe_t=0.

    def on_mouse_drag(self,x,y,dx,dy,buttons,modifiers):
        if self.is_paused or self.cut_anim>0:return
        x,y=self.coords(x,y);old=self.mouse;self.mouse=(x,y)
        if self.drag in ('peel', 'debone', 'skewer') and math.dist(old, self.mouse) >= 4:
            if self.t-self.last_prep_drag_sound >= .20:
                self.last_prep_drag_sound = self.t
                cue = 'paper_slide' if self.drag == 'peel' else 'meat_slice'
                self.sound(cue, .27)
        step=self.meal.prep_step
        if self.drag=='knife_pickup':
            a,b=self.cut_guide()
            if math.dist((x,y),a)<45:
                self.drag='cut'
                self.start=(x,y);self.stroke=0.;self.cut_deviation=0.
            return
        if step==0 and self.knife_held and not self.drag and (buttons & arcade.MOUSE_BUTTON_LEFT):
            self.drag='cut';self.start=old;self.stroke=0.;self.cut_deviation=0.
        if self.check_cutting_motion(x,y,old[0],old[1]):
            self.feed_cut_vibration()
        elif math.hypot(x-old[0],y-old[1])>2.0:
            self.cut_vibe_t=0.
        if self.drag=='cut':
            self.stroke+=math.hypot(x-old[0],y-old[1])
            self.cut_deviation=max(self.cut_deviation,self.distance_to_cut(x,y))
            a,b=self.cut_guide()
            length=math.dist(a,b)
            if self.stroke>=length*.70 and math.dist((x,y),b)<45 and self.cut_deviation<55:
                self.cut_segment=(a,b)
                self.cut_cursor=b;self.cut_anim=.26;self.cut_pending=self.drag
                self.drag=None;self.cut_vibe_t=0.
                self.trigger_shake(1.5,0.10)

    def bone_pull(self, x, y):
        dx, dy = self.start[0]-x, self.start[1]-y
        along = dx*BONE_AXIS[0] + dy*BONE_AXIS[1]
        across = abs(dx*BONE_AXIS[1] - dy*BONE_AXIS[0])
        return along, across

    def draw_exposed_bone(self):
        pull = 0.
        if self.drag == 'debone':
            pull, _ = self.bone_pull(*self.mouse)
        exposed = BONE_EXPOSED + max(0., min(BONE_TRAVEL, pull))
        texture = self.bone_texture
        pixels = round(exposed * texture.width / BONE_WIDTH)
        # Reveal from the outer end. Keep the inner crop edge at the socket.
        if pixels not in self.bone_crops:
            self.bone_crops[pixels] = texture.crop(0, 0, pixels, texture.height)
        self.sprites['prep_bone'].texture = self.bone_crops[pixels]
        width = pixels * BONE_WIDTH / texture.width
        x = BONE_SOCKET[0] - BONE_AXIS[0] * width/2
        y = BONE_SOCKET[1] - BONE_AXIS[1] * width/2
        self.show('prep_bone', x, y, width, BONE_LEAN)
        for lip in self.bone_lip_layout:
            self.show(*lip)

    def on_mouse_release(self,x,y,button,modifiers):
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        if self.is_paused:self.stop_input();return
        x,y=self.coords(x,y);drag=self.drag;self.drag=None
        if not drag:return
        valid=False
        if drag=='knife_pickup':
            valid=self.hit(x,y,*BOARD,660,330)
            self.knife_held=valid
        elif drag=='cut':
            a,b=self.cut_guide()
            length=math.dist(a,b)
            forward=(math.dist(self.start,a)<50 and math.dist((x,y),b)<50)
            backward=(math.dist(self.start,b)<50 and math.dist((x,y),a)<50)
            if self.stroke>=length*.70 and (forward or backward) and self.cut_deviation<55:
                self.cut_segment=(a,b)
                self.cut_cursor=b;self.cut_anim=.26;self.cut_pending=drag;valid=True
                self.trigger_shake(1.5,0.10)
        elif drag=='portion' and self.hit(x,y,*TRAY,280,240):
            valid=self.commit('portion');self.knife_held=False
        elif drag=='peel' and x-self.start[0]>=PEEL_TRAVEL and abs(y-self.start[1])<100:
            valid=self.commit('peel')
        elif drag=='debone':
            along, across = self.bone_pull(x, y)
            if along >= BONE_TRAVEL and across < 55 and y < self.start[1]-35:
                valid=self.commit('debone')
        elif drag=='skewer' and x-self.start[0]>=160 and self.hit(x,y,*SKEWER_TARGET,220,120):
            valid=self.commit('skewer');self.knife_held=False
        elif drag=='mount' and self.hit(x,y,1110,290,260,300):valid=self.commit('mount')
        if not valid:self.message('Follow the highlighted direction, then release at the target.')
        self.window.bbq_progress=self.meal.save()

    def on_key_press(self,key,modifiers):
        if key==arcade.key.B and not self.is_paused:self.leave();return
        super().on_key_press(key,modifiers)

    def show_loaded_spit(self, x, y):
        self.show_mounted('mounted_raw_a')
        origin_x, origin_y = self.axis_point(RACK_CENTER[0])
        scale = .72
        for name in self.loaded_spit_layers():
            sprite = self.sprites[name]
            if sprite.visible:
                sprite.position = (x + (sprite.center_x-origin_x)*scale,
                                   y + (sprite.center_y-origin_y)*scale)
                sprite.scale = sprite.scale_x*scale

    def loaded_spit_layers(self):
        return ([name for name, _, _ in self.shaft_tiles]
                + self.rack_moving_names + self.rack_hardware_names)

    def on_draw(self):
        self.clear((31,34,24))
        ox,oy=0.,0.
        if self.shake_t>0:
            decay=self.shake_t/0.22
            ox+=math.sin(self.shake_t*68.0)*self.shake_amp*decay
            oy+=math.cos(self.shake_t*85.0)*self.shake_amp*0.75*decay
        if self.cut_vibe_t>0:
            vibe_strength=min(1.0,self.cut_vibe_t/0.05)
            ox+=math.sin(self.vibe_clock*95.0)*1.0*vibe_strength
            oy+=math.cos(self.vibe_clock*125.0)*0.7*vibe_strength
        if self.camera:
            self.camera.position=(640.+ox,360.+oy)
        self.use_game_camera()
        for sp in self.sprites.values():sp.visible=False
        step=self.meal.prep_step
        self.background('prep_ground')
        # Left corner has the stone cutting board:
        if step in (0,1):
            self.show('slab',*TRAY,320)
        elif step>=2:
            self.show('slab',*BOARD,650)

        if step in (0,1):
            self.show('prep_blood',720,315,420,alpha=165)
            self.show('prep_body_'+str(min(2,self.meal.prep_cuts)),*BOARD,760)
            if step==1:
                self.show('prep_thigh',*(self.mouse if self.drag=='portion' else (805,345)),160)
        elif step==2:
            self.show(self.peel_frames[self.meal.prep_peels], *BOARD, MEAT_WIDTH)
            pull = 0.
            if self.drag=='peel':
                pull=max(0.,min(PEEL_TRAVEL,self.mouse[0]-self.start[0]))
            grip_x,grip_y=self.peel_grip()
            tex=self.sprites['prep_peel_tool'].texture
            scale=320/tex.width
            self.show('prep_peel_tool',grip_x+pull+tex.width*.25*scale,
                      grip_y-tex.height*.20*scale,320)
        elif step==3:
            pull = self.bone_pull(*self.mouse)[0] if self.drag == 'debone' else 0.
            if pull >= BONE_STRAIN_START:
                strain = min(1., (pull-BONE_STRAIN_START)/(BONE_TRAVEL-BONE_STRAIN_START))
                x, y, width = BONE_STRETCH_POSE
                self.show('prep_socket_stretch',
                          x + math.sin(self.vibe_clock*86)*strain*2.8,
                          y + math.cos(self.vibe_clock*69)*strain*1.6, width)
            else:
                self.show('prep_deboned',*BOARD,MEAT_WIDTH)
                self.draw_exposed_bone()
        elif step==4:
            if self.bone_release <= 0:
                self.show('mounted_empty',1025,350,335)
            self.show('prep_deboned',*(self.mouse if self.drag=='skewer' else BOARD),MEAT_WIDTH)
            if self.bone_release > BONE_RELEASE_TIME-BONE_STRETCH_TIME:
                self.sprites['prep_deboned'].visible = False
                self.show('prep_socket_stretch', *BONE_STRETCH_POSE)
            elif self.bone_release > 0:
                # Once freed, render the complete joint beyond the socket.
                progress = 1-self.bone_release/(BONE_RELEASE_TIME-BONE_STRETCH_TIME)
                distance = BONE_WIDTH/2 + 12 + 54*progress
                x = BONE_SOCKET[0]-BONE_AXIS[0]*distance
                y = BONE_SOCKET[1]-BONE_AXIS[1]*distance
                self.sprites['prep_bone'].texture = self.bone_texture
                self.show('prep_bone', x, y, BONE_WIDTH, BONE_LEAN+14*progress,
                          alpha=round(255*min(1.,self.bone_release/.08)))
        elif step==5:
            self.show('prep_rack',1110,290,250)
            self.show_loaded_spit(*(self.mouse if self.drag=='mount' else (680,340)))
        if step==0:
            if self.knife_held or self.cut_anim>0:
                a,b=self.cut_segment if self.cut_anim>0 else self.cut_guide()
                progress=max(0.,min(1.,(1-self.cut_anim/.26)))
                # The diagonal pose and depth perspective are baked into this sprite.
                angle=0.
                if self.cut_anim>0:x,y=a[0]+(b[0]-a[0])*progress,a[1]+(b[1]-a[1])*progress
                else:
                    x,y=self.mouse
                    if self.cut_vibe_t>0:
                        vibe_strength=min(1.0,self.cut_vibe_t/0.05)
                        x+=math.sin(self.vibe_clock*145.0)*6.5*vibe_strength
                        y+=math.cos(self.vibe_clock*185.0)*5.0*vibe_strength
                        angle+=math.sin(self.vibe_clock*125.0)*6.0*vibe_strength
                tex=self.sprites['prep_knife'].texture
                width=260.
                scale=width/tex.width
                # Native tip (99%, 17%) is the gesture contact point. Rotate
                # vibration around that tip rather than around the sprite center.
                dx=(.5-.99)*tex.width*scale
                dy=(.17-.5)*tex.height*scale
                theta=math.radians(angle)
                cx=x+dx*math.cos(theta)+dy*math.sin(theta)
                cy=y-dx*math.sin(theta)+dy*math.cos(theta)
                self.show('prep_knife',cx,cy,width,angle)
            else:self.show('prep_knife_rest',*KNIFE,210,-90)
        self.order(['prep_ground','slab','plate','prep_blood']+['prep_body_'+str(i) for i in range(3)]+
                   ['prep_rack','mounted_empty','prep_thigh','raw',*self.peel_frames,'prep_deboned','prep_bone','prep_socket_stretch',*(lip[0] for lip in self.bone_lip_layout),*self.loaded_spit_layers(),'knife','prep_knife_rest','prep_knife','prep_peel_tool'])
        self.layers.draw()
        self.draw_particles();self.draw_prep_hud()
        if step==0:draw_knife_slot(self,KNIFE,'prep_knife_rest')
        self.draw_pause_overlay()
        if self.camera:
            self.camera.position=(640.,360.)

    def draw_prep_hud(self):
        step=self.meal.prep_step
        for x,width in ((100,150),(720,980)):
            arcade.draw_rect_filled(arcade.XYWH(x,674,width,48),(18,22,30,235))
        self.label('prep_back','< BACK TO VILLAGE',100,674,10,(200,220,240),'center')
        self.label('prep_instruction',('The bone comes free.' if self.bone_release > 0 else PREP_TEXT[min(step,len(PREP_TEXT)-1)]),250,674,12,width=500)
        self.step_meter(1110,674,'PREP',step,6)
        title='FIELD DRESSING' if step<2 else 'THE STONE CUTTING BOARD'
        self.label('prep_title',title,700,600,14,(245,224,182),'center')
        if step==0:
            a,b=self.cut_guide()
            if self.cut_vibe_t>0:
                arcade.draw_line(*a,*b,(255,160,60,160),9)
                arcade.draw_line(*a,*b,(255,245,210,255),5)
            else:
                arcade.draw_line(*a,*b,(255,220,145,235),3)
            arcade.draw_circle_filled(*a,5,(255,235,180,245))
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            ux,uy=dx/length,dy/length
            for sign in (-1,1):
                arcade.draw_line(*b,b[0]-ux*16+sign*uy*8,b[1]-uy*16-sign*ux*8,(255,220,145,235),3)
            if self.knife_held and self.cut_vibe_t>0:
                vibe_strength=min(1.0,self.cut_vibe_t/0.05)
                mx=self.mouse[0]+math.sin(self.vibe_clock*145.0)*6.5*vibe_strength
                my=self.mouse[1]+math.cos(self.vibe_clock*185.0)*5.0*vibe_strength
                r=14.0+3.5*math.sin(self.vibe_clock*110.0)
                arcade.draw_circle_outline(mx,my,r,(255,235,150,235),2.5)
                arcade.draw_circle_outline(mx,my,r+5.0,(255,150,70,150),1.5)
                arcade.draw_circle_filled(mx,my,4.0,(255,245,200,240))

        elif step==1:arcade.draw_ellipse_outline(*TRAY,280,220,(255,220,145,180),2)
        elif step==2:
            grip_x, grip_y = self.peel_grip()
            arcade.draw_line(grip_x,grip_y,grip_x+PEEL_TRAVEL,grip_y,(255,220,145,230),3)
            self.label('peel',f'PULL RIGHT  {self.meal.prep_peels}/{PEEL_PIECES}',
                       grip_x+PEEL_TRAVEL/2,470,12,anchor='center')
        elif step==3:
            x,y=BONE_GRIP
            arcade.draw_line(x,y,*BONE_END,(255,220,145,230),3)
            hint = 'PULL DOWN LEFT'
            if self.drag == 'debone':
                along, across = self.bone_pull(*self.mouse)
                if along >= BONE_TRAVEL and across < 55 and self.start[1]-self.mouse[1] > 35:
                    hint = 'RELEASE TO FREE THE BONE'
                elif along >= BONE_STRAIN_START:
                    hint = 'PULL A LITTLE FARTHER'
            self.label('debone',hint,(x+BONE_END[0])/2,y+35,12,anchor='center')
        elif step==4 and self.bone_release <= 0:
            arcade.draw_line(700,460,945,460,(255,220,145,230),3)
            self.label('skewer','SLIDE ONTO THE POINT  ->',830,490,12,anchor='center')
        elif step==5:arcade.draw_ellipse_outline(1110,290,260,280,(255,220,145,180),2)
        if self.notice_t>0:self.label('prep_notice',self.notice,700,65,12,(255,218,145),'center')
        self.label('prep_footer','B  Return to village     /     Esc  Pause',700,20,10,(215,208,189),'center')
