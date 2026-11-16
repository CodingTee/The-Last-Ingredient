"""Rendering-independent B03 dart rules; visible alpha is also the hit mask."""
from dataclasses import dataclass
import math
import random
from PIL import Image

WORLD_W, WORLD_H = 1584, 990


class AlphaMask:
    def __init__(self, image):
        self.alpha = image.convert('RGBA').getchannel('A')
        self.width, self.height = image.size

    def contains(self, x, y, cx, foot_y, width, height, flipped=False):
        u = (x-(cx-width/2))/width
        v = (y-foot_y)/height
        if not (0 <= u < 1 and 0 <= v < 1):
            return False
        ix = min(self.width-1, int(u*self.width))
        if flipped:
            ix = self.width-1-ix
        iy = min(self.height-1, int((1-v)*self.height))
        return self.alpha.getpixel((ix, iy)) >= 96


@dataclass
class Tree:
    kind: int
    x: float
    foot_y: float
    height: float
    width: float


def make_trees(sizes):
    rng = random.Random(310)
    trees = []
    # Foot positions determine depth. The middle row crosses the route;
    # upper-row trees sit behind it, lower trees provide foreground depth.
    rows = [(760, list(range(120, 1520, 125)), (195, 245)),
            (435, [250, 445, 635, 830, 1020, 1210, 1400], (210, 260)),
            (235, [100, 270, 470, 710, 930, 1180, 1410, 1550], (245, 310))]
    for foot, xs, heights in rows:
        for x in xs:
            kind = rng.randrange(len(sizes))
            tw, th = sizes[kind]
            height = rng.uniform(*heights)
            trees.append(Tree(kind, x+rng.uniform(-18,18),
                              foot+rng.uniform(-16,16), height, height*tw/th))
    # Dense broadleaf groves place real opaque crowns across the route.
    # Their irregular bases break up the sparse rows and force observation.
    for x,foot,height in ((365,185,490),(710,205,460),(1080,175,505)):
        tw,th=sizes[0]
        trees.append(Tree(0,x,foot,height,height*tw/th))
    return trees


class HuntModel:
    RELOAD = 1.5
    PATH = [(1280, 515), (1080, 540), (860, 515), (650, 560),
            (430, 510), (345, 605), (570, 655), (820, 630),
            (1040, 665), (1280, 610)]

    def __init__(self, dino_mask, tree_masks, trees):
        self.dino_mask, self.tree_masks, self.trees = dino_mask, tree_masks, trees
        self.width = 96.
        self.height = self.width*dino_mask.height/dino_mask.width
        self.x, self.y = self.PATH[0]
        self.segment, self.direction = 0, 1
        self.flipped = False
        self.elapsed = self.cooldown = self.hit_age = 0.
        self.steady_energy = 2.
        self.steadying = self.hit = False
        self.shots = 0
        self.last_result = None

    @property
    def bob(self):
        return 0 if self.hit else math.sin(self.elapsed*7)*.8

    def update(self, dt, steady=False):
        self.elapsed += dt
        self.cooldown = max(0., self.cooldown-dt)
        self.steadying = steady and self.steady_energy > .001 and not self.hit
        if self.steadying:
            self.steady_energy = max(0., self.steady_energy-dt)
        elif not steady:
            self.steady_energy = min(2., self.steady_energy+dt*.65)
        if self.hit:
            self.hit_age += dt
            return
        # Bounded speed modulation, deterministic route with no teleporting.
        remaining = dt*(43+8*math.sin(self.elapsed*.7))
        while remaining > 1e-8:
            target_index = self.segment+self.direction
            tx, ty = self.PATH[target_index]
            dx, dy = tx-self.x, ty-self.y
            distance = math.hypot(dx,dy)
            self.flipped = dx > 0
            if distance <= remaining:
                self.x, self.y = tx, ty
                remaining -= distance
                self.segment = target_index
                if self.segment in (0,len(self.PATH)-1):
                    self.direction *= -1
            else:
                self.x += dx/distance*remaining
                self.y += dy/distance*remaining
                remaining = 0

    def tree_blocks(self, x, y):
        # Every tree is bulletproof where drawn, including trees behind the
        # animal for a miss. Only foreground trees can obscure a target hit.
        return [tree for tree in self.trees if self.tree_masks[tree.kind].contains(
            x,y,tree.x,tree.foot_y,tree.width,tree.height)]

    def classify(self, x, y):
        on_animal = self.dino_mask.contains(x,y,self.x,self.y+self.bob,
                                           self.width,self.height,self.flipped)
        blocking = self.tree_blocks(x,y)
        if any(tree.foot_y <= self.y for tree in blocking):
            return 'tree'
        if on_animal:
            return 'hit'
        return 'tree' if blocking else 'miss'

    def fire(self, x, y):
        if self.hit:
            return 'finished'
        if self.cooldown > 1e-6:
            return 'reloading'
        self.shots += 1
        self.cooldown = self.RELOAD
        self.last_result = self.classify(x,y)
        if self.last_result == 'hit':
            self.hit = True
            self.hit_age = 0
        return self.last_result

