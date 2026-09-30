#!/usr/bin/env python3
"""Assemble Wardogs_Male Live2D art from generated part stickers.

Chroma-keys magenta part PNGs (parts/), composes them into named layers on a
1920x1080 canvas (layout matched to the reference concept), then exports:
  - Wardogs_Male/wardogs_male.psd          layered Photoshop file (разрезка)
  - Wardogs_Male/wardogs_male.4096/texture_00.png + atlas_map.json (with pivots)
  - Wardogs_Male/wardogs_male_flat.png     merged preview
"""
import json, os
import numpy as np
from PIL import Image

W, H = 1920, 1080
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PARTS = os.path.join(ROOT, 'parts')
OUT = os.path.join(ROOT, 'Wardogs_Male')

def key_magenta(im):
    """Remove magenta chroma AND baked-in checkerboard backgrounds via
    flood-fill from the image borders through background-like pixels.

    The key colour is a *bright* magenta (~253,0,248). Some artwork is a *dark*
    maroon that also satisfies (r>g+18)&(b>g+18) -- the eye_smile arc is
    (39,6,31) -- so the magenta test needs a brightness gate, otherwise the
    keyer eats the art and leaves a 4px smudge.
    """
    from collections import deque
    im = im.convert('RGBA')
    a = np.asarray(im).astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    magenta = (r > g + 18) & (b > g + 18) & (r > 90)     # bright key only
    grey = (np.abs(r - g) < 16) & (np.abs(g - b) < 16) & (r >= 100)  # light checker
    bglike = magenta | grey
    hgt, wid = bglike.shape
    seen = np.zeros_like(bglike)
    dq = deque()
    for x in range(wid):
        for y in (0, hgt - 1):
            if bglike[y, x]: dq.append((y, x)); seen[y, x] = 1
    for y in range(hgt):
        for x in (0, wid - 1):
            if bglike[y, x] and not seen[y, x]: dq.append((y, x)); seen[y, x] = 1
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
            if 0 <= ny < hgt and 0 <= nx < wid and not seen[ny, nx] and bglike[ny, nx]:
                seen[ny, nx] = 1
                dq.append((ny, nx))
    a[..., 3] = np.where(seen, 0, a[..., 3])
    # keep only the connected component containing the image center
    # (drops stray fringe pixels that would corrupt the bbox)
    keep = a[..., 3] > 0
    if keep.any():
        cy0, cx0 = hgt // 2, wid // 2
        ys, xs = np.nonzero(keep)
        i = np.argmin((ys - cy0) ** 2 + (xs - cx0) ** 2)
        seed = (int(ys[i]), int(xs[i]))
        comp = np.zeros_like(keep)
        dq = deque([seed]); comp[seed] = 1
        while dq:
            y, x = dq.popleft()
            for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
                if 0 <= ny < hgt and 0 <= nx < wid and keep[ny, nx] and not comp[ny, nx]:
                    comp[ny, nx] = 1
                    dq.append((ny, nx))
        a[..., 3] = np.where(comp, a[..., 3], 0)
    # The key leaves a 1px magenta halo where the antialiased edge blended
    # into the background; erode it away, then fully neutralise any spill.
    m = a[..., 3] > 0
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    a[..., 3] = np.where(e, a[..., 3], 0)
    spill = np.minimum(a[..., 0], a[..., 2]) - a[..., 1]
    cut = np.where(spill > 0, spill, 0).astype(np.int32)
    a[..., 0] -= cut
    a[..., 2] -= cut
    np.clip(a[..., :3], 0, 255, out=a[..., :3])
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

def load(name):
    return key_magenta(Image.open(os.path.join(PARTS, name + '.png')))

def fit(im, width=None, height=None):
    bb = im.getchannel('A').getbbox()
    if bb: im = im.crop(bb)
    if width:
        s = width / im.width
        im = im.resize((width, max(1, int(im.height * s))), Image.LANCZOS)
    elif height:
        s = height / im.height
        im = im.resize((max(1, int(im.width * s)), height), Image.LANCZOS)
    return im

def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def place(canvas, im, cx, cy, mirror=False):
    if mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    x = int(cx - im.width / 2); y = int(cy - im.height / 2)
    canvas.alpha_composite(im, (x, y))

# ---------------- layout (matched to wardogs_male_chibi_01.png proportions) ----
HEAD = (960, 438)
EYE_L, EYE_R = (903, 454), (1017, 454)
BROW_L, BROW_R = (901, 406), (1019, 406)
MOUTH = (960, 532)
SHO_L, SHO_R = (775, 660), (1145, 660)
BODY_PIV = (960, 1010)

def build():
    P = {n: load(n) for n in ['face_base', 'hair', 'eye', 'brow', 'mouth_closed',
                             'mouth_open', 'eye_closed', 'eye_smile', 'torso', 'arm']}
    L = {}

    im = layer(); place(im, fit(P['torso'], width=470), 960, 898); L['Body'] = im

    # arm.png is the character's RIGHT arm (back of hand to camera, thumb
    # pointing medially). The character faces us, so his right side is screen
    # LEFT (SHO_L) and the mirrored copy is the left arm on SHO_R.
    im = layer(); place(im, fit(P['arm'], height=330), SHO_L[0], 815); L['ArmR'] = im
    im = layer(); place(im, fit(P['arm'], height=330), SHO_R[0], 815, mirror=True); L['ArmL'] = im

    im = layer(); place(im, fit(P['face_base'], width=340), *HEAD); L['Face'] = im

    im = layer(); place(im, fit(P['eye'], width=80), *EYE_L, mirror=True); L['EyeL'] = im
    im = layer(); place(im, fit(P['eye'], width=80), *EYE_R); L['EyeR'] = im

    im = layer(); place(im, fit(P['eye_closed'], width=80), *EYE_L, mirror=True); L['EyeCloseL'] = im
    im = layer(); place(im, fit(P['eye_closed'], width=80), *EYE_R); L['EyeCloseR'] = im

    im = layer(); place(im, fit(P['eye_smile'], width=80), *EYE_L, mirror=True); L['EyeSmileL'] = im
    im = layer(); place(im, fit(P['eye_smile'], width=80), *EYE_R); L['EyeSmileR'] = im

    # generated brow slopes down-left => inner-low for screen-RIGHT; mirror for left
    im = layer(); place(im, fit(P['brow'], width=95), *BROW_L, mirror=True); L['BrowL'] = im
    im = layer(); place(im, fit(P['brow'], width=95), *BROW_R); L['BrowR'] = im

    im = layer(); place(im, fit(P['mouth_closed'], width=72), *MOUTH); L['Mouth'] = im
    im = layer(); place(im, fit(P['mouth_open'], width=92), MOUTH[0], MOUTH[1] + 4); L['MouthOpen'] = im

    im = layer(); place(im, fit(P['hair'], width=370), 960, 338); L['Hair'] = im

    ORDER = ['Body', 'ArmR', 'ArmL', 'Face', 'EyeL', 'EyeR', 'EyeCloseL', 'EyeCloseR',
             'EyeSmileL', 'EyeSmileR', 'BrowL', 'BrowR', 'Mouth', 'MouthOpen', 'Hair']
    return L, ORDER

# The head must rotate about the neck joint (where it meets the collar), not
# about its own centre, otherwise it swings off the shoulders when turned.
NECK = (HEAD[0], 636)

PIVOTS = {
    'head': list(HEAD), 'neck': list(NECK), 'body': list(BODY_PIV),
    'eyeL': list(EYE_L), 'eyeR': list(EYE_R),
    'browL': list(BROW_L), 'browR': list(BROW_R),
    'mouth': list(MOUTH), 'shoL': list(SHO_L), 'shoR': list(SHO_R),
}

def main():
    L, ORDER = build()

    hidden = {'EyeCloseL', 'EyeCloseR', 'EyeSmileL', 'EyeSmileR', 'MouthOpen'}
    flat = Image.new('RGBA', (W, H), (24, 28, 34, 255))
    for n in ORDER:
        if n not in hidden:
            flat.alpha_composite(L[n])
    flat.convert('RGB').save(os.path.join(OUT, 'wardogs_male_flat.png'), optimize=True)

    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    psd = PSDImage.new('RGB', (W, H), color=(24, 28, 34))
    for n in ORDER:
        bb = L[n].getchannel('A').getbbox()
        if not bb: continue
        psd.append(PixelLayer.frompil(L[n].crop(bb), psd, n, bb[1], bb[0]))
    psd.save(os.path.join(OUT, 'wardogs_male.psd'))
    print('psd ok')

    AW = AH = 4096
    atlas = Image.new('RGBA', (AW, AH), (0, 0, 0, 0))
    amap, x, y, row_h, pad = {'__pivots__': PIVOTS}, 8, 8, 0, 8
    for n in ORDER:
        bb = L[n].getchannel('A').getbbox()
        if not bb: continue
        crop = L[n].crop(bb)
        if x + crop.width > AW - 8:
            x, y, row_h = 8, y + row_h + pad, 0
        atlas.paste(crop, (x, y))
        # bb is the part's bbox on the 1920x1080 canvas; keep it so the viewer
        # can place the layer back where the art was composed (x/y are the
        # packed atlas position, dx/dy the canvas position).
        amap[n] = {'x': x, 'y': y, 'w': crop.width, 'h': crop.height,
                   'dx': bb[0], 'dy': bb[1]}
        x += crop.width + pad
        row_h = max(row_h, crop.height)
    tex = os.path.join(OUT, 'wardogs_male.4096')
    os.makedirs(tex, exist_ok=True)
    atlas.save(os.path.join(tex, 'texture_00.png'), optimize=True)
    with open(os.path.join(tex, 'atlas_map.json'), 'w') as f:
        json.dump({'texture': 'texture_00.png', 'size': [AW, AH],
                   'pivots': PIVOTS, 'layers': {k: v for k, v in amap.items() if k != '__pivots__'}}, f, indent=1)
    print('atlas ok,', len(amap) - 1, 'rects')

if __name__ == '__main__':
    main()
