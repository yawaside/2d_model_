#!/usr/bin/env python3
"""Build preview/00-contact-sheet.png and preview/00-vs-reference.png from the
stills written by tools/render_preview.js."""
import os
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PV = os.path.join(ROOT, 'preview')

# character box in RENDER pixels of the 1200x1080 stills
# (canvas 1920x1080, camera s=0.96, centre (960,610))
BODY_BOX = (370, 130, 830, 1042)
FACE_BOX = (440, 130, 780, 600)

def cam(box, s=0.96, ox=600, oy=550):
    x0, y0, x1, y1 = box
    return (int(ox + (x0 - 960) * s), int(oy + (y0 - 610) * s),
            int(ox + (x1 - 960) * s), int(oy + (y1 - 610) * s))

def label(d, xy, text, w, h=26, fs=15):
    d.rectangle([xy[0], xy[1] - h, xy[0] + w, xy[1]], fill=(200, 170, 94))
    d.text((xy[0] + 8, xy[1] - h + 5), text, fill=(14, 17, 22), font=fs and __import__('PIL.ImageFont', fromlist=['ImageFont']).ImageFont.load_default())

def load(name, box):
    im = Image.open(os.path.join(PV, name + '.png')).convert('RGB')
    return im.crop(box)

def sheet():
    names = sorted(f[:-4] for f in os.listdir(PV)
                   if f.endswith('.png') and f[:2].isdigit() and f[:2] != '00')
    tw = 300
    tiles = []
    for n in names:
        im = load(n, BODY_BOX)
        tiles.append((n, im.resize((tw, int(im.height * tw / im.width)), Image.LANCZOS)))
    th = max(t.height for _, t in tiles) + 26
    cols, rows = 5, (len(tiles) + 4) // 5
    out = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 8) + 34), (14, 17, 22))
    d = ImageDraw.Draw(out)
    d.text((10, 10), 'WARDOGS_MALE // assembled rig — 14 poses', fill=(200, 170, 94))
    for i, (n, t) in enumerate(tiles):
        x = 8 + (i % cols) * (tw + 8)
        y = 34 + (i // cols) * (th + 8) + 26
        out.paste(t, (x, y))
        d.rectangle([x, y - 22, x + tw, y], fill=(27, 34, 44))
        d.text((x + 6, y - 18), n, fill=(200, 170, 94))
    p = os.path.join(PV, '00-contact-sheet.png')
    out.save(p)
    print('wrote', os.path.relpath(p, ROOT), out.size)

    # face close-ups for the expression set
    fnames = [n for n in names if 'expr' in n or n.endswith('blink') or n.endswith('mouth-open')
              or n == '01-neutral']
    ft = []
    for n in fnames:
        im = load(n, FACE_BOX)
        ft.append((n, im))
    fw = max(i.width for _, i in ft)
    fh = max(i.height for _, i in ft) + 26
    fcols = len(ft)
    fo = Image.new('RGB', (fcols * (fw + 8) + 8, fh + 34), (14, 17, 22))
    fd = ImageDraw.Draw(fo)
    fd.text((10, 10), 'WARDOGS_MALE // face detail', fill=(200, 170, 94))
    for i, (n, t) in enumerate(ft):
        x = 8 + i * (fw + 8)
        y = 34 + 26
        fo.paste(t, (x, y))
        fd.rectangle([x, y - 22, x + fw, y], fill=(27, 34, 44))
        fd.text((x + 6, y - 18), n, fill=(200, 170, 94))
    p2 = os.path.join(PV, '00-face-detail.png')
    fo.save(p2)
    print('wrote', os.path.relpath(p2, ROOT), fo.size)

def vs_reference():
    ref = Image.open(os.path.join(ROOT, 'Wardogs_Male', 'wardogs_male_flat.png')).convert('RGB')
    mine = Image.open(os.path.join(PV, '01-neutral.png')).convert('RGB')
    # same canvas-space box on both, so the two crops line up 1:1
    CB = (690, 150, 1230, 1080)
    a = ref.crop(CB)
    b = mine.crop(cam(CB))
    w = 620
    a = a.resize((w, int(a.height * w / a.width)), Image.LANCZOS)
    b = b.resize((w, int(b.height * w / b.width)), Image.LANCZOS)
    h = max(a.height, b.height) + 40
    out = Image.new('RGB', (w * 2 + 24, h), (14, 17, 22))
    d = ImageDraw.Draw(out)
    out.paste(a, (8, 32))
    out.paste(b, (w + 16, 32))
    d.text((8, 10), 'GROUND TRUTH  wardogs_male_flat.png (build_psd.py)', fill=(200, 170, 94))
    d.text((w + 16, 10), 'VIEWER RENDER  preview/01-neutral.png', fill=(200, 170, 94))
    p = os.path.join(PV, '00-vs-reference.png')
    out.save(p)
    print('wrote', os.path.relpath(p, ROOT), out.size)

if __name__ == '__main__':
    sheet()
    vs_reference()
