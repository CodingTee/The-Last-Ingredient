"""B05 kitchen sequence with live wide shots, a spill insert, and timed foley."""
from pathlib import Path
import math
import random
import arcade

W,H=1440,900
ASSETS=Path(__file__).resolve().parents[1]/'assets'/'Scene B05'


class B05Cinematic:
    # The spill-to-recall interval is deliberately short: the hero tries to
    # intervene immediately and is recalled before he can take the salt jar.
    SHOTS=[('take',3.2,0),('listen',1.1,1),('spill',.85,2),
           ('reach',.65,3),('recall',1.15,3),('empty',4.0,4)]
    CUES={
        'take':[(2.0,'step_stone',.33),(2.5,'step_stone',.4),(3.0,'step_stone',.45)],
        'listen':[(.13,'step_stone',.48),(.5,'step_stone',.52),(.78,'kit_bump',.75)],
        'spill':[(0,'pouch_tear',.48),(.12,'grain_fall',.48)],
        'reach':[(0,'recall_warning',.65)],
        'recall':[(0,'recall_whoosh',.8)],'empty':[]}

    def __init__(self,view):
        self.view=view
        self.spill_images={ratio: arcade.load_texture(ASSETS/f'03_spill_{ratio}.png')
                           for ratio in ('16x10','16x9')}
        self.sounds={name:arcade.load_sound(ASSETS/f'{name}.wav')
                     for name in ('step_stone','kit_bump','pouch_tear','grain_fall','recall_warning','recall_whoosh')}
        rng=random.Random(506)
        self.motes=[(rng.random()*math.tau,rng.uniform(40,150),rng.uniform(0,490),
                     rng.uniform(85,200),rng.uniform(1.4,3.5)) for _ in range(150)]
        self.players=[]
        self.restart()

    def restart(self):
        self.stop()
        self.index=0;self.age=0.;self.clock=0.;self.done=False
        self.fired=set();self.paused=False;self.events=[]

    @property
    def shot(self):return self.SHOTS[self.index][0]

    def stop(self):
        for player in self.players:
            try:arcade.stop_sound(player)
            except Exception:pass
        self.players=[]

    def set_paused(self,value):
        if value==self.paused:return
        self.paused=value
        for player in self.players:
            try:
                if value:player.pause()
                elif player.source is not None:player.play()
            except Exception:pass

    def _cues(self):
        for i,(at,name,volume) in enumerate(self.CUES[self.shot]):
            key=(self.index,i)
            if self.age>=at and key not in self.fired:
                self.fired.add(key)
                self.events.append((self.shot,name))
                self.players.append(self.sounds[name].play(volume=volume))

    def update(self,dt):
        if self.paused or self.done:return
        self.clock+=dt
        remaining=dt
        while remaining>1e-8 and not self.done:
            duration=self.SHOTS[self.index][1]
            step=min(remaining,duration-self.age)
            self.age+=step;remaining-=step
            self._cues()
            if self.age>=duration-1e-8:
                if self.index==len(self.SHOTS)-1:
                    self.done=True
                else:
                    self.index+=1;self.age=0.;self._cues()

    def _image(self,ratio,zoom=1.,dx=0,dy=0,alpha=255):
        tex=self.spill_images[ratio]
        arcade.draw_texture_rect(tex,arcade.XYWH(W/2+dx,H/2+dy,W*zoom,
                                  W*zoom*tex.height/tex.width),alpha=alpha)

    @staticmethod
    def point(u,v,zoom=1.,dx=0,dy=0):
        return W/2+(u-.5)*W*zoom+dx,H/2+(.5-v)*H*zoom+dy

    def _recall_layer(self,t,behind,*,anchor,scale):
        p=min(1,t/1.0)
        x,y=anchor
        intensity=math.sin(math.pi*min(1,t/1.15))
        for a,r,base,speed,size in self.motes:
            angle=a+t*.8
            if (math.sin(angle)>0)!=behind:continue
            height=(base+t*speed)%500
            sx=x+math.cos(angle)*r*scale
            sy=y+(math.sin(angle)*r*.21+height)*scale
            alpha=int(210*intensity)
            arcade.draw_circle_filled(sx,sy,size*3,(30,200,255,int(alpha*.1)))
            arcade.draw_circle_filled(sx,sy,size,(170,245,255,alpha))
        for i in range(3):
            level=50+i*155
            points=[]
            for n in range(33):
                angle=(0 if behind else math.pi)+n*math.pi/32
                points.append((x+math.cos(angle)*150*scale,y+(math.sin(angle)*30+level)*scale))
            arcade.draw_line_strip(points,(115,235,255,int(165*intensity)),2)
        # Dissolution edge sweeps from the head down to the floor.
        if not behind and p<1:
            level=490*(1-p)
            arcade.draw_line(x-115,y+level,x+165,y+level,(185,250,255,int(140*intensity)),2)

    def draw(self):
        ratio='16x9' if abs(self.view.window.width/self.view.window.height-16/9)<abs(self.view.window.width/self.view.window.height-1.6) else '16x10'
        name,duration,_=self.SHOTS[self.index]
        progress=min(1,self.age/duration)
        if name=='spill':
            shake=math.sin(self.age*70)*3*max(0,1-self.age/.2)
            self._image(ratio,1+.025*progress,dx=shake)
            x,y=self.point(.496,.46,1+.025*progress,shake)
            # Dry CX-SOLID grains fall by gravity; no wet stains or blue glow.
            for i in range(7):
                p=(self.age*2.4+i*.16)%1
                gx=x+math.sin(i*2.1)*3;gy=y-20*p
                arcade.draw_polygon_filled([(gx-1.2,gy),(gx,gy+1.6),
                    (gx+1.2,gy),(gx,gy-1.4)],(238,232,215,int(180*(1-p))))
        else:
            self.view.draw_cinematic_room(name,progress)
        caption=''
        if name=='take' and self.age<2.0:caption='Before it is served. I can still save her.'
        elif name=='listen':caption='Footsteps…'
        elif name=='reach':caption='Wait—!'
        elif name=='recall':caption='TEMPORAL WINDOW EXPIRED — RECALL'
        elif name=='empty' and self.age>1.5:caption='The kitchen is empty. The soup is still simmering.'
        if caption:
            arcade.draw_rect_filled(arcade.XYWH(W/2,109,1220,60),(11,15,19,210))
            self.view._label('film_caption',caption,W/2,109,17)
        if self.done:
            action = 'Continue' if self.view.story_mode else 'Replay animation'
            hint = f'ENTER {action}     R Replay scene     Esc Pause'
            self.view._label('film_replay',hint,W/2,66,12,(190,190,178,255))
