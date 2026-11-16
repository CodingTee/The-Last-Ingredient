# Royal princess v2

Generated with built-in imagegen, matching the current chibi chef rather than the older storybook atlas.

- princess_standing_ring.png: original transparent standing sprite.
- princess_seated_ring.png: original transparent seated sprite; no chair, for compositing over the dining chair.
- *_trimmed.png: alpha-bounds crops for aspect-preserving sprite loading.
- ring_hands_closeup.png: narrative insert for the mother's ring dialogue.
- proportion_preview.jpg: current chef at 500 px versus princess at 340 px, with aligned feet; seated pose shown separately.
- prompts.json: complete prompts and style reference.

Integration: use independent seated sprite rather than cropping the standing sprite. Establish standing foot anchors before setting princess height to 0.68 times chef height at equal depth. Chair seat and table foreground determine seated placement. Preserve the existing collapse sprite until a matching replacement is made. These assets are not yet installed into the Desktop ISE game.

Earlier storybook explorations are retained under storybook_drafts and are not the selected final assets.
