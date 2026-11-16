"""Scene 7: sprite picking, explicit cooking states and animated tool transfers."""

import math

import arcade

from arcade.types import Color





class CookingInteraction:

    def __init__(self, renderer):

        self.r = renderer

        self.v = renderer.view

        self.selected = None

        self.loaded = None

        self.pointer = (640, 360)

        self.regions = []

        self.message = 'Turn the right brass valve to fill the pot. Right-click returns a held item.'

        self.pot_placed = False

        self.right_on = False

        self.pan_heat = 0.0

        self.stirred = False

        self.shell_disposed = False
        self.eggs_remaining = 2
        self.egg_held = False

        self.broth = self.noodles = self.egg = False

        self.prep = False

        self.motion = None



    def record(self, name, x, y, w, h, key=None):

        self.regions.append((key or name, name, x, y, w, h))



    def hit(self, x, y):

        """Reverse draw-order picking; transparent pixels never become targets."""

        for key, name, cx, cy, w, h in reversed(self.regions):

            t = self.r.tex[name]

            scale = min(w / t.width, h / t.height)

            fx = (x - cx) / scale + t.width / 2

            fy = t.height / 2 - (y - cy) / scale

            if 0 <= fx < t.width and 0 <= fy < t.height:

                if t.image.getpixel((int(fx), int(fy)))[3] > 30:

                    return key

        return None



    def say(self, text):

        self.message = text



    def clear_hand(self):

        cracking = self.motion is not None and self.motion['name'] == 'egg_whole'
        if self.egg_held and not cracking:
            self.eggs_remaining += 1
            self.egg_held = False
        self.selected = self.loaded = None



    def cancel(self):

        # Let an already committed short animation finish before returning to map.

        self.clear_hand()

        self.v.is_filling_water = False



    def animate(self, name, target, finish, payload=None, origin=None):

        if origin is None:

            origin = next(((x, y) for key, n, x, y, w, h in self.regions

                           if key == name), self.pointer)

        self.motion = dict(name=name, origin=origin, target=target, elapsed=0.0,

                           finish=finish, payload=payload)

        self.clear_hand()

        self.v.audio.play('click')

        self.say('Using '+name.replace('_',' ')+'.')



    def update(self, dt):

        if self.motion:

            m = self.motion

            m['elapsed'] += dt

            if m['elapsed'] >= .75:

                self.motion = None

                m['finish']()

        if self.right_on:

            self.pan_heat = min(1.0, self.pan_heat + dt * .5)

        else:

            self.pan_heat = max(0.0, self.pan_heat - dt * .2)



    def hint(self):

        v = self.v

        if v.cook_step == 0: return 'Click the right brass valve to turn it. Click again to stop the water.'

        if not self.pot_placed: return 'Pick up the filled pot; click the outlined left burner.'

        if not v.stove_ignited and not self.prep: return 'Turn on the LEFT brass knob to heat the noodle pot.'

        if v.cook_step == 1: return 'Wait for the water to boil. The RIGHT knob controls the skillet.'

        if v.cook_step == 2: return 'Pick up dry noodles; use them on the boiling pot.'

        if v.cook_step == 3:

            if not self.right_on: return 'Turn on the RIGHT knob to heat the skillet.'

            if not v.oil_poured: return 'Pick up the oil bottle and click inside the skillet.'

            if self.pan_heat < .6: return 'Let the skillet warm up before adding the egg.'

            return 'Pick up an egg from the carton and use it on the skillet.'

        if v.cook_step == 4: return 'Pick up the half-shell; use it on the stray shell fragment.'

        if not self.shell_disposed: return 'The shell is being placed on the saucer.'

        if v.noodle_cook_progress < 1 or v.egg_cooked_progress < 1:

            return 'Let both foods finish cooking.'

        if not self.prep: return 'Turn BOTH burners off, then click the bowl to move to the serving counter.'

        if self.broth and self.noodles and self.egg: return 'Your soup is ready. Click the bowl to carry it to the dining room.'

        return 'Ladle > pot > bowl: broth. Chopsticks > pot > bowl: noodles. Spatula > skillet > bowl: egg.'



    def click(self, x, y, button):

        self.pointer = (x, y)

        if self.motion:

            self.say('Finish the current movement first.'); return None

        if button == arcade.MOUSE_BUTTON_RIGHT:

            self.clear_hand(); self.say(self.hint()); return None

        if button != arcade.MOUSE_BUTTON_LEFT: return None

        if 70 < x < 245 and 595 < y < 635:

            self.cancel()

            self.v.mode = 0

            self.v.key_left = self.v.key_right = self.v.key_up = self.v.key_down = False

            self.say('Cooking progress saved. Approach the sink, prep counter or stove to resume.')

            return None

        v = self.v

        name = self.hit(x, y)

        target = {'water_surface': 'pot_empty', 'broth_surface':'pot_empty', 'noodles_cooked': 'pot_empty',

                  'egg_raw': 'pan_empty', 'egg_fried': 'pan_empty',

                  'bowl_broth': 'bowl_empty', 'bowl_noodles': 'bowl_empty',

                  'bowl_egg': 'bowl_empty', 'bowl_soup': 'bowl_empty'}.get(name, name)

        tool = self.selected

        if v.cook_step == 0:

            if name == 'faucet_valve':

                v.is_filling_water = not v.is_filling_water

                v.audio.play('boil' if v.is_filling_water else 'click')

                self.say('Water running.' if v.is_filling_water else 'Valve closed. Filling progress saved.')

            else: self.say(self.hint())

            return None

        oven_controls = {
            'oven_mode': 'Oven mode selector: selects the oven heating elements.',
            'oven_temperature': 'Oven thermostat: sets the oven temperature.',
            'oven_timer': 'Oven timer: sets the baking duration.',
        }
        if name in oven_controls:
            self.say(oven_controls[name] + ' This soup uses the two hob burners.')
            return None
        if not self.pot_placed:
            if tool == 'pot_empty' and math.hypot((x-420)/1.4, y-268) < 105:

                self.animate('pot_empty', (420,370), self.place_pot, origin=(150,365))

            elif name == 'pot_empty':

                self.selected = 'pot_empty'; self.say('Click the outlined left burner to set the pot down.')

            else: self.say(self.hint())

            return None

        if name in ('left_knob', 'right_knob'):

            self.clear_hand()

            if name == 'left_knob':

                v.stove_ignited = not v.stove_ignited

                v.audio.play('click')

                self.say('Left burner ON.' if v.stove_ignited else 'Left burner OFF.')

            else:

                self.right_on = not self.right_on; v.audio.play('click')

                self.say('Right burner ON. Skillet warming.' if self.right_on else 'Right burner OFF.')

            return None

        if tool == 'oil_bottle' and target == 'pan_empty':

            if v.oil_poured: self.say('The skillet already has enough oil.'); return None

            if not self.right_on: self.say('Turn on the RIGHT burner first.'); return None

            self.animate(tool,(854,375),self.pour_oil); return None

        if tool == 'noodles_dry' and target == 'pot_empty':

            if v.cook_step != 2 or not v.stove_ignited:

                self.say('Bring the water to a boil first.'); return None

            self.animate(tool,(420,430),self.add_noodles); return None

        if tool == 'chopsticks' and target == 'pot_empty' and not self.prep:

            if not v.noodles_added: self.say('Add noodles first.'); return None

            self.animate(tool,(420,435),self.stir); return None

        if tool == 'eggs_carton' and target == 'pan_empty':

            if v.cook_step != 3: self.say('Add the noodles before frying the egg.'); return None

            if not v.oil_poured or not self.right_on or self.pan_heat < .6:

                self.say('The skillet needs oil and a warm RIGHT burner first.'); return None

            self.animate('egg_whole',(854,375),self.crack_egg,origin=self.pointer); return None

        if tool == 'shell_half' and name == 'shell_fragment' and v.cook_step == 4:

            self.animate(tool,(814,355),self.scoop_shell,payload='shell_fragment'); return None

        if not self.prep and v.cook_step == 5 and target == 'bowl_empty':

            if not self.shell_disposed: self.say('Let the shell cleanup finish.'); return None

            if v.noodle_cook_progress < 1 or v.egg_cooked_progress < 1:

                self.say('Both foods must finish cooking first.'); return None

            if v.stove_ignited or self.right_on: self.say('Turn BOTH burners off before moving to the serving counter.'); return None

            self.prep = True;self.clear_hand();self.say(self.hint());return None

        if self.prep and tool in ('ladle','chopsticks','spatula'):

            source = 'pan_empty' if tool == 'spatula' else 'pot_empty'

            flag = {'ladle':'broth','chopsticks':'noodles','spatula':'egg'}[tool]

            if target == source:

                if getattr(self,flag):self.say('That portion is already in the bowl.');return None

                self.loaded = flag

                self.say('Carrying '+flag+'. Click inside the bowl.');return None

            if target == 'bowl_empty' and self.loaded == flag:

                payload = {'broth':'broth_surface','noodles':'noodles_cooked','egg':'egg_fried'}[flag]

                self.animate(tool,(650,370),lambda: self.transfer(flag),payload=payload,origin=self.pointer)

                return None

        if self.prep and target == 'bowl_empty' and not tool:

            if self.broth and self.noodles and self.egg:return (640,80)

            self.say(self.hint());return None

        if name in ('knife','cutting_board'):

            self.say('Clean prep tools. No chopping is needed for this recipe.');return None

        pickup = ('noodles_dry','eggs_carton','oil_bottle','shell_half','ladle','chopsticks','spatula')

        if name in pickup:

            if name == 'shell_half' and self.shell_disposed:

                self.say('The used shell stays on its saucer.');return None

            if name == 'eggs_carton' and (v.egg_cracked or self.eggs_remaining == 0):
                self.say('One egg is enough for this bowl. The other stays in the carton.')
                return None
            self.clear_hand()
            if name == 'eggs_carton':
                self.eggs_remaining -= 1
                self.egg_held = True
            self.selected = name
            self.loaded = None

            self.say('Selected '+('one egg' if name=='eggs_carton' else name.replace('_',' '))+'. Click its target.')

        else:self.say(self.hint())

        return None



    def place_pot(self):

        self.pot_placed=True;self.say(self.hint())



    def pour_oil(self):

        self.v.oil_poured=True;self.say('Oil coats the skillet. '+self.hint())



    def add_noodles(self):

        self.v.noodles_added=True;self.v.cook_step=3

        self.v.audio.play('boil');self.say(self.hint())



    def stir(self):

        self.stirred=True;self.say('Noodles loosened with chopsticks. '+self.hint())



    def crack_egg(self):

        self.egg_held = False
        self.v.egg_cracked=True;self.v.eggshell_present=True;self.v.cook_step=4

        self.v.audio.play('chop');self.v.audio.play('sizzle');self.say(self.hint())



    def scoop_shell(self):

        v=self.v;v.eggshell_removed=True;v.cook_step=5;v.audio.play('clue_match')
        self.animate('shell_pair', (1170, 196), self.dispose_shell, origin=(814, 355))
        self.say(self.hint())



    def dispose_shell(self):

        self.shell_disposed=True;self.say(self.hint())



    def transfer(self,flag):

        setattr(self,flag,True);self.say(self.hint())



    def overlay(self):

        r=self.r;v=self.v

        arcade.draw_rect_filled(arcade.XYWH(155,615,180,34),(20,24,31,225))

        arcade.draw_text('BACK TO KITCHEN',155,615,(245,225,185),11,anchor_x='center',anchor_y='center')

        for key,n,x,y,w,h in self.regions:

            if key == self.selected:

                t=r.tex[n];q=min(w/t.width,h/t.height)

                arcade.draw_texture_rect(t,arcade.XYWH(x,y,t.width*q*1.07,t.height*q*1.07),color=Color(255,215,115,170))

                arcade.draw_texture_rect(t,arcade.XYWH(x,y,t.width*q,t.height*q))

        if self.selected:

            name='egg_whole' if self.selected=='eggs_carton' else self.selected

            x,y=self.pointer

            self.draw_hand(name,x+28,y+32)

            if self.loaded:

                payload={'broth':'broth_surface','noodles':'noodles_cooked','egg':'egg_fried'}[self.loaded]

                self.draw_hand(payload,x+25,y+55,65,40)

        if self.motion:

            m=self.motion;p=min(1,m['elapsed']/.75);a=m['origin'];b=m['target']

            x=a[0]+(b[0]-a[0])*p;y=a[1]+(b[1]-a[1])*p+35*math.sin(math.pi*p)

            angle=-25*math.sin(math.pi*p)

            if m['name']=='chopsticks' and not self.prep:

                x+=18*math.sin(p*math.pi*4);y+=8*math.cos(p*math.pi*4)

            frame_name = 'shell_pair' if m['name'] == 'egg_whole' and p >= .55 else m['name']
            self.draw_hand(frame_name,x,y,150 if m['name']=='pot_empty' else 90,120,angle)
            if m['name'] == 'egg_whole' and p >= .55:
                self.draw_hand('egg_raw', x, y - 22, 65, 40)

            if m['payload']:self.draw_hand(m['payload'],x,y+12,65,40)

            if m['name']=='oil_bottle' and p>.45:

                arcade.draw_line(x-10,y-15,854,345,(240,196,65,190),3)





    def draw_hand(self,name,x,y,w=80,h=90,angle=0):

        texture_name = self.r.filled_pot_name() if name == 'pot_empty' else name
        t = self.r.tex[texture_name]
        q = min(w / t.width, h / t.height)

        arcade.draw_texture_rect(t,arcade.XYWH(x,y,t.width*q,t.height*q),angle=angle)



    def assembly(self):

        r=self.r;v=self.v

        r.background('prep_background')

        pot_frame = 'pot_broth_golden' if self.noodles else 'pot_noodles_golden'
        r.sprite(pot_frame, 270, 350, 260, 215, key='pot_empty')

        r.sprite('pan_oiled' if v.oil_poured else 'pan_empty',1010,330,330,190,key='pan_empty')

        if not self.egg:r.sprite('egg_fried',945,340,125,90)

        bowl_frames = {
            (False, False, False): 'bowl_empty',
            (True, False, False): 'bowl_broth',
            (False, True, False): 'bowl_noodles',
            (False, False, True): 'bowl_egg',
            (True, True, False): 'bowl_broth_noodles',
            (True, False, True): 'bowl_broth_egg',
            (False, True, True): 'bowl_noodles_egg',
            (True, True, True): 'bowl_soup',
        }
        bowl_frame = bowl_frames[(self.broth, self.noodles, self.egg)]
        if self.broth and self.noodles and self.egg:
            bowl_key = 'bowl_soup'
        elif self.noodles:
            bowl_key = 'bowl_noodles'
        elif self.broth:
            bowl_key = 'bowl_broth'
        elif self.egg:
            bowl_key = 'bowl_egg'
        else:
            bowl_key = 'bowl_empty'
        r.sprite(bowl_frame, 650, 325, 310, 245, key=bowl_key)

        for n,x in [('ladle',440),('chopsticks',650),('spatula',855)]:r.sprite(n,x,180,85,140)

        if self.broth:

            for j in range(4):

                yy=420+((v.t*30+j*24)%100)

                arcade.draw_circle_filled(650+math.sin(v.t+j)*25,yy,8,(235,229,215,35))

        r.title('ASSEMBLE YOUR SOUP',self.hint())

