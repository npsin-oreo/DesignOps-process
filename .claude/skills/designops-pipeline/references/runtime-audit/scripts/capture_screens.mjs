#!/usr/bin/env node
/**
 * SCREENSHOT capture (Step 4.6 input / track F) — render the built page at each breakpoint and save
 * PNGs, so the Step 4.6 critique + its judge score what is ACTUALLY VISIBLE, not the code + the
 * screen-inventory. Root cause #5: the judge gave PARICH draft-1 an 8.1 from source, blind to the
 * cramped column / flat surfaces a screenshot makes obvious.
 *
 * Writes <out>/<name>-<viewport>.png for mobile + desktop (+ -dark with --dark). Prints the list of
 * files it wrote — that list is what critique.json's `screenshots` array should reference (the
 * evidence the richness/responsiveness scores are read from).
 *
 * Usage: node scripts/capture_screens.mjs <file.html> [--out docs/screens] [--dark] [--name home]
 * Degrades gracefully: no Playwright → SKIPPED, exit 0.
 */
import { resolve, join, basename, dirname } from "node:path";
import { mkdirSync } from "node:fs";
let chromium;
try { ({ chromium } = await import("playwright")); }
catch { console.log("capture_screens: playwright not installed — SKIPPED"); process.exit(0); }

const argv = process.argv.slice(2);
const file = argv.find((a) => !a.startsWith("--"));
const dark = argv.includes("--dark");
const outArg = argv.find((a) => a.startsWith("--out="));
const nameArg = argv.find((a) => a.startsWith("--name="));
if (!file) { console.log("usage: node scripts/capture_screens.mjs <file.html> [--out=dir] [--dark] [--name=x]"); process.exit(0); }

const out = outArg ? outArg.split("=")[1] : join(dirname(resolve(file)), "screens");
const name = nameArg ? nameArg.split("=")[1] : basename(file).replace(/\.html?$/i, "") || "screen";
mkdirSync(out, { recursive: true });

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 900 },
];

const browser = await chromium.launch({ channel: "chrome" }).catch(() => chromium.launch());
const written = [];
for (const vp of VIEWPORTS) {
  const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
  await page.goto("file://" + resolve(file), { waitUntil: "networkidle" }).catch(() => {});
  if (dark) await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
  const dst = join(out, `${name}-${vp.name}${dark ? "-dark" : ""}.png`);
  await page.screenshot({ path: dst, fullPage: true }).catch(() => {});
  written.push(dst);
  await page.close();
}
await browser.close();

console.log(`Captured ${written.length} screenshot(s) for "${name}":`);
for (const w of written) console.log("  " + w);
console.log("\nReference these in critique.json `screenshots` — the judge must score richness/responsiveness from them.");
process.exit(0);
