import math

SWITCH=(1440,107,120,64)
HINT_RING=(1440,107,158.4,102.4)
HINT_ARROW=(1410,187,58,42)
# Decorative lab switch, sheared to the station's -39 deg perspective.
LAB_SWITCH=(410.5,525,14,20.2)
HOLO=(1330,506,484,730)
CONSOLE_WIPE=.25

CONSOLE_ART = ("console_switch_on", "console_switch_off", "switch_hint_ring", "switch_hint_arrow", "holo_panel", "holo_frame")
LIFT_ART = ("lift_opening", "lift_cover", "lift_door_lower", "lift_door_upper", "lift_front_edge")

def advance_console(self,dt):
    # Symmetric reveal timer: the off switch replays the wipe in reverse.
    step=dt if self.console_open else -dt
    self.console_t=max(0.,min(CONSOLE_WIPE,self.console_t+step))

def draw_console_chrome(self):
    # Physical toggle stays visible while the screen is closed.
    self.sprite('console_switch_on' if self.console_open else 'console_switch_off',SWITCH)
    if not self.console_open:
        if self.console_hint:
            pulse=.82+.18*math.sin(self.elapsed*4.2)
            a=int(255*pulse)
            self.sprite('switch_hint_ring',HINT_RING,alpha=a)
            bob=6*math.sin(self.elapsed*4.2)
            self.sprite('switch_hint_arrow',(HINT_ARROW[0],HINT_ARROW[1]+bob,*HINT_ARROW[2:]),alpha=a)
        if self.inside(self.mouse[0],self.mouse[1],SWITCH):
            self.sprite('console_switch_on',SWITCH,alpha=110)
    t=min(1.,max(0.,self.console_t/CONSOLE_WIPE))
    if t>=1. and self.console_open:
        self.sprite('holo_panel',HOLO)
        sweep=HOLO[1]+HOLO[3]/2-50-((self.elapsed*95)%(HOLO[3]-100))
        self.box((HOLO[0],sweep,HOLO[2]-44,9),(112,228,245,26))
        self.sprite('holo_frame',HOLO,alpha=int(178+56*math.sin(self.elapsed*2.1)))
        return True
    if t>0.:
        e=t*t*(3-2*t)
        h=HOLO[3]*(.12+.88*e)
        self.sprite('holo_panel',(HOLO[0],HOLO[1]-HOLO[3]/2+h/2,HOLO[2],h),alpha=int(255*e))
    return False

def draw_rising_cartridge(view, art, bounds, opening, rise):
    """Use the kitchen hatch and clip the rising sprite at the countertop."""
    ctx = view.window.ctx
    previous = ctx.scissor
    left, bottom = view.xy(69, 370)
    right, top = view.xy(281, 430)
    middle = (top + bottom) / 2
    gap = (top - bottom) * opening / 2
    try:
        if gap >= 1 and rise < 1:
            ctx.scissor = (int(left), int(middle-gap), int(right-left), int(2*gap))
            view.sprite('lift_opening', (175,400,212,60), alpha=int(255*min(1,(1-rise)*8)))
        if 0 < opening < 1:
            for sprite_name, start, end, y in (
                ('lift_door_lower', bottom, middle-gap, 385-30*opening),
                ('lift_door_upper', middle+gap, top, 415+30*opening),
            ):
                if end-start >= 1:
                    ctx.scissor = (int(left),int(start),int(right-left),int(end-start))
                    view.sprite(sprite_name,(175,y,212,30))
        if rise > 0:
            cutoff = int(bottom)
            ctx.scissor = (0, cutoff, view.window.width, view.window.height-cutoff)
            x,y,w,h = bounds
            view.sprite(art, (x,y-131*(1-rise),w,h))
    finally:
        ctx.scissor = previous
    if 0 < rise < 1:
        view.sprite('lift_front_edge', (175,374.5,212,9), alpha=int(255*min(1,(1-rise)*8)))
