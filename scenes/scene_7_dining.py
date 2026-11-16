"""Kitchen dining furniture, foot-based collision/depth and post-meal story state."""
import arcade
from arcade.types import Color
from core.constants import SCENE_7_DIR


class KitchenDining:
    center = (900, 270)
    root = 180
    # Foot-contact footprints, rather than the full tall furniture silhouette.
    obstacles = [(775,1025,190,285), (860,940,305,360), (855,945,105,170)]

    def __init__(self, view):
        self.v=view
        self.ready=False
        self.eating=False
        self.eaten=False
        self.table=arcade.load_texture(SCENE_7_DIR/'sprites/kitchen_table.png')
        self.seated=arcade.load_texture(SCENE_7_DIR/'sprites/chef_seated.png')
        self.scale=min(360/self.table.width,330/self.table.height)
        # Crop is a runtime sprite layer, retaining the generated alpha and registration.
        self.front_cut=round(self.table.height*.30)
        self.front=self.table.crop(0,self.front_cut,self.table.width,self.table.height-self.front_cut)

    def update(self):
        if self.eating and not self.v.dialogue.active:
            self.eating=False;self.eaten=True;self.ready=False
            self.v.player.place(680,300)
            self.v.dialogue.start_dialogue([
                ('The Empty Seat','He finishes the noodles and sets down his chopsticks. The opposite chair remains empty.',(220,200,170)),
                ('Chef','"I should head back to the living room." [Approach the left doorway and press E.]',(230,210,175),self.v.portrait_chef),
            ])

    def interact(self):
        v=self.v
        if self.eaten:
            v.dialogue.start_dialogue([('Kitchen Table','The meal is finished. The living room is through the left doorway.',(220,200,170))]);return
        if not self.ready:
            v.dialogue.start_dialogue([('Kitchen Table','Two chairs. One simple meal to make. The place opposite will remain empty tonight.',(220,200,170))]);return
        self.eating=True
        v.key_left=v.key_right=v.key_up=v.key_down=False
        v.dialogue.start_dialogue([
            ('The Kitchen Table','He sets the hot bowl down and takes his seat. The chair opposite is empty.',(220,200,170)),
            ('Chef','"Tomorrow... what am I supposed to do tomorrow?"',(230,210,175),v.portrait_thinking),
            ('A Familiar Voice','Steam rises. The words from childhood return: "Eat first. We will work out tomorrow when it comes."',(235,215,180)),
            ('Chef','"And if there is still no answer tomorrow?" No one replies. He lifts his chopsticks and begins to eat.',(230,210,175),v.portrait_chef),
        ])

    def _table(self, foreground=False, glow=False):
        texture=self.front if foreground else self.table
        q=self.scale*(1.035 if glow else 1)
        x,y=self.center
        if foreground:y-=self.front_cut*self.scale/2
        tint=Color(255,217,130,145) if glow else Color(222,208,187,255)
        arcade.draw_texture_rect(texture,arcade.XYWH(x,y,texture.width*q,texture.height*q),color=tint)

    def _meal(self):
        v=self.v
        if self.eating:
            v.sprite_renderer.sprite('bowl_soup',900,324,52,40)
            v.sprite_renderer.sprite('chopsticks',950,325,42,35)
            for j in range(3):
                import math
                y=343+(v.t*14+j*10)%36
                arcade.draw_circle_filled(900+math.sin(v.t+j)*4,y,3,(235,231,220,38))
        elif self.eaten:
            v.sprite_renderer.sprite('bowl_empty',900,324,48,35)

    def draw(self, highlight=False):
        v=self.v
        if highlight:self._table(glow=True)
        # Front objects occlude feet according to the same roots used for collision.
        behind=v.player.y-v.player.feet_offset+8>self.root
        if self.eating:
            self._table()
            t=self.seated;q=150/t.height
            arcade.draw_texture_rect(t,arcade.XYWH(900,385,t.width*q,t.height*q),color=Color(225,211,192,255))
            self._table(foreground=True)
            self._meal()
        elif behind:
            v.player.draw();self._table();self._meal()
        else:
            self._table();self._meal();v.player.draw()
