# Wardogs_Male — 2D model

Chibi military character, rigged as a **texture-layer** model (not a Cubism
`.moc3`). Art is generated from chroma-keyed part stickers in `parts/`.

## Layout

```
parts/*.png                 source stickers (magenta key + baked checkerboard)
Wardogs_Male/
  wardogs_male.psd          layered PSD, 15 layers on a 1920x1080 canvas
  wardogs_male.4096/
    texture_00.png          THE texture — all 15 layers packed into one 4096² atlas
    atlas_map.json          per-layer atlas rect + canvas placement + rig pivots
  wardogs_male.model3.json  manifest (textures, physics, expressions, parameter groups)
  wardogs_male.cdi3.json    45 parameters + part names
  wardogs_male.physics3.json
  Expression/*.exp3.json    9 expressions
  wardogs_male_flat.png     merged reference render (built from the atlas)
viewer/index.html           interactive rig viewer (canvas, no runtime deps)
viewer/wardogs_model_standalone.html   single-file offline build
```

## atlas_map.json

Each layer carries two rectangles:

| field | meaning |
|---|---|
| `x, y, w, h` | where the part sits **in the 4096² atlas** |
| `dx, dy` | where the part belongs **on the 1920×1080 canvas** |

`dx/dy` is required: the parts are cut to their alpha bbox when packed into the
atlas, so the atlas rect alone does not say where the art was composed. The
pivots in the same file are all in canvas space.

`tools/build_psd.py` writes `dx/dy` on every build. `tools/atlas_placement.py`
back-fills them into an atlas built before that change.

## Pivots

`head` is the head centre; **`neck` (960, 636) is the rotation joint** — the head
must turn about the neck or it swings off the shoulders. `shoL`/`shoR` are
shoulders, `eyeL/R`, `browL/R`, `mouth` the face features, `body` the torso.

## Naming

The character faces the viewer, so **his right side is screen-left**.
`ArmR` is therefore on `shoL`. `parts/arm.png` is a **right** arm (back of hand
to camera, thumb pointing medially), so it is placed unmirrored at `shoL` and
the mirrored copy becomes `ArmL` at `shoR`.

## There is no `.moc3`

`model3.json` has a `Moc` field but the file does not exist in this repo, and
it cannot be produced without Cubism Editor. The model is **not** loadable by a
real Cubism runtime. `viewer/index.html` draws it directly from the atlas, so
the dangling `Moc` reference is inert here — but anything that hands this model
to Cubism will fail on it.

`ParamHandL/R` and `ParamFingerL/R` are declared in `cdi3.json` but not
articulated: a flat arm texture has no separate hand mesh to curl.

## Build

```bash
pip install numpy pillow psd-tools
python3 tools/build_psd.py        # parts/ -> psd + atlas + atlas_map + flat
python3 tools/build_standalone.py # viewer -> single-file html
```

`tools/build_psd.py` regenerates the art deterministically. Two things it gets
right that are easy to break:

- **the magenta test needs a brightness gate.** The key is a bright magenta
  (~253,0,248), but some art is a *dark* maroon (the `eye_smile` arc is
  (39,6,31)) that also satisfies `r>g+18 & b>g+18`. Without `r>90` the keyer
  eats the artwork and leaves a 4-pixel smudge.
- **de-fringe after keying.** A hard key leaves a 1px magenta halo; erode one
  pixel, then fully neutralise any remaining spill.

## Preview

```bash
npm i @napi-rs/canvas
node tools/render_preview.js        # writes preview/*.png
python3 tools/contact_sheet.py      # builds the contact sheets
```

`tools/render_preview.js` executes the real rendering code out of
`viewer/index.html` (via `vm`) against a headless canvas, so the stills come
from the same code path the browser runs. Serve the repo root and open
`/viewer/` for the interactive version.
