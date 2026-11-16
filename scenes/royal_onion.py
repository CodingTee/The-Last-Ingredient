"""Every cut reuses the same source pixels; only crop boundaries change."""
import random
import math
import arcade


class OnionSlices:
    def __init__(self, texture):
        self.texture = texture
        self.tiles = {}
        rng = random.Random(1910)
        self.pile = []
        for row in range(10):
            for col in range(10):
                # Small sprite pieces keep the exact original onion color/texture.
                l, t = 350+col*28, 50+row*30
                radius = math.sqrt(rng.random())
                theta = rng.random()*math.tau
                x = math.cos(theta)*radius*132
                y = math.sin(theta)*radius*65
                self.pile.append((l,t,x,y,rng.uniform(-85,85)))
        self.pile.sort(key=lambda piece: -piece[3])

    def tile(self, left, top, right, bottom):
        key = left, top, right, bottom
        if key not in self.tiles:
            self.tiles[key] = self.texture.crop(left, top, right-left, bottom-top)
        return self.tiles[key]

    def draw(self, count, angle=0, center=(740,400), scale=.55, pile_progress=1, stroke=None, corner_t=None):
        if count >= 10:
            self.draw_pile(center, scale, pile_progress)
            self.draw_discards(count, center=center, scale=scale, stroke=stroke, corner_t=corner_t)
            return
        # Original source canvas: 1000x420, bulb centered at (500,210).
        # One source, one scale, one lighting setup for all eleven states.
        xs = [0, 1000]
        if count >= 1: xs = [0, 630]
        if count >= 2: xs = [350, 630]
        if count >= 3: xs = [350] + [350+i*56 for i in range(1,min(count-2,4)+1)] + [630]
        ys = sorted([0,420]+[130+i*60 for i in range(max(0,count-6))])
        radians = math.radians(angle)
        cosine, sine = math.cos(radians), math.sin(radians)

        def piece(l,t,r,b,dx=0):
            texture = self.tile(round(l),round(t),round(r),round(b))
            x = ((l+r)/2-500)*scale + dx
            y = (210-(t+b)/2)*scale
            arcade.draw_texture_rect(texture,arcade.XYWH(center[0]+x*cosine-y*sine,center[1]+x*sine+y*cosine,(r-l)*scale,(b-t)*scale),angle=-angle)

        half_gap = .9 / scale
        for xi,(left,right) in enumerate(zip(xs,xs[1:])):
            for yi,(top,bottom) in enumerate(zip(ys,ys[1:])):
                # Remove a narrow strip at existing cuts, exposing the board.
                l=left+(half_gap if xi else 0);r=right-(half_gap if xi<len(xs)-2 else 0)
                t=top+(half_gap if yi else 0);b=bottom-(half_gap if yi<len(ys)-2 else 0)
                piece(l,t,r,b)
        self.draw_discards(count, center=center, scale=scale, stroke=stroke, corner_t=corner_t)

    def draw_pile(self, center, scale, progress=1):
        p=max(0,min(1,progress))
        ease=p*p*(3-2*p)
        for l,t,tx,ty,rotation in self.pile:
            # Start at the rotated onion's original coordinates, then gather.
            sx=(t+15-210);sy=(l+14-500)
            x=(sx+(tx-sx)*ease)*scale
            y=(sy+(ty-sy)*ease)*scale
            hop=math.sin(p*math.pi)*7
            texture=self.tile(l,t,l+27,t+29)
            arcade.draw_texture_rect(texture,arcade.XYWH(center[0]+x,center[1]+y+hop,27*scale,29*scale),angle=-90+rotation*ease)

    def draw_discards(self, count, center=(740, 400), scale=.55, stroke=None, corner_t=None):
        if count < 1:
            return
        # Tight opaque bounding crops for root tip and stem tip so they align accurately
        # Root tip: (632, 170, 670, 230), width 38, height 60, center (651, 200)
        # Stem tip: (330, 145, 350, 260), width 20, height 115, center (340, 202.5)
        dest1 = (1055, 452)  # Top-right on cutting board surface
        dest2 = (1025, 455)  # Top-right on cutting board surface
        base1 = (center[0] + (651 - 500) * scale, center[1] + (210 - 200) * scale)
        base2 = (center[0] + (340 - 500) * scale, center[1] + (210 - 202.5) * scale)
        orig1 = (base1[0] + 16, base1[1])
        orig2 = (base2[0] - 16, base2[1])

        tex1 = self.tile(632, 170, 670, 230)
        w1, h1 = 38 * scale, 60 * scale
        if count == 1:
            sep = min(1.0, max(0.0, (stroke.get('time', 0.4) - 0.16) / 0.14)) if stroke is not None else 1.0
            s_ease = sep * sep * (3 - 2 * sep)
            arcade.draw_texture_rect(tex1, arcade.XYWH(base1[0] + 16 * s_ease, base1[1], w1, h1))
            return

        tex2 = self.tile(330, 145, 350, 260)
        w2, h2 = 20 * scale, 115 * scale

        # Once the head-finishing cut begins, glide both tips to the top-right corner
        # and keep them there. corner_t is a one-shot clock captured at that cut's
        # start, so the motion runs continuously through the wind-up (no sitting on
        # the body) and later cuts can never re-trigger it.
        if corner_t is not None:
            t = min(1.0, max(0.0, corner_t / 0.22))
            ease = t * t * (3 - 2 * t)
            p1_x = orig1[0] + (dest1[0] - orig1[0]) * ease
            p1_y = orig1[1] + (dest1[1] - orig1[1]) * ease
            p2_x = orig2[0] + (dest2[0] - orig2[0]) * ease
            p2_y = orig2[1] + (dest2[1] - orig2[1]) * ease
            arcade.draw_texture_rect(tex1, arcade.XYWH(p1_x, p1_y, w1, h1), angle=15 * ease)
            arcade.draw_texture_rect(tex2, arcade.XYWH(p2_x, p2_y, w2, h2), angle=-12 * ease)
            return

        if count == 2:
            # Pre-trigger resting state: both tips sit on the board after the head is cut.
            arcade.draw_texture_rect(tex1, arcade.XYWH(orig1[0], orig1[1], w1, h1))
            sep = min(1.0, max(0.0, (stroke.get('time', 0.4) - 0.16) / 0.14)) if stroke is not None else 1.0
            s_ease = sep * sep * (3 - 2 * sep)
            arcade.draw_texture_rect(tex2, arcade.XYWH(base2[0] - 16 * s_ease, base2[1], w2, h2))
            return

        # count >= 3 without a corner trigger (e.g. shown while prepping the other
        # vegetable): already set aside at the corner.
        arcade.draw_texture_rect(tex1, arcade.XYWH(dest1[0], dest1[1], w1, h1), angle=15)
        arcade.draw_texture_rect(tex2, arcade.XYWH(dest2[0], dest2[1], w2, h2), angle=-12)
