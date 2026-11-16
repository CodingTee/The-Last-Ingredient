"""Shared, registered pot / elliptical liquid / food / foreground-rim renderer."""
import json
import math
import arcade


class RoyalPotSurface:
    def __init__(self,v,assets,angle='close'):
        self.v=v
        self.texture=arcade.load_texture(assets/'pot_angles_v5'/f'{angle}.png')
        folder=assets/'pot_perspective_v4'
        self.geometry=json.loads((assets/'pot_angles_v5'/f'{angle}.json').read_text())
        self.grain=arcade.load_texture(folder/'barley_grain.png')
        self.front=[]
        g=self.geometry;w,h=self.texture.width,self.texture.height
        cx,cy,rx,ry=[g[k] for k in ('cx','cy','rx','ry')]
        # Foreground is sampled from the same original sprite along its curved lip.
        for left in range(0,w,8):
            right=min(w,left+8);u=((left+right)/2-cx)/rx
            top=round(cy+ry*math.sqrt(max(0,1-u*u))) if abs(u)<1 else 0
            top=max(0,min(h-1,top))
            self.front.append((left,top,right,h,self.texture.crop(left,top,right-left,h-top)))

    def mouth(self,px,py,width=440):
        t=self.texture;g=self.geometry;s=width/t.width
        return (px+(g['cx']-t.width/2)*s,py+(t.height/2-g['cy'])*s,g['rx']*s,g['ry']*s)

    def surface(self,water,px,py,width=440):
        mx,my,rx,ry=self.mouth(px,py,width)
        fraction=max(0,min(1,water/.85))
        radius=.70+.26*fraction
        return mx,my-ry*.60*(1-fraction),rx*radius,ry*radius

    def hit(self,x,y,px=1000,py=565):
        mx,my,rx,ry=self.mouth(px,py)
        return ((x-mx)/(rx*.98))**2+((y-my)/(ry*.98))**2<=1

    def draw(self,px,py,width=440,heating=False,water_override=None):
        v=self.v;c=v.cook;t=self.texture;s=width/t.width;k=width/440
        height=t.height*s
        arcade.draw_texture_rect(t,arcade.XYWH(px,py,width,height))
        water=c.water if water_override is None else water_override
        mx,my,rx,ry=self.surface(water,px,py,width)
        if water>0:
            soup=bool(c.ingredients)
            edge=(126,103,57) if soup else (48,77,85)
            middle=(176,151,91) if soup else (99,137,146)
            for ring in range(18):
                amount=ring/17
                color=tuple(round(a+(b-a)*amount) for a,b in zip(edge,middle))
                size=1-amount*.35
                arcade.draw_ellipse_filled(mx,my+amount*2*k,rx*2*size,ry*2*size,color)
            highlight=(220,207,157,90) if soup else (185,214,216,105)
            arcade.draw_arc_outline(mx,my,rx*1.90,ry*1.84,highlight,35,145,max(.6,1.2*k))
            arcade.draw_arc_outline(mx-rx*.18,my+ry*.06,rx*.60,ry*.38,(*middle,75),30,120,max(.5,.8*k))
            for i,name in enumerate(('onion','carrot')):
                if name not in c.ingredients:continue
                for j,texture in enumerate(v.food_pieces[name]):
                    a=i*2+j*2.399+(v.stir_phase if c.stage=='simmer' else 0)
                    radius=.35+.10*(j%4)
                    x=mx+math.sin(a)*rx*radius;y=my+math.cos(a)*ry*radius
                    arcade.draw_texture_rect(texture,arcade.XYWH(x,y,15*k,10*k),angle=j*37)
            if 'barley' in c.ingredients:
                # A reproducible loose distribution of individual grains, never a heap.
                for j in range(32):
                    a=j*2.39996+v.stir_phase*.85
                    radius=math.sqrt((j+.5)/32)*.82
                    x=mx+math.cos(a)*rx*radius;y=my+math.sin(a)*ry*radius
                    alpha=150 if j%5==0 else 235
                    arcade.draw_texture_rect(self.grain,arcade.XYWH(x,y,8*k,8*k*self.grain.height/self.grain.width),angle=(j*71)%180,color=arcade.types.Color(255,255,255,alpha))
            if heating and c.temperature>65:
                activity=max(0,min(1,(c.temperature-65)/31))
                for j in range(round(3+activity*13)):
                    a=j*2.4;phase=(v.clock*(.7+activity)+j*.173)%1
                    x=mx+math.sin(a)*rx*.70;y=my+math.cos(a)*ry*.65
                    arcade.draw_ellipse_outline(x,y,(3+phase*9)*k,(2+phase*4)*k,(219,227,208,round((1-phase)*165)),max(.6,k))
                for j in range(round(activity*10)):
                    phase=(v.clock*.35+j*.11)%1
                    arcade.draw_circle_filled(mx+math.sin(j*2+v.clock)*rx*.55,my+ry+phase*110*k,(5+phase*13)*k,(230,224,208,round((1-phase)*45)))
        # Restore the curved front wall / lip over the liquid and food layer.
        for l,top,r,b,texture in self.front:
            x=px+((l+r)/2-t.width/2)*s;y=py+(t.height/2-(top+b)/2)*s
            arcade.draw_texture_rect(texture,arcade.XYWH(x,y,(r-l)*s,(b-top)*s))
        return mx,my,rx,ry

    def draw_mark(self,px=443,py=565):
        v=self.v
        if v.cook.ingredients:return
        mx,my,rx,ry=self.mouth(px,py)
        color=(139,211,161) if v.cook.water_ready else (224,189,119)
        # A short mark on the left inner wall; nothing crosses the liquid surface.
        target=self.surface(.60,px,py)
        x=mx-rx*.87;y=target[1]
        arcade.draw_line(x,y,x+11,y,color,2)
