Latest update: 2026-11-05 — see KITCHEN_DINING_UPDATE.md.
Kitchen meal now precedes living-room box/cards.
Full-map clarity/camera update and independent dining furniture are installed.

Scene 7 generated sprite implementation — updated 2026-11-04

21 separate transparent ingredient/tool/food-state sprites + 4 scene backgrounds.
Generated with built-in image generation. Original images retained in sources/.
See INDEPENDENT_INTERACTIONS.md for the current step audit and controls.

Click an item, then its target. Right-click returns the held item.
B / Back to kitchen leaves the workstation and retains in-memory progress.
Faucet: click to start/stop. Filled pot: select, then click the left burner.
LEFT and RIGHT knobs toggle independently; right skillet must be warm and oiled.
Half-shell removes the fragment, then returns to its saucer.
After cooking, turn both burners off and click the bowl to use the serving counter.
Ladle > pot > bowl; chopsticks > noodles > bowl; spatula > egg > bowl.
Click the complete bowl to return to the dining room. Scene 8 owns the single tarot choice.

Runtime: scene_7_interaction.py, scene_7_sprites.py, scene_7_kitchen_view.py;
Scene 8 uses the same completed-bowl/chopsticks sprite.
Native texture aspect ratios preserved. Alpha-based item/source/bowl picking.
Particles, water stream, flame and steam remain procedural animated effects.
Knife/board are inspectable props; this recipe needs no chopping.

Verification: python tools/verify_scene7_steps.py
Existing verify_scene7_sprites.py and verify_scene7_independent.py delegate to it.
Checked fill/pause/focus, pot movement, independent burners, oil/heat gates,
noodles/stirring, shell memory/disposal, individual animated serving transfers,
wrong-target handling, departure/resume, 16:9/16:10 picking and pause menu,
Scene 8 locked card inspection, Beast confirmation and actual Scene 9 render.
This does not claim a manual playthrough of the entire game or other eras.

Backup: backups/scene7_step_polish_20261104.
Asset catalogue: manifest.json. Generation prompts: generation-prompts.json
plus broth-generation-prompt.txt for the newly generated golden broth.
