#!/usr/bin/env python3
"""Re-skin the Neko_Aether Live2D rig with the Wardogs_Male character.

The rig (Aether.moc3: meshes, deformers, physics, parameters) is kept 100 %
untouched -- only Aether.4096/texture_00.png is repainted.  For every art mesh
we know its UV triangles (atlas) and where each vertex sits on the model canvas
in the rest pose (tools/data/aether_rest_geometry.json, exported once from the
moc with the Cubism Core, PawOff=1 / all other params default).  Each atlas
texel is therefore mapped to a canvas position, and the colour at that position
is taken from the Wardogs part stickers (parts/*.png) that have been placed on
the canvas (face, hair, torso, arms, eyes, brows, mouth).

Meshes that do not exist on this character (cat ears, earring, scarf, gold
emblem/shoulder pad, cape flaps, belt, cat paws) are left transparent.

    python3 tools/retexture_aether.py            # writes Neko_Aether/Aether.4096/texture_00.png
    python3 tools/retexture_aether.py --preview  # also writes preview/aether_*.png

Needs: numpy pillow scipy.
"""
import argparse, io, json, os, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from build_psd import key_magenta  # noqa: E402

TEX = os.path.join(ROOT, 'Neko_Aether', 'Aether.4096', 'texture_00.png')
GEOM = os.path.join(ROOT, 'tools', 'data', 'aether_rest_geometry.json')
REF_COMMIT = '9d1291a9b0d1f7f1979270aacb78bbcc9b2a9dc2'   # original Neko texture
AT = 4096

# ----------------------------------------------------------------- sources --
def load_part(name):
    im = key_magenta(Image.open(os.path.join(ROOT, 'parts', name + '.png')))
    im = im.crop(im.getchannel('A').getbbox())
    a = np.asarray(im).astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]                     # premultiply
    return a

class Src:
    """A sticker placed on the model canvas.

    (ax, ay) is a point in sticker pixels that lands on canvas point (cx, cy);
    sx / sy are canvas px per sticker px; mirror flips the sticker about the
    anchor column."""
    def __init__(self, img, anchor, canvas, sx, sy=None, mirror=False):
        self.img, self.ax, self.ay = img, anchor[0], anchor[1]
        self.cx, self.cy = canvas
        self.sx, self.sy = sx, sy or sx
        self.m = -1.0 if mirror else 1.0

    def uv(self, X, Y):
        return (self.ax + self.m * (X - self.cx) / self.sx,
                self.ay + (Y - self.cy) / self.sy)

    def sample(self, X, Y):
        """premultiplied RGBA, bilinear, transparent outside"""
        u, v = self.uv(X, Y)
        h, w = self.img.shape[:2]
        u -= 0.5; v -= 0.5
        x0 = np.floor(u).astype(int); y0 = np.floor(v).astype(int)
        fx = (u - x0)[:, None]; fy = (v - y0)[:, None]
        def g(xx, yy):
            ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
            out = np.zeros((len(xx), 4), np.float32)
            out[ok] = self.img[yy[ok], xx[ok]]
            return out
        return (g(x0, y0) * (1 - fx) * (1 - fy) + g(x0 + 1, y0) * fx * (1 - fy) +
                g(x0, y0 + 1) * (1 - fx) * fy + g(x0 + 1, y0 + 1) * fx * fy)

def over(layers):
    out = np.zeros_like(layers[0])
    for l in layers:
        out = l + out * (1 - l[:, 3:4])
    return out

def straight(p):
    a = p[:, 3:4]
    rgb = np.where(a > 1e-4, p[:, :3] / np.maximum(a, 1e-4), 0)
    return np.clip(rgb, 0, 1), a[:, 0]

def smooth(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1)

# -------------------------------------------------------------- layout ------
def build_sources():
    P = {n: load_part(n) for n in ['face_base', 'hair', 'eye', 'brow', 'mouth_open',
                                   'torso', 'arm']}
    S = {}
    # head: skull centre (229, 0) -> head3 top; ears/neck come along.  The rig's
    # head meshes (11 + back layer 15) lean a little to the left towards the jaw,
    # so the skull is sized/centred such that its whole silhouette stays inside
    # their union (checked numerically: 0 skull px outside).
    S['face'] = Src(P['face_base'], (229, 0), (800, 237), 1.48, 1.45)
    S['hair'] = Src(P['hair'], (217, 0), (800, 144), 1.68)
    S['torso'] = Src(P['torso'], (335, 0), (800, 1058), 0.91)
    # arms hang straight down at the sides (the rig's PawOff pose)
    S['armR'] = Src(P['arm'], (101, 0), (560, 1068), 0.64)
    S['armL'] = Src(P['arm'], (101, 0), (1040, 1068), 0.64, mirror=True)
    # eye sticker is the screen-right eye; the UV islands belong to the
    # screen-left eye (right eye = mirrored mesh; only the iris is a plain
    # translated copy, so everything is centred on the mesh centre x=664 to stay
    # symmetric) -> mirror the sticker.
    S['eye'] = Src(P['eye'], (244, 134), (664, 692), 0.36, mirror=True)
    S['brow'] = Src(P['brow'], (218, 91), (645, 575), 0.42, 0.27, mirror=True)
    S['mouth_open'] = Src(P['mouth_open'], (263, 266), (798.5, 840.5), 0.30, 0.21)
    return S

IRIS_C, IRIS_R = (244.0, 134.0), 121.0

# ---------------------------------------------------------------- painters --
# every painter gets X, Y (canvas px per texel) and ref (original atlas RGBA,
# straight 0..1) and returns straight rgb (N,3) and alpha (N,)
def P_src(*names):
    def f(S, X, Y, ref):
        return straight(over([S[n].sample(X, Y) for n in names]))
    return f

def P_none(S, X, Y, ref):
    return np.zeros((len(X), 3), np.float32), np.zeros(len(X), np.float32)

def lash_mask(S, X, Y, stroke):
    s = S['eye']; p = s.sample(X, Y); rgb, a = straight(p)
    u, v = s.uv(X, Y)
    d = np.hypot(u - IRIS_C[0], v - IRIS_C[1])
    lum = rgb @ np.array([0.3, 0.5, 0.2])
    dark = smooth(0.42 - lum, 0.0, 0.14)                # near-black ink only
    outside = smooth(d, IRIS_R + 1, IRIS_R + 5)
    in_stroke = (u > 420) & (v > 100)
    sel = in_stroke if stroke else ~in_stroke
    return rgb, a * dark * outside * sel

def P_lash(stroke):
    def f(S, X, Y, ref):
        rgb, a = lash_mask(S, X, Y, stroke)
        return rgb, a
    return f

def P_iris(S, X, Y, ref):
    s = S['eye']; rgb, a = straight(s.sample(X, Y))
    u, v = s.uv(X, Y)
    d = np.hypot(u - IRIS_C[0], v - IRIS_C[1])
    return rgb, a * (1 - smooth(d, IRIS_R - 2, IRIS_R + 1))

def P_eyewhite(S, X, Y, ref):
    cx, cy, rx, ry = 664.0, 694.0, 55.0, 50.0
    e = np.hypot((X - cx) / rx, (Y - cy) / ry)
    a = 1 - smooth(e, 0.94, 1.0)
    t = smooth((Y - (cy - ry)) / (2 * ry), 0.0, 0.55)[:, None]
    top, bot = np.array([0.74, 0.62, 0.64]), np.array([0.90, 0.84, 0.84])
    return top * (1 - t) + bot * t, a.astype(np.float32)

def P_brow(S, X, Y, ref):
    return straight(S['brow'].sample(X, Y))

def P_lip(S, X, Y, ref):
    """skin patch (colour of the baked face underneath) with a dark lip line
    wherever the original art had its red line"""
    rgb, a = straight(over([S['face'].sample(X, Y)]))
    skin = np.array([0.80, 0.56, 0.40])
    rgb = np.where(a[:, None] > 0.5, rgb, skin)
    red = smooth(ref[:, 0] - ref[:, 1], 0.24, 0.40)[:, None]
    ink = np.array([0.17, 0.09, 0.08])
    rgb = rgb * (1 - red) + ink * red
    return rgb, ref[:, 3]

def P_mouth_in(S, X, Y, ref):
    rgb, a = straight(S['mouth_open'].sample(X, Y))
    dark = np.array([0.50, 0.10, 0.12])
    rgb = rgb * a[:, None] + dark * (1 - a[:, None])
    return rgb, ref[:, 3]

HAIR_PIECES = {8: 'ArtMesh5', 10: 'ArtMesh10', 60: 'ArtMesh6',
               39: 'ArtMesh28', 40: 'ArtMesh27', 41: 'ArtMesh26',
               42: 'ArtMesh29', 43: 'ArtMesh30', 44: 'ArtMesh31',
               45: 'ArtMesh40', 46: 'ArtMesh41', 47: 'ArtMesh42', 48: 'ArtMesh43'}

PAINT = {}
for i in HAIR_PIECES: PAINT[i] = P_src('hair')
PAINT.update({
    11: P_src('face', 'hair'),          # head3: face skin, hair baked on top
    14: P_src('face'),                  # neck stub
    15: P_src('face', 'hair'),          # back layer: ears + scalp hair
    29: P_src('torso', 'armR', 'armL'), # torso with both arms hanging down
    7: P_eyewhite, 6: P_iris,
    58: P_lash(False), 32: P_lash(True),
    59: P_brow,
    2: P_lip, 3: P_lip, 4: P_mouth_in,
})
# everything not listed stays transparent: ears 12/13, earring 9, scarf 0/1/34-37,
# shoulder 38, belt 28, sleeves 30/31 (arms are baked into 29), thin crease lines
# 5/33/57, cat paws 16-27 (hidden by PawOff anyway).

# --------------------------------------------------------------- baking -----
def reference_atlas():
    # the working texture is overwritten by this script -> read the original
    # Neko texture from git history (falls back to the file on disk)
    try:
        raw = subprocess.check_output(['git', 'show', REF_COMMIT + ':Neko_Aether/Aether.4096/texture_00.png'],
                                      cwd=ROOT)
        return Image.open(io.BytesIO(raw)).convert('RGBA')
    except Exception:
        return Image.open(TEX).convert('RGBA')

def raster(dr):
    """texel grid (px,py ints) + canvas position for every texel of a mesh"""
    uv = np.array(dr['uv'], np.float64).reshape(-1, 2)
    pos = np.array(dr['pos'], np.float64).reshape(-1, 2)
    idx = np.array(dr['idx']).reshape(-1, 3)
    tx = uv[:, 0] * AT; ty = (1 - uv[:, 1]) * AT
    PX, PY, CX, CY = [], [], [], []
    for a, b, c in idx:
        x0, x1 = int(np.floor(min(tx[[a, b, c]]))) - 2, int(np.ceil(max(tx[[a, b, c]]))) + 2
        y0, y1 = int(np.floor(min(ty[[a, b, c]]))) - 2, int(np.ceil(max(ty[[a, b, c]]))) + 2
        gx, gy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        gx = gx.ravel(); gy = gy.ravel()
        px, py = gx + 0.5, gy + 0.5
        den = (ty[b] - ty[c]) * (tx[a] - tx[c]) + (tx[c] - tx[b]) * (ty[a] - ty[c])
        if abs(den) < 1e-9: continue
        l1 = ((ty[b] - ty[c]) * (px - tx[c]) + (tx[c] - tx[b]) * (py - ty[c])) / den
        l2 = ((ty[c] - ty[a]) * (px - tx[c]) + (tx[a] - tx[c]) * (py - ty[c])) / den
        l3 = 1 - l1 - l2
        eps = 1.2 / max(1.0, np.sqrt(abs(den)))
        ok = (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps) & (gx >= 0) & (gx < AT) & (gy >= 0) & (gy < AT)
        PX.append(gx[ok]); PY.append(gy[ok])
        CX.append((l1 * pos[a, 0] + l2 * pos[b, 0] + l3 * pos[c, 0])[ok])
        CY.append((l1 * pos[a, 1] + l2 * pos[b, 1] + l3 * pos[c, 1])[ok])
    return (np.concatenate(PX), np.concatenate(PY), np.concatenate(CX), np.concatenate(CY))

def bake():
    geom = json.load(open(GEOM))
    ref = np.asarray(reference_atlas()).astype(np.float32) / 255.0
    S = build_sources()
    out = np.zeros((AT, AT, 4), np.float32)
    done = {}
    for dr in geom['d']:
        i = dr['i']
        if i not in PAINT: continue
        key = tuple(np.round(dr['uv'], 5))
        if key in done: continue
        done[key] = i
        px, py, cx, cy = raster(dr)
        r = ref[py, px]
        rgb, a = PAINT[i](S, cx, cy, r)
        out[py, px, :3] = rgb
        out[py, px, 3] = a
    return out

def finish(out):
    a = out[..., 3]
    rgb = out[..., :3].copy()
    # bleed colour 4 px into transparent texels so bilinear filtering never
    # pulls black in at mesh borders
    solid = a > 0.02
    dist, (iy, ix) = ndi.distance_transform_edt(~solid, return_indices=True)
    near = (~solid) & (dist <= 4)
    rgb[near] = rgb[iy[near], ix[near]]
    res = np.dstack([rgb, a])
    return Image.fromarray((np.clip(res, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=TEX)
    args = ap.parse_args()
    img = finish(bake())
    img.save(args.out, optimize=True)
    print('wrote', args.out)

if __name__ == '__main__':
    main()
