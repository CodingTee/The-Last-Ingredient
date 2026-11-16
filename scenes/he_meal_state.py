"""HE-only cooking state. No ending or achievement is chosen by cooking mistakes."""
from dataclasses import dataclass,field

@dataclass
class HEMeal:
    phase:str='program'
    selected:set=field(default_factory=set)
    water:bool=False
    noodles:bool=False
    egg_cracks:int=0
    temperature:float=22.
    power:float=0.
    heating:bool=False
    boil_progress:float=0.
    noodle_progress:float=0.
    auto_stir:bool=False
    egg_progress:float=0.
    presentation_rejected:bool=False
    broth_served:bool=False
    noodles_served:bool=False
    egg_lifted:bool=False
    egg_served:bool=False
    carrying:bool=False
    warning_read:bool=False
    bowl_placed:bool=False
    returned:bool=False
    feedback:str='Close the nutrient-block program. This meal is for you.'

    def act(self,action):
        p=self.phase
        transitions={
            ('program','close_program'):'choose',
            ('choose','confirm'):'recipe',
            ('recipe','begin'):'water',
            ('water','pour_water'):'heat_water',
            ('add_noodles','add_noodles'):'cook_noodles',
            ('add_egg','egg_to_pan'):'crack_egg',
            ('serve_broth','broth_to_bowl'):'serve_noodles',
            ('serve_noodles','noodles_to_bowl'):'serve_egg',
            ('serve_egg','egg_to_bowl'):'presentation',
            ('presentation','keep'):'pickup',
            ('pickup','pick_up'):'carry',
            ('carry','read_warning'):'carry',
            ('carry','place_bowl'):'return',
            ('return','return_empty'):'returning'
        }
        if action.startswith('select_') and p=='choose' and action[7:] in {'water','noodles','egg'}:
            self.selected.add(action[7:]);return True
        if p=='choose' and action=='confirm' and self.selected!={'water','noodles','egg'}:
            self.feedback='Choose ordinary water, noodles and an egg first.';return False
        if p=='presentation' and action=='adjust':
            self.feedback='The egg is cooked. Its uneven edge does not need fixing.';return False
        if p=='crack_egg' and action=='crack':
            self.egg_cracks+=1
            if self.egg_cracks>=2:
                self.phase='fry_egg';self.temperature=22.;self.power=0.;self.heating=False
                self.feedback='Start the pan. Keep a gentle 130-165 C to fry the egg.'
            else:self.feedback='One more gentle tap to open the shell.'
            return True
        if action=='start_stir' and p=='cook_noodles':
            self.auto_stir=True;self.feedback='Automatic magnetic stirring in progress.';return True
        if action=='heat' and p in ('heat_water','fry_egg'):
            self.heating=True;return True
        if p=='pickup' and action=='pick_up' and not self.presentation_rejected:return False
        if p=='carry' and action=='place_bowl' and (not self.warning_read or not self.carrying):
            self.feedback='Take the bowl to Consciousness Return first.';return False
        if p=='return' and action=='return_empty' and (self.carrying or not self.bowl_placed):
            return False
        next_phase=transitions.get((p,action))
        if not next_phase:return False
        self.phase=next_phase
        if action=='pour_water':
            self.water=True;self.feedback='Start heating. Keep the water at 90-100 C.'
        elif action=='add_noodles':
            self.noodles=True;self.heating=False;self.feedback='Start the robotic magnetic stirrer.'
        elif action=='begin':
            self.feedback='Drag the water jug into the soup pot.'
        elif action=='close_program':
            self.feedback='Choose ordinary water, noodles and an egg.'
        elif action=='confirm':
            self.feedback='For the person who was ready to give up: a warm bowl, and another tomorrow.'
        elif action=='broth_to_bowl':
            self.broth_served=True;self.feedback='Use the chopsticks to move the noodles from the pot into the bowl.'
        elif action=='noodles_to_bowl':
            self.noodles_served=True;self.feedback='Slide the spatula beneath the egg, then place it on the noodles.'
        elif action=='egg_to_bowl':
            self.egg_served=True;self.egg_lifted=False
            self.feedback='Adjust presentation? The meal is already warm and complete.'
        elif action=='keep':
            self.presentation_rejected=True;self.feedback="No. It's good just like this."
        elif action=='pick_up':
            self.carrying=True;self.feedback='Carry the bowl to Consciousness Return.'
        elif action=='read_warning':
            self.warning_read=True
            self.feedback="Physical items cannot be transferred. Leave the bowl on the research table."
        elif action=='place_bowl':
            self.carrying=False;self.bowl_placed=True
            self.feedback="The bowl stays here. Return to the chair empty-handed."
        return True

    def update(self,dt,stir=False):
        dt=min(.1,max(0,dt))
        if self.phase=='heat_water' and self.heating:
            self.temperature+=(22+100*self.power-self.temperature)*min(1,dt*.9)
            if 90<=self.temperature<=100:
                self.feedback='Gentle boil. Keep the water in this range.'
                self.boil_progress=min(3,self.boil_progress+dt)
            elif self.temperature>100:
                self.boil_progress=max(0,self.boil_progress-dt*.35)
                self.feedback='The water is boiling too fiercely. Lower the power.'
            if self.boil_progress>=3:
                self.phase='add_noodles';self.feedback='Water is ready. Drag the noodles into the pot.'
        elif self.phase=='cook_noodles' and self.auto_stir and stir:
            self.noodle_progress=min(4,self.noodle_progress+dt)
            if self.noodle_progress>=4:
                self.auto_stir=False;self.phase='add_egg';self.feedback='Use the separate frying pan. Drag the egg onto it.'
        elif self.phase=='fry_egg' and self.heating:
            self.temperature+=(22+250*self.power-self.temperature)*min(1,dt*.9)
            if 130<=self.temperature<=165:
                self.feedback='The white is setting. A gently browned edge is enough.'
                self.egg_progress=min(5,self.egg_progress+dt)
            elif self.temperature>165:
                self.feedback='Lower the heat. An uneven browned edge is fine.'
            if self.egg_progress>=5:
                self.phase='serve_broth';self.heating=False
                self.feedback='Dip the ladle into the pot, then pour broth into the bowl.'
