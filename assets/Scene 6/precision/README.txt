Scene 6 precision environment update

Runtime: scenes/scene_6_precision.py, loaded by HomeKitchenView.
Assets: assets/Scene 6/precision (RGBA silhouettes, contours, additive light passes, manifest).
Independent registered state images: assets/Scene 6/states/*_only.png.
Generated source plates: *_only_generated.png; these are references, not directly overlaid at runtime.
Original Dark/Light backgrounds remain unchanged.
Backup: assets/Scene 6/backup_precision_20261019.

Changes:
- Traced 14 object masks against native 1678 x 937 coordinates, including furniture legs/gaps.
- Cutouts and contours share one alpha mask and native crop rectangle; no stretch.
- Root depth uses Player FEET_OFFSET + collision baseline consistently.
- Interactive target selection shared by prompt and E handler; nearest eligible target wins.
- Contours participate in depth sorting, so the foreground player can occlude them.
- Four independent additive light passes, original window geometry, isolated lamp emitters.
- Existing smooth intensity transitions preserved; lower-left corridor remains in base background.
- Occluding furniture receives matching masked light passes instead of dark patches.
- Standing from sofa places player outside furniture colliders.

Verification:
python tools/verify_scene6_precision.py
Actual Arcade GPU render: 16 combinations + front/behind furniture + sitting.
Assertions: 6 proximity targets, 8 light/window toggles, no electric emitter contribution from window passes,
and safe stand-up position. Compiles successfully. No full story playthrough performed.

Rebuild order (Pillow, numpy, OpenCV required):
python tools/scene6_trace_assets.py
python tools/scene6_refine_edges.py
python tools/scene6_build_light_passes.py

This is a 2D registered-layer renderer, not a 3D physically based lighting simulation.

2026-10-19 revision 2: Removed hard circular moonlight suppression around lamp shades. Suppression now follows lamp surfaces with feathered edges. Retraced vanity, coffee table, dining set incl. narrow legs and negative spaces. Run tools/scene6_retrace_furniture_v2.py AFTER initial trace/refine and BEFORE scene6_build_light_passes.py. QA rerun: 29 rendered states, 16 combinations and interaction checks passed.

2026-10-20: New transparent coffee table baked consistently into all background/light plates; native replacement alpha reused for cutout/outline. Rebuild hooks preserve replacement mask. After scene6_refine_edges.py and scene6_retrace_furniture_v2.py, run scene6_refine_vanity_plant.py and then scene6_build_light_passes.py. Vanity upper-right props restored; sofa-arm contamination removed from plant mask.
