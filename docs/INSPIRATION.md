# Inspiration research

Researched 2026-11-10 from primary product and manual sources:

- Reallusion Character Creator: https://www.reallusion.com/character-creator/
- Character Creator 5 HD characters: https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/CC5-HD-Characters.htm
- Quick guide: https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/04-Quick-Guide/Quick-Guide-for-Creating-Characters.htm

The product's core workflow emphasizes adjustable character shapes, skin and hair appearance, outfits and posing. CC5 also supports HD character detail and production pipelines far outside this kata.

Persona Forge deliberately keeps only a learnable loop: choose a stylized archetype, change proportions, color the character, choose a static pose and export. The browser implementation creates its own ellipsoid-based geometry and original studio design; it neither reproduces proprietary character assets nor attempts source-product parity. Actual OBJ export makes the small study usable outside the app, with explicit caveats about disconnected topology, RGB vertex-color compatibility and the lack of a rig.
