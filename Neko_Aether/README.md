# Neko_Aether — re-skinned with the Wardogs_Male character

The rig (`Aether.moc3`, physics, parameters, VTube Studio file) is the original
Neko_Aether one. Only the texture was replaced:

* `Aether.4096/texture_00.png` — repainted with the Wardogs_Male parts
  (`tools/retexture_aether.py`, reads `parts/*.png`).
* `Aether.moc3` — one byte-level change: the default of `ParamPawOff` is now `1`
  (was `0`), so the model starts with both arms hanging straight down at the
  sides and no raised cat paws. Nothing else in the file was touched.

Preview: `preview_wardogs.png` (default pose).

Meshes the new character has no equivalent for (cat ears, earring, scarf,
gold emblem / shoulder pad, cape flaps, belt, cat paws) are transparent in the
atlas. The arms are painted into the torso mesh, so they don't swing
independently (the original sleeve meshes sit *under* the torso in draw order).

## Rebuild

```bash
pip install numpy pillow scipy
python3 tools/retexture_aether.py
```

`tools/data/aether_rest_geometry.json` holds the rest-pose mesh geometry
(UV + canvas position of every art mesh) that the script needs; it was exported
once from the moc with the Live2D Cubism Core. The original Neko texture is read
from git history (commit `9d1291a`).

To restore the original Neko arms-up default: set the `ParamPawOff` default back
to `0` (float at file offset `31184` of `Aether.moc3`) and check out the old texture.
