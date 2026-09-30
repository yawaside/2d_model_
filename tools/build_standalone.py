#!/usr/bin/env python3
"""Embed texture + configs into viewer/index.html -> standalone single file.

The resulting viewer/wardogs_model_standalone.html works offline: open it
directly in a browser (double-click) — no http server required.
"""
import base64, json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WM = os.path.join(ROOT, 'Wardogs_Male')

paths = [
    'wardogs_male.cdi3.json',
    'wardogs_male.model3.json',
    'wardogs_male.physics3.json',
    'wardogs_male.4096/atlas_map.json',
]
for e in json.load(open(os.path.join(WM, 'wardogs_male.model3.json')))['FileReferences']['Expressions']:
    paths.append(e['File'])

embed = {'json': {}, 'tex': None}
for p in paths:
    with open(os.path.join(WM, p), 'r', encoding='utf-8') as f:
        embed['json'][p] = f.read()
with open(os.path.join(WM, 'wardogs_male.4096', 'texture_00.png'), 'rb') as f:
    embed['tex'] = base64.b64encode(f.read()).decode()

html = open(os.path.join(ROOT, 'viewer', 'index.html'), encoding='utf-8').read()
tag = '<script>window.EMBED=' + json.dumps(embed) + ';</script>'
html = html.replace('<script>\n"use strict";', tag + '\n<script>\n"use strict";', 1)
assert 'window.EMBED=' in html
out = os.path.join(ROOT, 'viewer', 'wardogs_model_standalone.html')
open(out, 'w', encoding='utf-8').write(html)
print('standalone:', out, os.path.getsize(out) // 1024, 'KB')
