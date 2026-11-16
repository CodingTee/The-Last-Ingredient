# Kitchen map and dining update — 2026-11-05

Implemented flow: cook and assemble soup → carry it to the small kitchen table → sit and eat opposite the empty chair → return through the left kitchen doorway → discover the box in the living room → inspect the cards in Scene 8 → proceed to Scene 9.

The kitchen table is an independent generated transparent furniture sprite with two chairs, not painted into the map. It has foot-contact collision footprints and root-based character depth ordering. The upper chair is behind the seated character; the table surface/front is a separate runtime texture layer in front of the character. Existing front-facing seated character artwork is reused.

The bowl is carried before sitting, appears on the kitchen table while eating, and becomes an empty bowl afterward. There is no duplicate full meal in the living room. Scene 8's standalone default behavior is preserved, while the route from Scene 7 now passes meal_finished=True and starts near the kitchen doorway with post-meal dialogue. Cards remain exclusive to Scene 8.

Clarity change concerns the full-room kitchen map, NOT the first-person cooking backgrounds. The map was conservatively regenerated to clarify cabinet edges, tiles and hardware while retaining its layout. The generated image remains native 1678 x 937: this is NOT a native 4K claim. The world camera now spans 937 world pixels vertically instead of 720, reducing enlargement by about 23%. At a 1080p 16:9 viewport, one source-map pixel covers roughly 1.15 screen pixels rather than 1.5. Screen scaling remains uniform. At 16:10, horizontal camera tracking exposes the sides without stretching the map.

Loose map ingredient/tool sprites receive a subdued warm tint to match the room lighting. First-person cooking sprites and backgrounds retain their previous rendering. The original kitchen background is preserved; kitchen_refined.png is preferred at runtime.

Validation:
- Full six-step cooking suite passes.
- Table collision blocks walking through its footprint.
- Seated, character-in-front and character-behind framebuffers rendered and inspected.
- Kitchen meal must finish before the living-room return is available.
- No duplicate meal appears on both table and hands.
- Post-meal Scene 8 state confirmed, locked cards checked, and Scene 9 initialized/rendered.
- 16:9 and 16:10 display/input checks pass.

Main files: scenes/scene_7_dining.py, scenes/scene_7_sprites.py, scenes/scene_7_kitchen_view.py, scenes/scene_8_view.py.
Verification: tools/verify_scene7_steps.py and tools/render_kitchen_dining.py.
Backup: backups/scene7_kitchen_dining_20261105.

Generation: built-in image_gen, no CLI/API fallback. Exact prompts are in generation-prompts.json. Newly generated assets are saved beside these notes and in the project asset folders.
