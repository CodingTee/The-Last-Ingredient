"""Small contextual affordances for the Royal sprite interactions."""
import math
import arcade


class RoyalImmersion:
    def __init__(self, v, assets):
        self.v = v
        self.prep_scene = arcade.load_texture(assets / 'prep_table_closeup_v1.png')

    def hotspot(self,label,x,y,w,h,action,enabled=True):
        v=self.v
        v.buttons.append((x,y,w,h,action,enabled,label))
        if enabled:
            mx,my=v.mouse
            if x<=mx<=x+w and y<=my<=y+h:
                from scenes.royal_view import text,GOLD
                text(label,min(1240,mx+18),min(820,my+25),15,GOLD)

    def cooking_banner(self):
        from scenes.royal_view import box, text, GOLD, WHITE
        v = self.v
        c = v.cook
        if c.stage == 'fill':
            if len(c.ingredients) == 3:
                message = 'Click the coal bucket to add coal and start heating.'
            elif c.water > .72:
                message = 'Too much water. Right-click the pot to remove a little.'
            elif c.water_ready:
                message = 'Release the mouse to stop pouring.' if v.hold == 'pour' else 'Drag the ingredient tray over the pot and hold.'
            else:
                message = 'Hold the left mouse button on the jug until the water reaches the mark.'
            title = 'Water and ingredients'
        elif c.stage == 'boil':
            title = 'Bring to a boil'
            if v.coal_motion is not None:
                message = 'Adding coal. Wait for the firebox to close.'
            elif v.range_hardware.door_open:
                message = 'Click the firebox door to close it before adjusting the vent.'
            elif c.heat == 0:
                message = 'Fire is unlit! Click the coal bucket on the right to add coal and ignite.'
            elif c.air_opening == 0:
                message = 'Open the air vent clockwise to start the fire.'
            elif c.heat == 1:
                message = 'Medium heat active (1/2). Click bucket to add another shovel for High heat.'
            elif c.air_opening < .99:
                message = 'High heat active (2/2)! Drag the air vent clockwise to Open for maximum boil.'
            else:
                message = 'Coal burning strong! Keep heat up until the soup reaches 96 C.'
        elif c.stage == 'simmer':
            title = 'Simmer on the same hob'
            message = 'Reduce the air vent for a gentle simmer. Stir in circles and check with the spoon.'
        elif c.stage == 'returned' and c.salted:
            title = 'Mix the salt'
            message = 'Drag the wooden spoon around the pot twice to start serving.'
        elif c.stage == 'serve':
            title = 'Serve the soup'
            message = 'Click the full bowl to carry it.' if c.served >= 1 else 'Click the bowl to pour.' if v.serving.loaded else 'Click the pot to scoop soup.' if v.serving.selected else 'Pick up the ladle.'
        else:
            return
        rows = []
        if c.stage == 'fill':
            rows.append(('Water level', c.water / .85, 'Ready' if c.water_ready else 'Too much' if c.water > .72 else 'Fill to green', c.water_ready))
        elif c.stage == 'boil':
            fraction = max(0, (c.temperature - 18) / (96 - 18))
            rows.append(('Water temp', fraction, f'{int(c.temperature)} / 96 C', c.temperature >= 96))
            rows.append(('Broth level', c.water / .85, f'{int(c.water * 100)}%', c.water >= .45))
        elif c.stage == 'serve':
            rows.append(('Bowl fill', c.served, f'{round(c.served * 3)} / 3 ladles', c.served >= 1))
        elif c.stage == 'simmer':
            turns = min(1, abs(v.stir_travel) / math.tau) if v.hold == 'stir' else 0
            if c.heat == 0:
                message = 'Add coal to keep the soup simmering.'
            elif c.air_opening == 0:
                message = 'Open the air vent a little to keep the soup simmering.'
            elif c.air_opening >= .80:
                message = 'Airflow is high. Reduce the vent opening to prevent scorching.'
            elif c.water < 0.45:
                message = 'Broth is low from evaporation! Click the jug on the right or [Add water] to replenish.'
            elif c.air_opening > .55:
                message = 'Reduce the air vent for a gentler simmer.'
            elif c.ready:
                message = 'Soup is ready! Vegetables are tender and broth is rich. Click [Finish simmering].'
            elif c.unstirred >= 16:
                message = 'Drag the spoon into the pot and stir one circle to prevent sticking.'
            elif c.softness >= 1:
                message = 'Click [Check soup] with spoon to inspect thickness and taste.'
            else:
                message = 'Simmering gently at 70-80 C on cast iron heat. Stir occasionally until vegetables soften.'
            if v.inspect_motion is not None and v.soup_sample:
                message = v.soup_sample['advice']
            elif v.hold == 'stir':
                message = 'Complete one circle to add 2% to the cooking progress.'
            status = 'Ready' if c.ready else 'Needs water' if c.water < 0.45 else 'Needs stirring' if c.unstirred >= 16 else 'Check thickness' if c.softness >= 1 else f'{int(c.softness * 100)}% tender'
            rows.append(('Soup doneness', c.softness, status, c.ready))
            water_status = 'Low (Add water)' if c.water < 0.45 else ('Normal' if c.water <= 0.70 else 'Plentiful')
            rows.append(('Broth level', min(1.0, c.water / .75), f'{int(c.water * 100)}% ({water_status})', c.water >= 0.45))
        if c.stage in {'boil', 'simmer'}:
            coal = c.coal_fuel / 2
            coal_value = f'{math.ceil(coal * 100)}%'
            if coal > 0 and c.air_opening == 0:
                coal_value += ' · No airflow'
            rows.append(('Coal fire', coal, coal_value, False))
            vent_ready = c.air_opening >= .99 if c.stage == 'boil' else 0 < c.air_opening <= .55
            rows.append(('Air vent', c.air_opening, f'{c.air_opening:.0%}', vent_ready))

        top = 450 + v.window.height / v.canvas.scale / 2
        row_count = (len(rows) + 1) // 2
        height = 54 + 28 * row_count
        box(230, top-15-height, 980, height, (19, 17, 16, 232), (122, 93, 56))
        text(f'{title} · {message}', 248, top-40, 12, WHITE)
        bar_width = 155
        for index, (label, fraction, value, ready) in enumerate(rows):
            row, column = divmod(index, 2)
            x = 248 + 478 * column
            y = top - 66 - 28 * row
            bar_x = x + 142
            text(label, x, y, 13, WHITE)
            text(value, bar_x + bar_width + 10, y, 12, WHITE)
            box(bar_x, y+2, bar_width, 8, (58, 49, 39))
            if c.stage == 'fill':
                box(bar_x+bar_width*.45/.85, y+2, bar_width*(.72-.45)/.85, 8, (61, 111, 77))
            if fraction > 0:
                if label == 'Coal fire':
                    color = (255, 85, 36) if fraction > .5 else (255, 190, 72)
                    if c.air_opening == 0:
                        color = (130, 128, 125)
                else:
                    color = (135, 205, 159) if ready else (213, 132, 99) if c.stage == 'fill' and c.water > .72 else GOLD
                box(bar_x, y+3, bar_width*min(1, fraction), 6, color)

    def overlay(self):
        from scenes.royal_view import image,text,box,GOLD,WHITE
        v=self.v
        if v.is_paused:return
        if v.page == 'cooking' and not v.in_map():
            self.cooking_banner()
        if v.page=='cooking' and not v.in_map():
            c=v.cook
            if c.stage=='prep':
                # Onion already starts on the board, so it no longer needs a
                # left-side thumbnail. The carrot waits on the left (enlarged and
                # stood upright) until the player clicks it; clicking flies it
                # onto the board, after which the left panel is empty.
                if v.chop_item == 'onion' and v.carrot_fly is None:
                    # Rest on the left as a small, horizontal carrot (not on the board).
                    arcade.draw_texture_rect(v.carrot_frames[0], arcade.XYWH(120, 370, 200, 84), angle=0)
                    ready = v.cook.cuts['onion'] >= 10 and v.chop_motion is None and v.onion_turn_motion is None
                    self.hotspot('Carrot', 5, 320, 210, 95, 'select_carrot', ready)
            elif c.stage=='fill':
                image(v.boil_sprites['coal_bucket'],1170,465,185,200)
                ready=.45<=c.water<=.72 and len(c.ingredients)==3
                if ready:self.hotspot('Add coal',1065,355,210,220,'boil')
        if v.page=='cooking' and not v.in_map():
            x,y=v.mouse;c=v.cook;hint=''
            if c.stage=='fill':
                hint=v.batch_tray.hint(x,y)
                if 1140<x<1340 and 510<y<740:hint='Hold to pour' if not c.ingredients and not c.water_ready and v.hold!='pour' else ''
                if not c.ingredients and not v.batch_tray.dragging and c.water>0 and 280<x<650 and 460<y<650:hint='Right-click to remove a little water'
            elif c.stage in {'boil','simmer'}:
                hint=v.range_hardware.hint(x,y)
                if 1065<x<1275 and 355<y<575:hint='Add coal'
                if c.stage=='simmer' and 1140<x<1340 and 510<y<740:
                    from scenes.royal_water_feedback import water_hint
                    hint=water_hint(c)
                if c.stage=='simmer' and 760<x<940 and 360<y<540 and v.hold is None:hint='Drag to stir. Click to check.'
            if hint:text(hint,min(940 if len(hint)>30 else 1100,x+18),min(800,y+25),15,GOLD)
        # In-map prompts are now rendered as Scene-7 style floating popup cards above workstations
        pass

    def prep_background(self):
        from scenes.royal_view import image
        v=self.v
        image(self.prep_scene,720,450,1440,900)
        v.prep_board()
        v.button('',20,820,60,55,'prep_exit',v.chop_motion is None and v.onion_turn_motion is None and v.carrot_fly is None)
