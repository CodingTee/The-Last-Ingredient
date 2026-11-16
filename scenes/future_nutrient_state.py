"""BE food preparation rules, including timed physical transfer interlocks."""
from dataclasses import dataclass, field
from enum import IntEnum

TRANSFER_SECONDS=4.2
HOOD_OPEN_SECONDS=.7
TRAY_DELIVERY_SECONDS=1.8
TRAY_TRANSFER_SECONDS=TRAY_DELIVERY_SECONDS+.6
EAT_SECONDS=3.4

class Phase(IntEnum):
    RECIPE=0
    SCAN=1
    PROFILE=2
    LOAD=3
    MIX=4
    READY=5
    SYNTHESIZE=6
    COLLECT=7
    CONSUME=8
    EATING=9
    DONE=10

@dataclass
class NutrientPreparation:
    phase: Phase=Phase.RECIPE
    selected: bool=False
    scan_active: bool=False
    scan_time: float=0.
    ingredients: list=field(default_factory=list)
    mix_time: float=0.
    synthesis_time: float=0.
    age: float=0.
    transfer: float=0.
    last_ingredient: int=-1
    message: str='Select the transit ration recipe preview.'

    @property
    def can_action(self):
        if self.phase==Phase.RECIPE:return self.selected
        if self.phase==Phase.SCAN:return not self.scan_active
        if self.phase in (Phase.PROFILE,Phase.READY,Phase.DONE):return True
        if self.phase==Phase.COLLECT:return self.age>=HOOD_OPEN_SECONDS
        if self.phase==Phase.CONSUME:return self.age>=TRAY_TRANSFER_SECONDS
        return False

    def go(self,phase,message):
        self.phase=phase;self.age=0.;self.message=message

    def load(self,index):
        if self.phase!=Phase.LOAD:return False
        if self.transfer>0:
            self.message='Wait for the current cartridge to finish dispensing.'
            return False
        if index not in range(4) or index!=len(self.ingredients):
            self.message='Load in order: base, gel, crystal, binding solution.'
            return False
        self.last_ingredient=index
        self.transfer=TRANSFER_SECONDS
        self.message='Opening and dispensing the food cartridge...'
        return True

    def action(self):
        p=self.phase
        if not self.can_action:
            if p==Phase.RECIPE:self.message='Select the NUTRIENT BLOCK recipe preview first.'
            elif p==Phase.COLLECT:self.message='Wait for the protective hood to finish opening.'
            elif p==Phase.CONSUME:self.message='Wait for the ration to reach the serving tray.'
            return False
        if p==Phase.RECIPE:
            self.go(Phase.SCAN,'Scan the current future body before synthesis.')
        elif p==Phase.SCAN:
            self.scan_active=True;self.message='Scanning current body profile...'
        elif p==Phase.PROFILE:
            self.go(Phase.LOAD,'Body profile confirmed. Select nutrient-base cartridge.')
        elif p==Phase.READY:
            self.go(Phase.SYNTHESIZE,'Shield closing. Stabilizing the mixture.')
        elif p==Phase.COLLECT:
            self.go(Phase.CONSUME,'Retrieving the serving tray from the lift.')
        elif p==Phase.CONSUME:
            self.go(Phase.EATING,'Taking the transit ration...')
        else:return False
        return True

    def update(self,dt,stirring=False):
        if dt<=0:return
        self.age+=dt
        was_transferring=self.transfer>0
        self.transfer=max(0.,self.transfer-dt)
        if was_transferring and self.transfer<=1e-6:
            self.transfer=0.
            if self.last_ingredient==len(self.ingredients):
                self.ingredients.append(self.last_ingredient)
                self.message=['Nutrient base loaded. Add the energy gel.',
                              'Energy gel loaded. Add the white crystals.',
                              'Crystals loaded. Add the binding solution.',
                              'All food ingredients loaded.'][self.last_ingredient]
        if self.phase==Phase.SCAN and self.scan_active:
            self.scan_time=min(3.,self.scan_time+dt)
            if self.scan_time>=3.-1e-6:
                self.go(Phase.PROFILE,'CURRENT BODY PROFILE: COMPATIBLE. Confirm this profile.')
        elif self.phase==Phase.LOAD and len(self.ingredients)==4 and not self.transfer:
            self.go(Phase.MIX,'Hold SPACE to mix the ingredients into a uniform paste.')
        elif self.phase==Phase.MIX and stirring:
            self.mix_time=min(4.,self.mix_time+dt)
            if self.mix_time>=4.-1e-6:self.go(Phase.READY,'Uniform soft mixture. Start the synthesis cycle.')
        elif self.phase==Phase.SYNTHESIZE:
            self.synthesis_time=min(6.,self.synthesis_time+dt)
            if self.synthesis_time<2:self.message='Stabilizing mixture / shield closed'
            elif self.synthesis_time<4:self.message='Pressing / forming the rectangular ration'
            elif self.synthesis_time<6.-1e-6:self.message='Cooling / wait for the hood to open'
            else:self.go(Phase.COLLECT,'Opening the protective hood. Please wait.')
        elif self.phase==Phase.COLLECT and self.can_action:
            self.message='Hood open. Collect the finished nutrient block.'
        elif self.phase==Phase.CONSUME and TRAY_DELIVERY_SECONDS<=self.age<TRAY_TRANSFER_SECONDS:
            self.message='Moving the ration onto the tray.'
        elif self.phase==Phase.CONSUME and self.can_action:
            self.message='Ration on tray. Consume it to finish nutritional preparation.'
        elif self.phase==Phase.EATING:
            self.message=('Taking the transit ration...' if self.age<.8 else
                          'Eating the ration...' if self.age<2.5 else 'Finishing the ration...')
            if self.age>=EAT_SECONDS:
                self.go(Phase.DONE,'Nutritional preparation complete. Return to the Physical Jump Capsule.')
