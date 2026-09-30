#!/usr/bin/env python3
"""Recover each layer's placement on the 1920x1080 canvas and store it in
atlas_map.json.

build_psd.py centres every part on the 1920x1080 canvas and then crops it to
its alpha bbox before packing it into texture_00.png -- so the atlas rect alone
loses where the part belongs. Because fit() already crops to the alpha bbox,
the stored atlas w/h ARE the fitted canvas size, so the destination rect is
fully recoverable:  dx = int(cx - w/2), dy = int(cy - h/2).

Run once; tools/build_psd.py now emits dx/dy itself on any future rebuild.
"""
import json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
AMAP = os.path.join(ROOT, 'Wardogs_Male', 'wardogs_male.4096', 'atlas_map.json')

# centres used by build_psd.py::build() on the 1920x1080 canvas
LAYOUT = {
    'Body':       (960, 898),
    'ArmR':       (775, 815),
    'ArmL':       (1145, 815),
    'Face':       (960, 438),
    'EyeL':       (903, 454),
    'EyeR':       (1017, 454),
    'EyeCloseL':  (903, 454),
    'EyeCloseR':  (1017, 454),
    'EyeSmileL':  (903, 454),
    'EyeSmileR':  (1017, 454),
    'BrowL':      (901, 406),
    'BrowR':      (1019, 406),
    'Mouth':      (960, 532),
    'MouthOpen':  (960, 536),
    'Hair':       (960, 338),
}

def main():
    with open(AMAP, encoding='utf-8') as f:
        amap = json.load(f)
    missing = [k for k in amap['layers'] if k not in LAYOUT]
    if missing:
        raise SystemExit('no canvas centre known for: ' + ', '.join(missing))
    for name, (cx, cy) in LAYOUT.items():
        r = amap['layers'][name]
        r['dx'] = int(cx - r['w'] / 2)
        r['dy'] = int(cy - r['h'] / 2)
    with open(AMAP, 'w', encoding='utf-8') as f:
        json.dump(amap, f, indent=1)
    print('patched %d layer rects with canvas placement' % len(amap['layers']))
    for name, r in amap['layers'].items():
        print('  %-11s atlas %4d,%4d %3dx%-3d -> canvas %4d,%4d'
              % (name, r['x'], r['y'], r['w'], r['h'], r['dx'], r['dy']))

if __name__ == '__main__':
    main()
