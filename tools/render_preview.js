#!/usr/bin/env node
/**
 * Headless preview renderer for the Wardogs_Male texture-layer rig.
 *
 * Runs the REAL rendering code out of viewer/index.html (extracted from the
 * page and executed via vm) against a @napi-rs/canvas 2D context, then pumps
 * requestAnimationFrame manually to capture still frames of any pose.
 *
 *   npm i @napi-rs/canvas
 *   node tools/render_preview.js [outDir]
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { createCanvas, loadImage } = require('@napi-rs/canvas');

const ROOT = path.resolve(__dirname, '..');
const VIEWER = path.join(ROOT, 'viewer', 'index.html');
const OUT = path.resolve(process.argv[2] || path.join(ROOT, 'preview'));
const TEX_FILE = path.join(ROOT, 'Wardogs_Male', 'wardogs_male.4096', 'texture_00.png');

const STAGE_W = 1200;
const STAGE_H = 1080;
const DPR = 1;
const DT = 1000 / 60;

const realCanvas = createCanvas(STAGE_W * DPR, STAGE_H * DPR);

/* ---------------- DOM shim ---------------- */
function stubEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    _cls: new Set(),
    _on: {},
    style: {},
    dataset: {},
    children: [],
    textContent: '',
    innerHTML: '',
    clientWidth: STAGE_W,
    clientHeight: STAGE_H,
    appendChild(c) { this.children.push(c); return c; },
    append(...c) { this.children.push(...c); },
    addEventListener(type, fn) { (this._on[type] = this._on[type] || []).push(fn); },
    removeEventListener() {},
    dispatch(type, ev) { (this._on[type] || []).forEach((f) => f(ev)); },
    setAttribute() {},
    getAttribute() { return null; },
    querySelector() { return stubEl('div'); },
    querySelectorAll() { return []; },
    getBoundingClientRect() {
      return { left: 0, top: 0, width: STAGE_W, height: STAGE_H, right: STAGE_W, bottom: STAGE_H };
    },
  };
  el.classList = {
    add: (c) => el._cls.add(c),
    remove: (c) => el._cls.delete(c),
    contains: (c) => el._cls.has(c),
    toggle: (c, force) => {
      const on = force === undefined ? !el._cls.has(c) : !!force;
      if (on) el._cls.add(c); else el._cls.delete(c);
      return on;
    },
  };
  Object.defineProperty(el, 'className', {
    get() { return [...el._cls].join(' '); },
    set(v) { el._cls = new Set(String(v).split(/\s+/).filter(Boolean)); },
  });
  return el;
}

const els = new Map();
function getEl(sel) {
  if (els.has(sel)) return els.get(sel);
  let c;
  if (sel === '#cv') {
    c = stubEl('canvas');
    c.getContext = () => realCanvas.getContext('2d');
    Object.defineProperty(c, 'width', { get: () => STAGE_W * DPR, set: () => {} });
    Object.defineProperty(c, 'height', { get: () => STAGE_H * DPR, set: () => {} });
  } else {
    c = stubEl('div');
  }
  els.set(sel, c);
  return c;
}

global.document = {
  querySelector: getEl,
  getElementById: getEl,
  createElement: (t) => stubEl(t),
  body: stubEl('body'),
  activeElement: null,
  addEventListener() {},
};
global.window = global;
global.devicePixelRatio = DPR;
global.innerWidth = STAGE_W;
global.innerHeight = STAGE_H;
global.addEventListener = () => {};
Object.defineProperty(global, 'navigator', {
  value: { mediaDevices: { getUserMedia: async () => { throw new Error('no mic headless'); } } },
  configurable: true,
  writable: true,
});
global.AudioContext = undefined;
global.webkitAudioContext = undefined;

let rafCb = null;
global.requestAnimationFrame = (cb) => { rafCb = cb; return 1; };
global.cancelAnimationFrame = () => { rafCb = null; };

global.fetch = async (url) => {
  const txt = fs.readFileSync(path.resolve(ROOT, 'viewer', url), 'utf8');
  return { ok: true, status: 200, json: async () => JSON.parse(txt), text: async () => txt };
};

/* ---------------- run the real viewer script ---------------- */
const html = fs.readFileSync(VIEWER, 'utf8');
const main = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((s) => s.includes('"use strict"'));
if (!main) { console.error('viewer script not found in', VIEWER); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const G = (expr) => vm.runInThisContext(expr); // read viewer's top-level let/const

async function main_() {
  // The viewer creates exactly one Image (the atlas). Pre-load it and hand back
  // the real napi image so drawImage() gets a genuine image object.
  const tex = await loadImage(TEX_FILE);
  let pending = null;
  Object.defineProperty(tex, 'src', {
    set(v) { tex._src = v; pending && (pending = null), queueMicrotask(() => tex.onload && tex.onload()); },
    get() { return tex._src; },
  });
  global.Image = function Image() { return tex; };

  vm.runInThisContext(main, { filename: 'viewer/index.html#script' });

  for (let i = 0; i < 400 && !G('AMAP'); i++) await sleep(25);
  if (!G('AMAP')) throw new Error('model failed to load');
  await sleep(60);

  let t = 1000;
  const pump = (n = 1) => {
    for (let i = 0; i < n; i++) {
      if (!rafCb) throw new Error('render loop stopped');
      rafCb((t += DT));
    }
  };
  const save = (name) => {
    const p = path.join(OUT, name + '.png');
    fs.writeFileSync(p, realCanvas.toBuffer('image/png'));
    console.log('wrote', path.relative(ROOT, p));
  };
  const mouseAt = (fx, fy) =>
    getEl('#stage').dispatch('mousemove', { clientX: fx * STAGE_W, clientY: fy * STAGE_H });
  const set = (o) => vm.runInThisContext('Object.assign(P,' + JSON.stringify(o) + ')');
  const expr = (n, on) => vm.runInThisContext(`exprTarget[${JSON.stringify(n)}]=${on ? 1 : 0}`);

  fs.mkdirSync(OUT, { recursive: true });

  mouseAt(0.5, 0.42);
  pump(45);
  save('01-neutral');

  for (const [name, fx, fy] of [
    ['02-look-left', 0.14, 0.42],
    ['03-look-right', 0.86, 0.42],
    ['04-look-up', 0.5, 0.10],
    ['05-look-down', 0.5, 0.80],
  ]) { mouseAt(fx, fy); pump(60); save(name); }

  mouseAt(0.5, 0.42);
  pump(40);

  set({ ParamEyeLOpen: 0, ParamEyeROpen: 0 });
  pump(1);
  save('06-blink');
  set({ ParamEyeLOpen: 1, ParamEyeROpen: 1 });
  pump(20);

  set({ ParamMouthOpenY: 1 });
  pump(1);
  save('07-mouth-open');
  set({ ParamMouthOpenY: 0 });
  pump(12);

  set({ ParamArmLZ: 30, ParamArmRZ: -30, ParamArmLY: 14, ParamArmRY: -14 });
  pump(1);
  save('08-arms');
  set({ ParamArmLZ: 0, ParamArmRZ: 0, ParamArmLY: 0, ParamArmRY: 0 });
  pump(12);

  for (const [name, e] of [
    ['09-expr-eyeclose', 'EyeClose'],
    ['10-expr-eyesmile', 'EyeSmile'],
    ['11-expr-mouthsmile', 'MouthSmile'],
    ['12-expr-salute', 'Salute'],
    ['13-expr-armcross', 'ArmCross'],
  ]) { expr(e, true); pump(45); save(name); expr(e, false); pump(28); }

  set({ ParamBodyAngleX: 10, ParamBodyAngleZ: -8, ParamAngleZ: 18 });
  pump(40);
  save('14-body-angle');

  console.log('done ->', OUT);
}

main_().catch((e) => { console.error(e); process.exit(1); });
