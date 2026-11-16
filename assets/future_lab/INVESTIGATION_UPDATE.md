# Future investigation and branch audit — 2026-11-05

This round repairs the future laboratory investigation and its branch entry controls. Existing Nutrient Block and HE-only cooking implementations were retained and exercised through actual inputs.

| Area | Changes / verified behavior |
|---|---|
| Evidence | Opening, stepping away, clicking outside or right-clicking does not record a comparison. Each instrument has observation/comparison pages and an explicit Record action. Repeated records cannot increase the count. |
| Material relationship | The salt investigation distinguishes the sealed white sample from the blue liquid precursor and explains their connection through analysis. Archive text includes later synthesis/distribution rather than making future material depend exclusively on an ancient sample. |
| Understanding | Three recorded comparisons unlock a four-page explanation. All pages plus the final confirmation are required. A navigation arrow on the last page does not confirm. Escape leaves the explanation unconfirmed; R reopens review. |
| Deliberate choice | Waiting, closing a panel or finishing food does not select an ending. Abort is rejected before full understanding. Launch preparation remains available before or after understanding. |
| Synthesizer | Restored a menu for ordinary practice and, after Launch, Nutrient Block preparation. Ordinary food does not satisfy the transit-nutrition flag. The ordinary demonstration now uses existing generated cookware/food PNGs instead of primitive noodle/egg shapes. |
| Transit ration | Selected recipe, current-body scan, ordered ingredient transfers, mixing, synthesis, protective-hood delay, collection and actual eating were verified. Merely preparing or eating the ration does not perform a jump. |
| Physical departure | Requires preparation, secured equipment case, capsule entry and explicit activation. Entry and case animations have interlocks. Tested actual arrival in BadEndingView B03. |
| Abort entry | Explicit informed Abort sets the existing H01 confirmation once and begins H02, avoiding a second duplicate Abort choice. Existing HE-only cooking constructor still requires that confirmation. |
| HE soup | Verified ordinary ingredients, water heating, stirring noodles, separate egg pan/cracking/frying, broth/noodles/egg assembly, and choosing to keep the imperfect presentation. |
| Empty-handed return | Verified carrying the bowl, the physical-items warning, placing the bowl on the future table, returning empty-handed, and arrival in H07. The future bowl stays in the future scene. |
| Pause / focus | Added focus-loss cancellation to the lab, optional practice station and HE cooking scene. Active hands/stirring/held selection stop; paused actions cannot advance recipe state. |

New runtime module: `scenes/future_investigation_ui.py`.
Changed runtime files: `scenes/future_view.py`, `scenes/future_cooking_view.py`, `scenes/he_cooking_scene.py`.
Backup: `backups/future_investigation_20261105/`.

Validation: `tools/verify_future_branches.py` uses a hidden Arcade window, real input handlers and framebuffer captures. It verifies evidence de-duplication, incomplete explanation/Abort rejection, navigation-only behavior, ordinary food isolation, both Launch knowledge states, full transit preparation and activation, informed Abort, HE soup and bowl placement. Both 1280x800 and 1280x720 windows are exercised.

The regression ends at B03 on the physical branch and H07 on the return branch. It does not claim a manual playthrough of every remaining ending scene, achievement persistence or all Future Retry paths. No achievement was deliberately unlocked by this test. No new image generation was needed in this round; existing generated Scene 7 / future assets were reused.
