# Onion cutting states

Five transparent PNG files, all700x420, in sequence:
0 whole;1 1:4;2 1:1:3;3 1:1:1:2;4 1:1:1:1:1.
This is FOUR knife actions plus the initial uncut frame.

Use the entire common canvas; do not independently auto-trim each texture at runtime or resize by each state's width. The sequence uses the same visible onion diameter, baseline and right anchor. Switch state on knife impact, then lift the knife. Game integration is not included in this asset export.

Artwork: built-in image_gen. Source sheet and exact prompts are retained in the project assets; export only crops/uniformly scales/positions the generated frames.
