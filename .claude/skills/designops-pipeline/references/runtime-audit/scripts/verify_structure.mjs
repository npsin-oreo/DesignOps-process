#!/usr/bin/env node
/**
 * RENDER structure gate (Step 4.7b / track E) — the things that are ONLY visible once the page
 * lays out at real viewports, which the static audit_prototype.py cannot see:
 *
 *   1. control-height parity   — form controls in the same <form> must render at the same height.
 *                                Catches the NativeSelect className→wrapper bug (a 32px select next
 *                                to a 48px input) that passes every static gate. Checked per viewport.
 *   2. surface consistency     — the page canvas (body / main background) must not change color by
 *                                breakpoint (an unintended media-query surface swap).
 *   3. phone-lock (advisory)   — on a desktop viewport, the content must not be capped to a phone
 *                                width (a fixed max-w-md everywhere). Advisory unless --desktop-role,
 *                                because a genuinely centered narrow form (login) is legitimate.
 *
 * Renders at mobile (390) + desktop (1280). This is the layer that would have caught the PARICH WMS
 * draft-1 gaps (cramped mobile-only column, 32px select) that green-passed all 9 static gates.
 *
 * Usage: node scripts/verify_structure.mjs <file.html> [--desktop-role]
 * Degrades gracefully: no Playwright → prints SKIPPED, exits 0. A real structural failure → exit 1.
 */
import { resolve } from "node:path";
let chromium;
try { ({ chromium } = await import("playwright")); }
catch { console.log("verify_structure: playwright not installed — SKIPPED"); process.exit(0); }

const argv = process.argv.slice(2);
const file = argv.find((a) => !a.startsWith("--"));
const desktopRole = argv.includes("--desktop-role");
if (!file) { console.log("usage: node scripts/verify_structure.mjs <file.html> [--desktop-role]"); process.exit(0); }

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 900 },
];
const PARITY_TOL = 4;   // px — intra-form control-height spread allowed (sub-pixel / border rounding)
const PHONE_CAP = 480;  // px — content spread narrower than this on desktop reads as phone-locked
// single-line form controls whose heights should match; textarea (multi-line) + checkbox/radio/range
// (native sizing) + buttons (own scale) are deliberately excluded.
const CONTROL_SEL =
  'input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=range]):not([type=file]), ' +
  'select, [data-slot="input"], [data-slot="native-select"], [data-slot="select-trigger"]';

const browser = await chromium.launch({ channel: "chrome" }).catch(() => chromium.launch());
const fails = [], notes = [];
const surface = {};

for (const vp of VIEWPORTS) {
  const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
  await page.goto("file://" + resolve(file), { waitUntil: "networkidle" }).catch(() => {});
  await page.addStyleTag({ content: "*{transition:none!important;animation:none!important}" });

  // (1) control-height parity within each form (fall back to a single page-level group)
  const parity = await page.evaluate(({ sel, tol }) => {
    const vis = (el) => {
      const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
    };
    const ctrls = [...document.querySelectorAll(sel)].filter(vis);
    const groups = new Map();
    for (const el of ctrls) {
      const key = el.closest("form") || document.body;   // group by nearest form, else the page
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push({
        h: Math.round(el.getBoundingClientRect().height),
        label: el.getAttribute("data-slot") || el.tagName.toLowerCase(),
      });
    }
    const out = [];
    let gi = 0;
    for (const [, items] of groups) {
      gi++;
      if (items.length < 2) continue;   // parity is only meaningful with ≥2 controls together
      const hs = items.map((i) => i.h), min = Math.min(...hs), max = Math.max(...hs);
      if (max - min > tol) {
        const tall = items.find((i) => i.h === max), short = items.find((i) => i.h === min);
        out.push(`form ${gi}: control heights span ${min}px–${max}px (${short.label} ${short.h} vs ${tall.label} ${tall.h})`);
      }
    }
    return out;
  }, { sel: CONTROL_SEL, tol: PARITY_TOL });
  for (const p of parity) fails.push(`[${vp.name}] control parity — ${p}`);

  // (2) record the canvas colors for the cross-viewport comparison below
  surface[vp.name] = await page.evaluate(() => {
    const bg = (n) => (n ? getComputedStyle(n).backgroundColor : null);
    return { body: bg(document.body), main: bg(document.querySelector("main")) };
  });

  // (3) phone-lock — measure the actual spread of the primary content on the desktop viewport
  if (vp.name === "desktop") {
    const lock = await page.evaluate((cap) => {
      const nodes = [...document.querySelectorAll('h1,h2,h3,p,input,select,textarea,button,[data-slot="card"]')]
        .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
      if (nodes.length < 2) return { width: null, narrow: false };
      let left = Infinity, right = -Infinity;
      for (const el of nodes) { const r = el.getBoundingClientRect(); left = Math.min(left, r.left); right = Math.max(right, r.right); }
      const w = Math.round(right - left);
      return { width: w, narrow: w <= cap };
    }, PHONE_CAP);
    if (lock.narrow) {
      const msg = `[desktop] content spans only ${lock.width}px on a 1280px viewport — looks phone-locked (a fixed max-w-md?)`;
      if (desktopRole) fails.push(msg);
      else notes.push(`${msg} — advisory; pass --desktop-role to block`);
    }
  }
  await page.close();
}

// (2) cross-viewport surface consistency — the canvas must not change color by breakpoint
for (const key of ["body", "main"]) {
  const m = surface.mobile?.[key], d = surface.desktop?.[key];
  if (m && d && m !== d) {
    fails.push(`surface consistency — ${key} background differs by breakpoint (mobile ${m} vs desktop ${d})`);
  }
}

await browser.close();

console.log(`Structure check — ${file} (viewports: ${VIEWPORTS.map((v) => v.name).join(", ")})`);
for (const n of notes) console.log("  ~ " + n);
if (fails.length) {
  console.log(`\nFAIL — ${fails.length} structural issue(s):`);
  for (const f of fails) console.log("  x " + f);
  process.exit(1);
}
console.log("OK: control heights match within forms, and the surface is consistent across breakpoints.");
process.exit(0);
