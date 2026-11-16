"""Explicit evidence recording and modal decisions for the future laboratory."""
import arcade

from core.constants import ASSETS_DIR

EVIDENCE={
 'analysis':('Evidence I — Triangular wound','evidence_wound',[
  ('Observe the wound','A three-sided puncture wound matches the future laboratory dart launcher.\n\nThe neural toxin was carried by the wounded beast before it was cooked.'),
  ('Confirm the comparison','The projectile profile and wound morphology match.\n\nThis connects the prehistoric beast directly to future laboratory weaponry.')]),
 'sample':('Evidence II — The salt jar','evidence_salt_jar',[
  ('Compare the samples','Dried blue residue inside the royal salt jar matches the laboratory chemical precursor.\n\nThe 1910 poisoning did not originate from the chef\'s soup recipe.'),
  ('Reconstruct the spill','While the kitchen was empty, someone disturbed the shelf and spilled the blue toxin into the familiar salt container.')]),
 'archive':('Evidence III — The modern sample','evidence_modern',[
  ('Trace the distribution','The lethal powder from the modern restaurant matches synthetic compounds excavated from ancient strata and reproduced here.'),
  ('Connect the records','The ancient residue, laboratory synthesis, and modern poisoning are all links in one causal chain.')]),
}
REALISATION=[
 ('Three linked observations','The dart launcher wounded the ancient beast.\nThe blue vial contaminated the royal salt jar.\nThe recovered sample matches the modern toxin.'),
 ('The causal loop','Every physical intervention into the past did not prevent disaster—it caused it.\n\nThe chef himself brought the poison into history.'),
 ('A choice of destiny','To jump again is to perpetuate the tragic loop.\n\nTo break the cycle, consciousness must return empty-handed.'),
 ('A choice of destiny','You understand the full causal chain.\n\nPrepare a physical Launch, or Abort the jump to return consciousness to your own time.'),
]


class FutureInvestigationUI:
    def __init__(self,lab):
        self.lab=lab;self.page=0;self.realisation_page=0;self.seen=set();self.buttons=[]

        self.showing_image = False
        self.evidence_textures = {}

    def evidence_texture(self, field):
        if field not in self.evidence_textures:
            path = ASSETS_DIR / 'future_lab' / f'{field}_anime.png'
            self.evidence_textures[field] = arcade.load_texture(path)
        return self.evidence_textures[field]

    def draw_evidence_image(self, w, h, title, field):
        texture = self.evidence_texture(field)
        left, y, width = self.frame(w, h, title, '')
        scale = min((width - 60) / texture.width,
                    (min(580, h - 60) - 132) / texture.height)
        arcade.draw_texture_rect(texture, arcade.XYWH(
            left + width / 2, h / 2 + 8,
            texture.width * scale, texture.height * scale))
        self.button('hide_image', 'Back to evidence [Esc]', w / 2, y)

    def frame(self,w,h,title,body,page_text=''):
        pw=min(920,w-50);ph=min(580,h-60);cx,cy=w/2,h/2
        self.buttons=[]
        arcade.draw_rect_filled(arcade.XYWH(cx,cy,pw,ph),(10,18,28,248))
        arcade.draw_rect_outline(arcade.XYWH(cx,cy,pw,ph),(96,207,231),2)
        l=cx-pw/2
        self.lab._text(title,l+30,cy+ph/2-42,20,(244,211,146),bold=True)
        if page_text:self.lab._text(page_text,l+30,cy+ph/2-72,12,(139,198,221))
        self.lab._text(body,l+30,cy+20,15,(230,240,248),width=pw-60)
        return l,cy-ph/2+45,pw

    def button(self,action,label,x,y,width=230,enabled=True):
        arcade.draw_rect_filled(arcade.XYWH(x,y,width,42),(24,63,82) if enabled else (32,39,46))
        arcade.draw_rect_outline(arcade.XYWH(x,y,width,42),(128,224,247) if enabled else (65,84,96),1.5)
        self.lab._text(label,x,y,12,(239,244,248) if enabled else (126,141,151),bold=True,center=True)
        self.buttons.append((action,x,y,width,42,enabled))

    def hit(self,x,y):
        return next((a for a,cx,cy,w,h,enabled in reversed(self.buttons) if enabled and abs(x-cx)<=w/2 and abs(y-cy)<=h/2),None)

    def draw_panel(self,w,h,station):
        lab=self.lab;nid=station[0]
        if nid in EVIDENCE:
            title,field,pages=EVIDENCE[nid];heading,body=pages[self.page]
            if self.showing_image:
                self.draw_evidence_image(w, h, title, field)
                return
            status = 'RECORDED' if getattr(lab, field) else 'NOT RECORDED'
            l, y, pw = self.frame(w, h, title, '', f'{self.page+1} / {len(pages)}  |  {status}')
            top = h / 2 + min(580, h - 60) / 2
            preview_width = min(340, (pw - 82) * .42)
            text_width = pw - preview_width - 82
            lab._text(heading, l + 30, top - 115, 17, (244,211,146), bold=True)
            lab._text(body, l + 30, top - 145, 15, (230,240,248), width=text_width)
            texture = self.evidence_texture(field)
            scale = min(preview_width / texture.width, max(1, top - y - 190) / texture.height)
            preview_height = texture.height * scale
            preview_x = l + pw - 30 - preview_width / 2
            arcade.draw_texture_rect(texture, arcade.XYWH(
                preview_x, top - 104 - preview_height / 2,
                texture.width * scale, preview_height))
            self.button('show_image', 'View Image [I]', preview_x,
                        top - 134 - preview_height, min(190, preview_width))
            self.button('close','Step away [E / Esc]',l+140,y,220)
            if self.page:self.button('previous','Previous',l+pw/2,y,140)
            last=self.page==len(pages)-1
            self.button('record' if last else 'next','Record comparison [Enter]' if last else 'Next comparison [Enter]',l+pw-170,y,280)
            return
        if nid=='capsule':
            if lab.transit_committed:
                body=('Nutritional preparation is complete. Secure the field equipment, enter the capsule and explicitly activate physical transit.' if lab.nutrient_consumed else 'The Launch preparation decision is recorded. Visit Food Synthesizer, select Nutrient Block, confirm the current body profile, synthesize and consume the ration.\n\nFood provides energy; it does not perform a jump.')
                label='Open departure bay' if lab.nutrient_consumed else 'Review preparation'
            else:
                body=('You understand the evidence, but still insist that a different intervention might succeed.' if lab.truth_understood else 'You have not yet completed the explanation. A physical intervention remains your explicit choice.')+'\n\nConfirm Launch to prepare the body and equipment. No physical transit occurs until the capsule is activated.'
                label='Choose Launch preparation'
            l,y,pw=self.frame(w,h,'Physical Jump Capsule',body)
            self.button('close','Step away [E / Esc]',l+150,y,240)
            self.button('launch',label+' [Enter]',l+pw-210,y,350)
        elif nid=='chair':
            body=('The three comparisons and their complete explanation must be confirmed before Abort.\n\nContinue investigating. Closing a panel, waiting or leaving an instrument does not choose an ending.' if not lab.truth_understood else 'You understand the chain of consequences.\n\nExplicitly Abort physical intervention to begin the return path. The body and physical objects cannot return with consciousness.\n\nYou may also step away and keep investigating without choosing.')
            l,y,pw=self.frame(w,h,'Consciousness Return — Abort Time Jump',body)
            self.button('close','Step away [E / Esc]',l+150,y,240)
            self.button('abort','Abort Time Jump [Enter]',l+pw-190,y,310,lab.truth_understood)
        elif nid=='kitchen':
            l,y,pw=self.frame(w,h,'Food Synthesizer','Choose an ordinary practice meal, or prepare a transit ration after an explicit Launch decision.\n\nThe ordinary meal does not select an ending and does not satisfy physical-transit nutrition. Nutrient Block requires the current-body scan and its own complete preparation sequence.')
            self.button('practice','Ordinary meal',l+170,y,270)
            self.button('nutrient','Nutrient Block',l+pw-180,y,280,lab.transit_committed)
            self.button('close','Step away [E / Esc]',l+pw/2,y+65,240)
        else:
            l,y,pw=self.frame(w,h,station[1],station[3]);self.button('close','Close [Enter / E / Esc]',l+pw/2,y,300)

    def draw_realisation(self,w,h):
        self.seen.add(self.realisation_page)
        title,body=REALISATION[self.realisation_page]
        l,y,pw=self.frame(w,h,'The Realisation — '+title,body,f'{self.realisation_page+1} / {len(REALISATION)}')
        self.button('dismiss_review','Investigate later [Esc]',l+150,y,250)
        if self.realisation_page:self.button('real_previous','Previous',l+pw/2,y,140)
        final=self.realisation_page==len(REALISATION)-1
        self.button('understand' if final else 'real_next','I understand [Enter]' if final else 'Read next [Enter]',l+pw-170,y,270)

    def act(self,action):
        lab=self.lab
        if action in ('show_image', 'hide_image'):
            self.showing_image = action == 'show_image'
            self.buttons = []
        elif action=='close':lab._close_panel()
        elif action=='next':self.page=min(len(EVIDENCE[lab.panel[0]][2])-1,self.page+1)
        elif action=='previous':self.page=max(0,self.page-1)
        elif action=='record':lab._record_evidence()
        elif action=='real_previous':self.realisation_page=max(0,self.realisation_page-1)
        elif action=='real_next':
            self.seen.add(self.realisation_page);self.realisation_page=min(len(REALISATION)-1,self.realisation_page+1)
        elif action=='understand':lab._dismiss_realisation()
        elif action=='dismiss_review':lab.showing_realisation=False;lab.keys.clear()
        elif action=='launch':lab._confirm_physical_transit()
        elif action=='abort':lab._confirm_abort()
        elif action=='practice':lab._enter_practice_cooking()
        elif action=='nutrient':
            if lab.transit_committed:lab.panel=None;lab._enter_nutrient_preparation()
