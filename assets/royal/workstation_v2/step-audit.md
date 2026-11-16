# Royal cooking update — 2026-11-04

Scope: the current integrated Royal chapter (c. 1910), from kitchen preparation through serving and the transition into Future Lab. The future evidence/ending systems were not modified in this update.

| Step | Current implementation and checks |
|---|---|
| Nearby workstation | Prep/range entry requires the walker to be nearby. Remote entry rejected. |
| Cutting | Preserved the native onion/carrot sprite sequences and current six actions each (trimming included). Counts change when the knife contacts the board, not on press. Added the previously generated board sprite. |
| Pouring | Hold jug to pour, release to stop. Overfill is recoverable by draining. Pause, focus loss, resize and leaving clear held input. |
| Ingredients | Select each onion/carrot/barley sprite, then click the actual pot alpha. A short movement commits the addition on arrival. Duplicate materials are not counted twice. |
| Heating | Coal and air control retain thermal inertia. Boiling is required before moving the same pot. Invalid drop restores the left position; valid right-hob drop preserves temperature. |
| Simmering | Circular stirring, tenderness, consistency inspection, dilution and coal controls retained. Thick soup is recoverable; cooking mistakes do not choose an ending. |
| Map return | Fill, boil, simmer and final serving stations can return to the same kitchen and resume. The Cooking instance is preserved. Re-showing the view no longer resets the recipe. Cooking timers pause in the map. |
| Wash hands | Added a separate first-person washstand. Hold the jug to rinse the hands; progress survives interruption. Only completion enables return. Girl remains in the separate dining room. |
| Empty kitchen | Existing absence/clink/return story retained. No hidden failure timer or visitor reveal added. |
| Final salt | Select jar, click the pot; animated movement and salt feedback complete before the state changes. |
| Serving | Select ladle, load from the pot, hold over the bowl. Release stops filling; partial progress remains. A full bowl stops the pour and can be clicked to enter the dining-room story. |
| Chapter handoff | Existing fixed girl/ring/attendants/06:00 narrative retained. Actual FutureLabView initialized and rendered after Royal completion. |

New visuals: generated washstand background and basin; existing first-person hands adapted by built-in image generation to white chef cuffs. Forearms are occluded by a front-rim strip from the same basin texture. Prep board reuses the previously generated cutting-board sprite. All textures retain native aspect ratios. Source art and prompts are supplied alongside the report.

Validation: `tools/verify_royal_workstation.py`, an actual hidden Arcade window with framebuffer captures and physical input events. Covers step ordering, contact-time cuts, overfill, pause/cancel/focus, map return, view re-show, pot drop recovery, stirring, soup adjustment, washing interruption, salt animation, partial ladling, both 16:10 and 16:9 input mappings, pause-menu clicks and Future Lab initialization/render. This is not a manual playthrough of the complete game or a claim that the future chapter is finished.

Runtime files: `scenes/royal_view.py`, new `scenes/royal_workstation.py`. New/reused art: `assets/royal/workstation_v2/`. Backup: `backups/royal_workstation_20261104/royal_view.py`.
