"""B03 first-person forest encounter, using Arcade 3.x cameras and alpha masks."""
import math
from pathlib import Path

import arcade
from PIL import Image
from arcade.types.rect import LRBT
from core.base_view import BaseGameView
from core.constants import ASSETS_DIR, SOUNDS_DIR
from core.audio import AudioManager
from scenes.b03_atmosphere import distance_texture, forest_shade, shade_color
from scenes.b03_hunt_model import AlphaMask, HuntModel, make_trees, WORLD_W, WORLD_H


class B03HuntView(BaseGameView):
    def __init__(self, truth_understood=False, on_return=None):
        super().__init__()
        self.truth_understood = truth_understood
        self.on_return = on_return
        folder = ASSETS_DIR/'endings'/'bad_ending'/'b03_hunt'
        self.ground = arcade.load_texture(folder/'forest_floor_16x10.png')
        self.dino_tex = arcade.load_texture(folder/'dinosaur.png')
        self.dino_far = distance_texture(self.dino_tex)
        self.dino_near = distance_texture(self.dino_tex,scoped=True)
        self.dino_far_flip = self.dino_far.flip_left_right()
        self.dino_near_flip = self.dino_near.flip_left_right()
        self.tree_tex = [arcade.load_texture(ASSETS_DIR/'prehistoric'/'decor'/f'tree_{i}.png') for i in range(4)]
        masks = [AlphaMask(t.image) for t in self.tree_tex]
        self.model = HuntModel(AlphaMask(self.dino_tex.image), masks,
                               make_trees([(t.width,t.height) for t in self.tree_tex]))
        self.world_camera = self.ui_camera = None
        self.scoped = False
        self.magnification = 2
        self.aim_x,self.aim_y = 1140.,550.
        self.mouse_x=self.mouse_y=0
        self.shift=False
        self.message='Wait for a clear line through the trees.'
        self.message_age=4.
        self.shot_point=None
        self.shot_age=99.
        self.ambient=arcade.load_sound(SOUNDS_DIR/'b03_forest_air.wav')
        self.ambient_player=None
        self.text_cache={}

    def on_show_view(self):
        super().on_show_view()
        self.clean_texture_atlas()
        self.ambient_player=self.ambient.play(volume=.22,loop=True)
        self.window.set_mouse_visible(False)
        self.mouse_x,self.mouse_y=self.window.width/2,self.window.height/2

    def on_hide_view(self):
        self.shift=False
        self.window.set_exclusive_mouse(False)
        self.window.set_mouse_visible(True)
        if self.ambient_player:
            arcade.stop_sound(self.ambient_player)
            self.ambient_player=None

    def on_deactivate(self):
        self.shift=False
        self.window.set_exclusive_mouse(False)
        self.window.set_mouse_visible(True)

    def on_update(self,dt):
        if self.ambient_player:
            self.ambient_player.volume=0 if self.is_paused else .22
        if self.is_paused:
            return
        dt=min(dt,.05)
        self.model.update(dt,self.shift and self.scoped)
        self.message_age=max(0,self.message_age-dt)
        self.shot_age+=dt
        if self.model.hit and self.model.hit_age >= 1.8:
            self.window.show_view(B03AftermathView(self.truth_understood, self.on_return))

    def _layout(self):
        w,h=self.window.width,self.window.height
        scale=max(w/WORLD_W,h/WORLD_H)
        return w,h,scale

    def _camera(self):
        w,h,scale=self._layout()
        if self.world_camera is None:
            self.world_camera=arcade.camera.Camera2D(window=self.window)
            self.ui_camera=arcade.camera.Camera2D(window=self.window)
        zoom=self.magnification if self.scoped else 1
        effective=scale*zoom
        if self.scoped:
            margin=min(w,h)*.395/effective+5
            self.aim_x=max(margin,min(WORLD_W-margin,self.aim_x))
            self.aim_y=max(margin,min(WORLD_H-margin,self.aim_y))
        cx,cy=(self.aim_x,self.aim_y) if self.scoped else (WORLD_W/2,WORLD_H/2)
        self.world_camera.viewport=LRBT(0,w,0,h)
        self.world_camera.projection=LRBT(-w/(2*effective),w/(2*effective),-h/(2*effective),h/(2*effective))
        self.world_camera.position=(cx,cy)
        self.world_camera.use()
        return cx,cy,effective

    def _ui(self):
        w,h,_=self._layout()
        self.ui_camera.viewport=LRBT(0,w,0,h)
        self.ui_camera.projection=LRBT(-w/2,w/2,-h/2,h/2)
        self.ui_camera.position=(w/2,h/2)
        self.ui_camera.use()

    def _sway(self):
        m=self.model
        factor=.13 if m.steadying else 1.
        amplitude=2.6 if self.scoped else .7
        return (math.sin(m.elapsed*1.7)*amplitude*factor,
                math.cos(m.elapsed*1.3)*amplitude*.65*factor)

    def actual_aim(self):
        dx,dy=self._sway()
        return self.aim_x+dx,self.aim_y+dy

    def _label(self,key,text,x,y,size=14,color=(225,236,220,255),anchor='left'):
        signature=(text,size,color,anchor)
        if key not in self.text_cache or self.text_cache[key][0] != signature:
            self.text_cache[key]=(signature,arcade.Text(text,x,y,color,size,
                anchor_x=anchor,anchor_y='center',font_name='Arial'))
        obj=self.text_cache[key][1];obj.x=x;obj.y=y;obj.draw()

    def on_draw(self):
        self.clear((15,27,20))
        w,h,scale=self._layout()
        cx,cy,effective=self._camera()
        arcade.draw_texture_rect(self.ground,arcade.XYWH(WORLD_W/2,WORLD_H/2,WORLD_W,WORLD_H))
        # Painter order and hit-test depth use exactly the same foot positions.
        objects=[(tree.foot_y,'tree',tree) for tree in self.model.trees]
        objects.append((self.model.y,'dino',None))
        for _,kind,tree in sorted(objects,key=lambda entry:entry[0],reverse=True):
            if kind=='tree':
                arcade.draw_texture_rect(self.tree_tex[tree.kind],arcade.XYWH(
                    tree.x,tree.foot_y+tree.height/2,tree.width,tree.height))
            else:
                m=self.model
                if self.scoped:
                    tex=self.dino_near_flip if m.flipped else self.dino_near
                else:
                    tex=self.dino_far_flip if m.flipped else self.dino_far
                light=shade_color(forest_shade(m.x,m.y,self.model.trees))
                if m.hit:
                    collapse=min(1,m.hit_age/.45)
                    arcade.draw_texture_rect(tex,arcade.XYWH(m.x,m.y+m.height/2,
                        m.width,m.height),angle=-65*collapse,color=light)
                else:
                    arcade.draw_texture_rect(tex,arcade.XYWH(m.x,m.y+m.bob+m.height/2,m.width,m.height),color=light)
        if self.shot_point and self.shot_age<.2:
            px,py=self.shot_point
            a=int(220*(1-self.shot_age/.2))
            arcade.draw_line(px+9,py-5,px,py,(220,235,226,a),1.5)
            if self.model.last_result=='tree':
                for i in range(5):
                    angle=i*math.tau/5
                    arcade.draw_circle_filled(px+math.cos(angle)*self.shot_age*40,
                        py+math.sin(angle)*self.shot_age*40,1.6,(170,135,73,a))
        self._ui()
        ax,ay=self.actual_aim()
        rx,ry=w/2+(ax-cx)*effective,h/2+(ay-cy)*effective
        if self.scoped:
            # The lens uses the same world draw, no duplicate target or fake zoom.
            radius=min(w,h)*.395
            outer=max(w,h)*2
            for i in range(80):
                a=i*math.tau/80;b=(i+1)*math.tau/80
                arcade.draw_polygon_filled([(w/2+math.cos(a)*radius,h/2+math.sin(a)*radius),
                    (w/2+math.cos(b)*radius,h/2+math.sin(b)*radius),
                    (w/2+math.cos(b)*outer,h/2+math.sin(b)*outer),
                    (w/2+math.cos(a)*outer,h/2+math.sin(a)*outer)],(3,10,8,249))
            arcade.draw_circle_outline(w/2,h/2,radius,(69,93,79),3)
            arcade.draw_circle_outline(w/2,h/2,radius-5,(160,179,154,100),1)
            self._label('zoom',f'{self.magnification}x',w/2+radius*.58,h/2-radius*.65,12)
        reticle=(200,224,195,235)
        for dx,dy,ex,ey in [(-25,0,-7,0),(7,0,25,0),(0,-25,0,-7),(0,7,0,25)]:
            arcade.draw_line(rx+dx,ry+dy,rx+ex,ry+ey,reticle,1)
        arcade.draw_circle_filled(rx,ry,1.5,reticle)
        arcade.draw_rect_filled(arcade.XYWH(w/2,h-28,w,56),(6,17,13,205))
        self._label('title','B03 / THE WRONG TARGET',26,h-27,12,(172,197,165,255))
        status='RELOADING' if self.model.cooldown>0 else 'DART READY'
        self._label('ready',status,w-26,h-27,12,anchor='right')
        arcade.draw_rect_filled(arcade.XYWH(w/2,32,w,64),(6,17,13,220))
        self._label('controls','RMB Scope   |   LMB Fire   |   Wheel 2x / 4x   |   Hold Shift Steady   |   Esc Pause',w/2,26,12,anchor='center')
        if self.scoped:
            barw=110
            arcade.draw_rect_filled(arcade.XYWH(w-90,h-64,barw,4),(43,59,47))
            available=self.model.steady_energy/2
            arcade.draw_rect_filled(arcade.XYWH(w-145+barw*available/2,h-64,barw*available,4),(159,191,156))
        if self.message_age>0 and not self.model.hit:
            self._label('message',self.message,w/2,86,14,anchor='center')
        if self.model.hit:
            self._label('hit','The shape falls. You hurry down the slope.',w/2,100,17,anchor='center')
            alpha=int(255*max(0,min(1,(self.model.hit_age-.8)/1.)))
            arcade.draw_rect_filled(arcade.XYWH(w/2,h/2,w,h),(5,12,9,alpha))
        self.draw_pause_overlay()

    def on_mouse_motion(self,x,y,dx,dy):
        self.mouse_x,self.mouse_y=x,y
        if self.is_paused or self.model.hit:
            return
        w,h,scale=self._layout()
        if self.scoped:
            self.aim_x+=dx/(scale*self.magnification)
            self.aim_y+=dy/(scale*self.magnification)
        else:
            self.aim_x=WORLD_W/2+(x-w/2)/scale
            self.aim_y=WORLD_H/2+(y-h/2)/scale
        self.aim_x=max(120,min(WORLD_W-120,self.aim_x))
        self.aim_y=max(150,min(WORLD_H-150,self.aim_y))

    def on_mouse_drag(self,x,y,dx,dy,buttons,modifiers):
        self.on_mouse_motion(x,y,dx,dy)

    def on_mouse_scroll(self,x,y,scroll_x,scroll_y):
        if not self.is_paused and scroll_y:
            self.magnification=4 if scroll_y>0 else 2

    def on_mouse_press(self,x,y,button,modifiers):
        if self.is_paused:
            self.handle_pause_mouse_press(x,y,button)
            if self.window and self.window.current_view is self:
                self.window.set_mouse_visible(self.is_paused)
                self.window.set_exclusive_mouse(self.scoped and not self.is_paused)
            return
        if self.model.hit:
            return
        if button==arcade.MOUSE_BUTTON_RIGHT:
            self.scoped=not self.scoped
            self.window.set_exclusive_mouse(self.scoped)
            if not self.scoped:
                w,h,scale=self._layout()
                self.window.set_mouse_position(int(w/2+(self.aim_x-WORLD_W/2)*scale),
                                               int(h/2+(self.aim_y-WORLD_H/2)*scale))
            self.shift=False
            AudioManager().play('click',volume_scale=.25)
        elif button==arcade.MOUSE_BUTTON_LEFT:
            point=self.actual_aim()
            result=self.model.fire(*point)
            if result=='reloading':
                self.message='Reloading. Wait for a clear opening.';self.message_age=1.
                return
            self.shot_point=point;self.shot_age=0
            AudioManager().play('b03_dart_fire',volume_scale=.65)
            if result=='tree':
                AudioManager().play('b03_dart_wood',volume_scale=.6)
                self.message='Branches block the dart. Wait for an opening.'
            elif result=='miss':
                self.message='The dart misses. Follow the moving shape.'
            else:
                self.message=''
            self.message_age=2.4

    def on_key_press(self,key,modifiers):
        if key==arcade.key.F11:
            self.toggle_fullscreen();return
        if self.handle_pause_key(key):
            self.shift=False
            if self.window and self.window.current_view is self:
                self.window.set_exclusive_mouse(self.scoped and not self.is_paused)
                self.window.set_mouse_visible(self.is_paused)
            return
        if not self.is_paused and key in (arcade.key.LSHIFT,arcade.key.RSHIFT):
            self.shift=True

    def on_key_release(self,key,modifiers):
        if key in (arcade.key.LSHIFT,arcade.key.RSHIFT):
            self.shift=False


class B03AftermathView(BaseGameView):
    """A quiet reveal after the successful interaction, then return to B04."""
    LINES=[('You run down the slope. Your footsteps slow as you approach.',
            'The shape is smaller than you thought.'),
           ('No… It is the juvenile.',
            'A triangular metal dart barely protrudes from its neck. Blue payload has entered its body.'),
           ('The wound. The same triangular wound.',
            'I was trying to stop it… I did this.')]

    def __init__(self,truth_understood=False, on_return=None):
        super().__init__();self.truth_understood=truth_understood
        self.on_return = on_return
        self.image=arcade.load_texture(ASSETS_DIR/'Scene 9'/'Juvenile Dino Hurt.png')
        self.juvenile=arcade.load_texture(ASSETS_DIR/'Scene 9'/'Juvenile Dino.png')
        self.floor=arcade.load_texture(ASSETS_DIR/'endings'/'bad_ending'/'b03_hunt'/'forest_floor_16x10.png')
        self.index=0;self.age=0.;self.camera_native=None
        self.labels={}

    def on_show_view(self):
        super().on_show_view()
        self.clean_texture_atlas()
        self.window.set_mouse_visible(True)

    def on_update(self,dt):
        if not self.is_paused:self.age+=min(.1,dt)

    def advance(self):
        if self.age<.7:return
        if self.index<2:self.index+=1;self.age=0
        else:
            if self.on_return:
                self.on_return()
            else:
                from scenes.future_integrated_view import FutureLabView
                from scenes.future_nutrient_view import TransitDepartureView

                laboratory = FutureLabView()
                laboratory._close_notice()
                laboratory.transit_committed = True
                laboratory.nutrient_consumed = True
                laboratory.truth_understood = self.truth_understood
                laboratory.departure_view = TransitDepartureView(laboratory, next_destination=1)
                self.window.show_view(laboratory.departure_view)

    def on_draw(self):
        self.clear((7,16,12));w,h=self.window.width,self.window.height
        if self.camera_native is None:self.camera_native=arcade.camera.Camera2D(window=self.window)
        self.camera_native.viewport=LRBT(0,w,0,h)
        self.camera_native.projection=LRBT(-w/2,w/2,-h/2,h/2)
        self.camera_native.position=(w/2,h/2);self.camera_native.use()
        if self.index < 2:
            scale=max(w/self.floor.width,h/self.floor.height)
            arcade.draw_texture_rect(self.floor,arcade.XYWH(w/2,h/2,self.floor.width*scale,self.floor.height*scale))
            jw=w*.64
            arcade.draw_texture_rect(self.juvenile,arcade.XYWH(w/2,h*.56,jw,jw*self.juvenile.height/self.juvenile.width))
        else:
            scale=max(w/self.image.width,h/self.image.height)
            arcade.draw_texture_rect(self.image,arcade.XYWH(w/2,h/2,self.image.width*scale,self.image.height*scale))
        arcade.draw_rect_filled(arcade.XYWH(w/2,h*.14,w,h*.28),(5,13,11,235))
        lines=self.LINES[self.index]
        for i,line in enumerate(lines):
            key=(self.index,i,w,h)
            if key not in self.labels:
                self.labels[key]=arcade.Text(line,w/2,h*(.195-i*.055),(234,238,224),
                    max(13,int(h*.022)),anchor_x='center',anchor_y='center',width=w*.86,
                    multiline=True,align='center')
            self.labels[key].draw()
        arcade.draw_text('ENTER / CLICK TO CONTINUE',w/2,h*.045,(160,186,166),11,anchor_x='center')
        fade=int(255*max(0,1-self.age/.65))
        if fade:arcade.draw_rect_filled(arcade.XYWH(w/2,h/2,w,h),(4,10,7,fade))
        self.draw_pause_overlay()

    def on_key_press(self,key,modifiers):
        if key==arcade.key.F11:self.toggle_fullscreen();return
        if self.handle_pause_key(key):return
        if not self.is_paused and key in (arcade.key.ENTER,arcade.key.SPACE):self.advance()

    def on_mouse_press(self,x,y,button,modifiers):
        if self.is_paused:self.handle_pause_mouse_press(x,y,button)
        elif button==arcade.MOUSE_BUTTON_LEFT:self.advance()
