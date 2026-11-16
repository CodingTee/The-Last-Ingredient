> Updated route (2026-11-05): the finished dish is eaten at the NEW kitchen table. Only afterward can the player return through the left doorway for the living-room box/cards. See KITCHEN_DINING_UPDATE.md for the current route and map clarity details.

# Scene 7 modern cooking — completed step audit (2026-11-04)

This update covers the modern kitchen recipe and its handoff through Scene 8 into Scene 9. It does not claim completion of the prehistoric, Royal or future cooking chapters.

| Step | Implemented operation | Verification |
|---|---|---|
| Fill | Click tap to start/stop filling; partial water level retained | Pause, focus loss and departure/resume tested |
| Move pot | Pick up filled pot from counter, click left burner; animated placement commits on arrival | Double input during movement rejected |
| Boil | Left knob independently toggles flame and heating | Boiling is required before adding noodles |
| Add noodles | Select noodle sprite, click actual pot/contents mask | Noodles appear after placement animation |
| Loosen | Chopsticks move in a small stirring path; noodle surface responds | Optional action; no new perfect-score requirement |
| Heat skillet | Separate right knob, flame and pan preheat | Turning off the right burner stops egg cooking |
| Oil and egg | Oil sprite pours a stream; egg action follows oil/preheat checks | Cold/oilless pan rejected; animated state commit |
| Shell memory | Half-shell targets only the visible fragment; fragment removed on completion | Existing family memory retained |
| Shell disposal | Used half-shell returns to saucer separately | Used shell cannot be picked up again |
| Move to serving | Food cooked, shell disposed, both burners off; click bowl | No button bypass |
| Broth | Ladle > actual pot content mask > actual bowl mask | Held golden broth visible; transfer tracked once |
| Noodles | Chopsticks > cooked noodle sprite > bowl | Held noodles visible; independent transfer |
| Egg | Spatula > fried egg sprite > bowl | Held egg visible; independent transfer |
| Serve | Click completed bowl; narration then fade to dining room | No Scene 7 card choice remains |
| Midnight cards | Scene 8 owns box inspection and all three cards | Crown/Gear inspectable but locked; Beast confirmed once |
| Continue | Finish selection narration, fade, instantiate Scene 9 once | Actual Scene 9 initialization and rendering tested |

Controls: click item then target; right-click returns held item; B or Back to kitchen leaves the workstation. Progress remains in the active Scene 7 instance, not a disk save. Cooking timers pause while exploring. A committed short movement finishes before normal workstation departure is allowed. Focus loss pauses the workstation and stops tap/held selection.

Picking uses each drawn sprite's alpha and draw order. The tap and empty burner are parts of the background and have registered control regions. UI buttons use their displayed rectangles. Sources and bowls no longer use broad left/right counter rectangles. Ingredients layered over a bowl resolve to that bowl, not back to the pot.

Knife and cutting board remain inspectable prep props; this soup does not require chopping. Cooking still uses automatic time progression under the appropriate active burner; no arbitrary temperature test, free-form inventory, new story branch or perfect score was added.

The same generated meal sprite is used in the kitchen, the dining-room world view and the Scene 8 tabletop. A new transparent golden broth PNG replaces blue water in the serving stage. Original generated images remain in assets/Scene 7/sources.

Validation: tools/verify_scene7_steps.py. Uses an actual hidden Arcade window, framebuffer screenshots and physical-to-virtual input mapping. Includes 16:9 and 16:10 picking, pause-menu clicks, cancellation, wrong targets, state gates, resuming, locked cards and the actual Scene 8/9 transition. The other two Scene 7 verification entry points delegate to this suite.

Backup: backups/scene7_step_polish_20261104. Prior independent-controller backup also retained.

Changed runtime files: scenes/scene_7_interaction.py, scenes/scene_7_sprites.py, scenes/scene_7_kitchen_view.py, scenes/scene_8_view.py. New asset: assets/Scene 7/sprites/broth_surface.png, also registered in manifest.json.
