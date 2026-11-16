"""Registered Scene 6 silhouettes and independent light passes.
Image coordinates live in manifest.json; all sorting uses the same feet baseline.
"""
import json, math
import arcade
from arcade.types import Color
from core.player import FEET_OFFSET

KEYS=('window_left','window_right','floor_lamp','dining_lamp')
class PrecisionEnvironment:
    def __init__(self,view,folder):
        self.view=view; self.folder=folder
        self.items=json.loads((folder/'manifest.json').read_text())
        self.tex={};self.glow={};self.lights={};self.object_lights={};self.curtains={}
        for name in self.items:
            self.tex[name]=arcade.load_texture(folder/(name+'.png'))
            self.glow[name]=arcade.load_texture(folder/(name+'_outline.png'))
            self.object_lights[name]={k:arcade.load_texture(folder/(name+'_'+k+'_add.png')) for k in KEYS}
        for k in KEYS:self.lights[k]=arcade.load_texture(folder/(k+'_add.png'))
        for k in KEYS[:2]:self.curtains[k]=arcade.load_texture(folder/(k+'_curtain.png'))
        self.tex_chandelier=arcade.load_texture(folder/'chandelier.png')
        self.chand_lights={k:arcade.load_texture(folder/('chandelier_'+k+'_add.png')) for k in KEYS}
        # Feet footprints, not the whole visual rectangle.
        view.furniture_colliders=[tuple(c) for m in self.items.values() for c in m['colliders']]
        self.labels={'sofa':'Sit Down on Sofa','floor_lamp':'Toggle Floor Lamp','remote':'Use Dining Lamp Remote',
          'window_left':'Open / Close West Curtains','window_right':'Open / Close East Curtains',
          'fireplace':'Examine Hearth & Trophy','bookshelf':'Examine Books'}
    def feet(self):return self.view.player.x,self.view.player.y-FEET_OFFSET+8
    def active(self):
        v=self.view
        if v.is_sitting_on_sofa:return 'sofa'
        x,y=self.feet();near=[]
        for key in self.labels:
            ax,ay=self.items[key]['anchor'];distance=math.hypot(x-ax,y-ay)
            if distance < (110 if key in ('sofa','bookshelf','fireplace') else 100):near.append((distance,key))
        return min(near)[1] if near else None
    def rect(self,name):
        l,t,r,b=self.items[name]['box'];return arcade.XYWH((l+r)/2,937-(t+b)/2,r-l,b-t)
    def intensities(self):
        v=self.view
        return {'window_left':v.intensity_window_left,'window_right':v.intensity_window_right,
                'floor_lamp':v.intensity_floor_lamp,'dining_lamp':v.intensity_dining_lamp}
    def add(self,tex,rect,intensity):
        if intensity<=.005:return
        ctx=self.view.window.ctx;old=ctx.blend_func
        try:
            ctx.blend_func=(ctx.SRC_ALPHA,ctx.ONE)
            arcade.draw_texture_rect(tex,rect,color=Color(255,255,255,round(255*intensity)))
        finally:ctx.blend_func=old
    def draw_seated(self):
        v=self.view; x,y=v.sitting_pos
        # Contact is on the cushion, not a ground shadow under dangling boots.
        for width,height,alpha in [(63,14,10),(52,10,20),(41,7,32)]:
            arcade.draw_ellipse_filled(x,y-31,width,height,Color(12,15,17,alpha))
        height=178.0
        width=height*v.tex_char_sit.width/v.tex_char_sit.height
        # Same sprite geometry in every state; restrained ambient / lamp adaptation.
        cool=max(v.intensity_window_left,v.intensity_window_right)
        warm=v.intensity_floor_lamp
        tint=Color(min(255,round(198+48*warm+9*cool)),min(255,round(201+36*warm+13*cool)),min(255,round(213+22*warm+20*cool)))
        arcade.draw_texture_rect(v.tex_char_sit,arcade.XYWH(x,y,width,height),color=tint)
    def draw(self):
        v=self.view;levels=self.intensities();full=arcade.XYWH(839,468.5,1678,937)
        # Curtain geometry replacement first; independent illumination adds thereafter.
        for k,tex in self.curtains.items():
            if levels[k]>.005:arcade.draw_texture_rect(tex,full,color=Color(255,255,255,round(255*levels[k])))
        for k,tex in self.lights.items():self.add(tex,full,levels[k])
        x,root=self.feet();entities=[]
        key=None if v.dialogue.active else self.active()
        if v.is_sitting_on_sofa:
            entities.append((self.items['sofa']['root']-.1,self.draw_seated))
        else:entities.append((root,v.player.draw))
        for name,m in self.items.items():
            if name in ('remote','window_left','window_right'):continue
            l,t,r,b=m['box']
            # Repaint only where character can overlap, from the exact registered alpha.
            if not v.is_sitting_on_sofa and root>m['root'] and l-60<x<r+60 and root<937-t+170:
                def paint(n=name):
                    rect=self.rect(n);arcade.draw_texture_rect(self.tex[n],rect)
                    for k in KEYS:self.add(self.object_lights[n][k],rect,levels[k])
                entities.append((m['root'],paint))
        if not v.is_sitting_on_sofa and root>163 and 1200<x<1340 and root<520:
            def paint_chand():
                rect_chand=arcade.XYWH(1268.0,662,64,550)
                arcade.draw_texture_rect(self.tex_chandelier,rect_chand)
                for k in KEYS:self.add(self.chand_lights[k],rect_chand,levels[k])
            entities.append((163.1,paint_chand))
        if key and key!='remote':
            alpha=round(145+70*(.5+.5*math.sin(v.t*4)))
            entities.append((self.items[key]['root']-.01,lambda:arcade.draw_texture_rect(self.glow[key],self.rect(key),color=Color(255,255,255,alpha))))
        for _,draw in sorted(entities,key=lambda x:x[0],reverse=True):draw()
        if key=='remote':
            # Tabletop ring overlays the depth pass so the player cannot hide it.
            alpha=round(145+70*(.5+.5*math.sin(v.t*4)))
            arcade.draw_texture_rect(self.glow[key],self.rect(key),color=Color(255,255,255,alpha))
        if key:
            l,t,r,b=self.items[key]['box'];label='Stand Up from Sofa' if key=='sofa' and v.is_sitting_on_sofa else self.labels[key]
            prompt_y=max(937-t+20,v.sitting_pos[1]+115) if key=='sofa' and v.is_sitting_on_sofa else 937-t+20
            return ((l+r)/2,prompt_y,'[E] '+label, key in ('sofa','remote','floor_lamp','window_left','window_right'))
        if x>=1480 and 180<=root<=460:return (1530,420,'[E] Open Door & Enter Kitchen',True)
        return None
