#!/usr/bin/env node
/**
 * RENDER anti-plain check (Step 4.7b / track I) — the render-based evidence for the "clean but plain"
 * gap. Gate 6 proves the identity TOKENS are applied; this looks at whether they are actually USED
 * richly once the page renders, which no static gate can see:
 *
 *   1. flat surfaces  — cards whose background == the page background with no border AND no shadow
 *                       (white-on-white, no separation).
 *   2. accent unused  — no saturated identity colour anywhere in the rendered fills / text / borders
 *                       (the whole screen is greyscale — the brand accent never lands).
 *   3. no elevation   — no element carries a box-shadow (every surface reads flat).
 *   4. blank empty    — an empty-state region ([data-slot=empty] or "No data"-style text) with no
 *                       actionable descendant (button / link) — a dead end, not value+action.
 *
 * This is the evidence the Step 4.6 critique reads to score its **richness** dimension (track J), and
 * the render counterpart to the aesthetic `usage` block (track H). ADVISORY by default (report-only,
 * exit 0) — flatness detection is heuristic, so it never blocks a build; pass --strict-richness to make
 * findings exit 1 (opt-in teeth). Degrades gracefully: no Playwright → SKIPPED, exit 0.
 *
 * Usage: node scripts/verify_richness.mjs <file.html> [--dark] [--strict-richness]
 */
import { resolve } from "node:path";
let chromium;
try { ({ chromium } = await import("playwright")); }
catch { console.log("verify_richness: playwright not installed — SKIPPED"); process.exit(0); }

const argv = process.argv.slice(2);
const dark = argv.includes("--dark");
const strict = argv.includes("--strict-richness");
const file = argv.find((a) => !a.startsWith("--"));
if (!file) { console.log("usage: node scripts/verify_richness.mjs <file.html> [--dark] [--strict-richness]"); process.exit(0); }

const CHROMA_MIN = 26;  // sRGB (max-min) below this is effectively greyscale — no identity colour

const browser = await chromium.launch({ channel: "chrome" }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto("file://" + resolve(file), { waitUntil: "networkidle" }).catch(() => {});
await page.addStyleTag({ content: "*{transition:none!important;animation:none!important}" });
if (dark) await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));

const findings = await page.evaluate((chromaMin) => {
  const rgb = (s) => { const m = s && s.match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : null; };
  const opaque = (s) => { const a = s && s.match(/[\d.]+/g); return a && !(a.length === 4 && parseFloat(a[3]) === 0); };
  const chroma = (c) => { const p = rgb(c); return p ? Math.max(...p) - Math.min(...p) : 0; };
  const vis = (el) => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 4 && r.height > 4 && cs.visibility !== "hidden" && cs.display !== "none"; };
  const out = [];

  const all = [...document.querySelectorAll("body *")].filter(vis);
  const pageBg = getComputedStyle(document.body).backgroundColor;

  // (1) flat cards — bg equals the page canvas, no border, no shadow
  const cards = all.filter((el) => (el.getAttribute("data-slot") || "").includes("card") || /(^|\s)card(\s|$)/i.test(el.className || ""));
  let flat = 0;
  for (const el of cards) {
    const cs = getComputedStyle(el);
    const sameBg = !opaque(cs.backgroundColor) || cs.backgroundColor === pageBg;
    const noBorder = parseFloat(cs.borderTopWidth) === 0 && parseFloat(cs.borderBottomWidth) === 0;
    const noShadow = !cs.boxShadow || cs.boxShadow === "none";
    if (sameBg && noBorder && noShadow) flat++;
  }
  if (cards.length && flat === cards.length) out.push(`all ${cards.length} card(s) are flat — bg == page, no border, no shadow (no surface separation)`);
  else if (flat) out.push(`${flat}/${cards.length} card(s) are flat (bg == page, no border, no shadow)`);

  // (2) accent unused — no saturated colour anywhere in fills / text / borders
  let maxChroma = 0;
  for (const el of all) {
    const cs = getComputedStyle(el);
    for (const c of [opaque(cs.backgroundColor) ? cs.backgroundColor : null, cs.color, opaque(cs.borderTopColor) ? cs.borderTopColor : null]) {
      if (c) maxChroma = Math.max(maxChroma, chroma(c));
    }
  }
  if (maxChroma < chromaMin) out.push(`no identity colour rendered — the screen is greyscale (max chroma ${maxChroma} < ${chromaMin}); the accent/primary never lands on anything`);

  // (3) no elevation — nothing carries a shadow
  const hasShadow = all.some((el) => { const s = getComputedStyle(el).boxShadow; return s && s !== "none"; });
  if (!hasShadow) out.push("no elevation — no element has a box-shadow; every surface reads flat");

  // (4) blank empty states — an empty region with no action inside
  const empties = all.filter((el) =>
    (el.getAttribute("data-slot") || "").includes("empty") ||
    /\b(no data|nothing here|no results|no items|no records)\b/i.test((el.textContent || "").trim().slice(0, 60)));
  for (const el of empties) {
    if (!el.querySelector("button, a[href], [role=button]")) {
      out.push(`empty state "${(el.textContent || "").trim().slice(0, 30)}" has no action — value + next step, not a dead end`);
    }
  }
  return out;
}, CHROMA_MIN);

await browser.close();

const mode = dark ? " [dark]" : "";
console.log(`Richness (anti-plain) — ${file}${mode}`);
if (findings.length) {
  for (const f of findings) console.log("  ~ " + f);
  console.log(`\n${strict ? "FAIL" : "advisory"} — ${findings.length} plainness signal(s)${strict ? "" : " (report-only; feeds the critique richness score)"}`);
  process.exit(strict ? 1 : 0);
}
console.log("OK: surfaces are tinted/separated, identity colour is present, elevation exists, empty states carry action.");
process.exit(0);
