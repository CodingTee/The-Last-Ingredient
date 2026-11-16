# Prehistoric cooking rebuild

Entry: run_scene_11.py in the ISE developer workspace.

Scope: S10 wound inspection, S11 cooking and guard handoff, S12 fixed-memory collapse, S13 wakeup and continuation to the existing RoyalKitchenView.

## Controls and sequence

1. Walk beside the juvenile; E opens the sprite wound inspection, E or Esc closes it. This clue does not gate cooking.
2. Walk to the hearth spit; E opens first-person cooking. Read the tribe member's request and click or press Enter.
3. Drag the raw meat from the left stone platter onto the spit.
4. Hold the hide fan and sweep left and right. Fire heat responds to movement and fades when released. Roast side A until golden.
5. Click the crank at the right of the spit to play the half-turn animation. Repeated clicks do not reset it. If interrupted, click again to continue.
6. Fan again until side B is cooked. Both sides must be complete before removal.
7. Drag the cooked roast onto the right stone slab, then click the slab to enter its dedicated first-person carving station.
8. Click the flint knife, then swipe downward across each of the three marked cuts. Incorrect cuts do not erase progress.
9. Drag two servings from the slab onto the left platter. Click the loaded platter to carry it in the village.
10. Walk south to the approach between the entrance watchtowers and press E. Drag the platter into the guards' hands. Click or E to return after they begin eating.
11. Return to the hearth, press E, and drag the next raw roast onto the spit. The fixed memory then continues: guards collapse, the bone whistle falls without an alarm, the mother appears, and the image fades.
12. At 03:00, click the Crown or press Enter to continue to the existing Royal chapter.

Esc pauses cooking. Continuous actions stop on pause, focus loss, and view exit. Back to Village retains recipe progress in the active window session; this is not a disk save system. F11 toggles fullscreen in the closeup.

## Art and implementation

Physical props use independent Arcade sprites: three roast states, sliced meat, stone platter, cutting slab, flint knife, hide fan, empty spit, hands, bone whistle, mother, wound, clock, tarot cards, and four poses for each of the two existing guard identities. Backgrounds are sprite layers; the original animated campfire is retained. Camera scaling is uniform, and the 16:10 view reveals more vertical area instead of stretching props.

The map spit reflects the current raw/cooked/removed meat state. The independent northeast cooking rack remains removed. The juvenile remains east of the hearth.

Cooking input/rendering: scenes/prehistoric_bbq_view.py
Recipe state: core/prehistoric_meal.py
Village handoffs: scenes/scene_11_view.py
Assets: assets/prehistoric/cooking_v2/
Regression: python TheLastIngredient/tools/qa_prehistoric_cooking_v2.py from ISE.

Validated with physical mouse/key events through the entire recipe, map carrying, guard handoff, return to hearth, next batch, collapse, silent whistle, mother, wakeup and Royal view transition. Invalid drops/cuts, pause, focus loss, resume, wound inspection, and 16:10 input mapping were also exercised. Visual PNGs were inspected during development.

The shared forest-to-village story handoff and modernization of the Royal chapter are outside this rebuild. No cooking score chooses a bad ending. No alarm sound is played before the whistle falls. Full truth about the fragment remains reserved for later evidence.


## Village continuity update 2026-11-07

The closeups now depict the actual Scene 11 village, replacing the cave-themed backgrounds. Cooking faces north from the central ochre dirt plaza toward the north hut and its northwest/northeast neighbors, with the two woodpiles and surrounding green grass/fence/forest. Guard handoff and collapse face south toward the same paired straw-roof watchtowers and skull-decorated timber gate. The new backgrounds omit painted-in cooking props so animated sprites remain independent. Source map references were rendered from the current Scene11View before generation. Runtime assets: camp_village_bg.png and gate_village_bg.png. Old backgrounds remain available and the previous loader is backed up.


## Skewered roast and click turn update 2026-11-07

The cooking fire width is now 260 + 20 * heat virtual pixels, approximately 1.7 times its previous width, with its base aligned beneath the roast. The removable spit assembly uses nine generated axle-aligned sprites: raw/half/done side A, 45/90/135 degree rolling views, and raw/half/done side B. Each sprite includes the wooden shaft visibly piercing the meat and the matching right-side crank position. The independent spit_supports.png contains only the forked uprights and feet.

Click the right-hand crank when side A is ready. The animation advances the meal turn from its saved angle to 180 degrees over approximately 1.15 seconds for a full half-turn. It changes the visible surfaces around a fixed horizontal axle instead of rotating the entire sprite in the image plane. Pause, focus loss or leaving the view stops the turn; progress remains in the meal object, and another click resumes. The updated regression exercises click turning, repeated clicks and pause/resume before completing the rest of S11-S13.


## Rack attachment correction 2026-11-08

All mounted sprites, including the generated empty spit, now use the same calibrated shaft line derived from the two actual support-fork cradles in spit_supports.png: source pixels (280, 141) and (1230, 148). RACK_CENTER and RACK_WIDTH define the shared station transform. The shaft center is placed one shaft radius above the wood at both cradles and given the corresponding small slope. The rack stays the same while loading meat, changing doneness, turning, and taking meat off. Input targets follow the calibrated height.

python TheLastIngredient/tools/qa_rack_attachment.py checks that opaque shaft pixels pass through both measured contact points in all ten mounted sprites and renders empty/roasting/turning states. The full recipe regression was also run after this correction.


## Fork front occlusion 2026-11-08

spit_fork_front.png is an exact pixel extraction from spit_supports.png, retaining the camera-facing fork arm on each side on the original canvas. It shares RACK_CENTER and RACK_WIDTH with the supports, and is drawn after every mounted shaft frame, before foreground tools/food. This makes the shaft pass behind the front lips of the V-cradles while the outer crank remains exposed. The source artwork, attachment geometry and click-turn behavior are preserved. qa_rack_attachment.py also asserts the support < mounted shaft < fork-front rendering order.


## Independent proportions 2026-11-08

The supports and matching front lips are cropped into left/right native texture sprites, shifted 55 virtual pixels outward on each side without changing their size. Fork spacing grows from about 438 to 548 pixels. The center roast is uniformly scaled to 70 percent of its previous size. Tip and crank remain at their original uniform scale and shift outward with the supports. Repeated narrow native shaft textures bridge the longer exposed wooden axis. The axle slope and contact points are recalculated from the new support positions, and the clickable crank region moves with the right-hand assembly.

qa_rack_attachment.py now checks the rendered component textures at both actual fork contact points in every state, verifies front-lip ordering and equal x/y scaling, and renders selected states. Full cooking and story interaction regression passed after the change.


## External collar visibility 2026-11-08

The right collar and crank now have a separate foreground sprite cropped from each original mounted frame, starting at the collar after the thin exposed shaft. Only the wood shaft stays behind the fork lip; the complete external collar and handle render after the fork front. This preserves the seated-shaft effect while preventing the fork from hiding the collar. The geometry and click region are unchanged. The rack regression checks this foreground exception in every state.


## Collar clearance 2026-11-08

SPIT_EXTENSION adds 75 virtual pixels of exposed shaft at each outer end while keeping support spacing and roast size fixed. The right crank and its matching foreground collar cutout move outward together; the shaft tiles fill the extra length and the click target follows the crank. The fixed empty-spit tip is reused in every cooking state to avoid copying tiny roast fragments into the exposed left tip.


## Dedicated stone-board station 2026-11-08

After both roast sides are cooked, dragging the meat onto the small right-hand slab sets the recipe to carve but keeps the player at the hearth. Clicking the slab opens CarvingBoardView in scenes/prehistoric_board_view.py. Its ground is a downward-looking crop of the same village background. The slab, knife, platter and four newly generated progressive carving states are independent sprites.

Pick up the flint knife, then swipe down through the three highlighted cut marks. Each completed swipe plays a short knife downstroke; a cut is awarded at impact, not on mouse-down or release. Pausing or focus loss cancels an unfinished stroke without awarding a cut. B or Back to Fire returns to the same hearth object, retaining cuts.

Four cooked slices are split into two pairs. Either pair can be dragged to the platter first; portion_mask persists which pair has been plated, so leaving and re-entering cannot duplicate servings. When both pairs are plated, clicking the platter returns to the village with the existing carry/guard-handoff state. Existing version-2 recipe snapshots without portion_mask infer the previously plated pairs from portions.

The updated tools/qa_prehistoric_cooking_v2.py verifies the full physical-input recipe and story route, explicit slab-click entry, invalid cuts/drops, timed knife impact, pause cancellation, first-cut station return/resume, 16:10 input and scaling, right pair first, plated-pair persistence, and continuation through the guard scene to Royal.


## Stable doneness materials 2026-11-09

The old raw/half/done mounted images each included independently drawn hardware and slightly different crop boundaries. The closeup now uses canonical raw_a mechanical textures for all side-A doneness values and raw_b mechanical textures for side B. The empty spit preserves the current half-turn orientation. Only explicit turn_45/90/135 animation states change mechanical frames. The left tip and shaft sections are invariant.

New stable_meat_a/b_raw/half/done.png sprites contain only meat, generated together in stable_meat_atlas.png and sliced with one shared registered crop. Their surface layers blend continuously with cooking progress; no wooden shaft, collar or crank is baked into these meat sprites. The station dimensions, fork-front occlusion, collar clearance, click-turn timing and carving-board flow are preserved.

The dedicated tools/qa_stable_roast_material.py compares every visible mechanical sprite's texture identity, position, scale, angle and alpha at 10 progress values on each side, including the old cutover thresholds, and checks readiness remains stationary until a clicked turn. The full physical-input cooking -> carving-board -> guard -> wakeup -> Royal regression also passed.
