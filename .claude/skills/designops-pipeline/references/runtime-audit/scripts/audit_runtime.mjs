#!/usr/bin/env node
/**
 * audit_runtime.mjs — Step 4.7b RUNTIME audit (opt-in). Renders the built page in
 * headless Chrome (Playwright) and runs the gates that the STATIC audit_prototype.py
 * cannot see: real ARIA/labels/landmarks (axe), hover/focus-state contrast, modal
 * focus-trap, plus a render-based taste (anti-slop) report.
 *
 * Usage (run from the prototype so Playwright resolves from its node_modules):
 *   node scripts/runtime/audit_runtime.mjs out/index.html [--dark]
 *                                          [--open=<triggerSel> --dialog=<sel>]
 *
 * Degrades gracefully: if Playwright isn't installed, every sub-gate prints SKIPPED
 * and this exits 0 (non-blocking) with a one-line "how to enable". With Playwright
 * present, a failing BLOCKING gate (axe / states / focus-trap) exits 1. The taste
 * audit is heuristic and runs in report-only mode (never blocks).
 *
 * Zero deps of its own (spawns the vendored sibling scripts).
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { existsSync } from "node:fs";

const HERE = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const html = argv.find((a) => !a.startsWith("--"));
const passthru = argv.filter((a) => a.startsWith("--dark"));
const open = argv.find((a) => a.startsWith("--open="));
const dialog = argv.find((a) => a.startsWith("--dialog="));

if (!html) {
  console.error("usage: audit_runtime.mjs <built.html> [--dark] [--open=<sel> --dialog=<sel>]");
  process.exit(2);
}
if (!existsSync(html)) {
  console.error(`[audit_runtime] file not found: ${html} — build first (npm run build → out/index.html)`);
  process.exit(2);
}

function run(script, extra = []) {
  const p = spawnSync(process.execPath, [resolve(HERE, script), html, ...passthru, ...extra], {
    encoding: "utf8",
  });
  const out = `${p.stdout || ""}${p.stderr || ""}`.trim();
  return { code: p.status ?? 0, skipped: /SKIPPED/.test(out), out };
}

// blocking gates (hard a11y); focus-trap only runs when a trigger selector is given
const gates = [
  ["axe", "axe_audit.mjs", []],
  ["states", "verify_states.mjs", []],
];
if (open) gates.push(["focus-trap", "verify_focustrap.mjs", [open, ...(dialog ? [dialog] : [])]]);

let blocked = false;
let anyRan = false;
console.log(`[audit_runtime] ${html}\n`);
for (const [name, script, extra] of gates) {
  const r = run(script, extra);
  if (r.skipped) {
    console.log(`  • ${name.padEnd(11)} SKIPPED`);
    continue;
  }
  anyRan = true;
  console.log(`  • ${name.padEnd(11)} ${r.code === 0 ? "PASS" : "FAIL"}`);
  if (r.code !== 0) {
    blocked = true;
    console.log(r.out.split("\n").map((l) => `      ${l}`).join("\n"));
  }
}

// taste audit — heuristic, report-only (never blocks)
const taste = run("taste_audit.mjs");
if (!taste.skipped) {
  anyRan = true;
  console.log(`\n  taste (anti-slop, advisory):`);
  console.log(taste.out.split("\n").map((l) => `    ${l}`).join("\n"));
}

if (!anyRan) {
  console.log("  all gates SKIPPED — Playwright not installed.");
  console.log("  enable:  npm i -D playwright && npx playwright install chromium");
  process.exit(0); // opt-in: skipping is not a failure
}

console.log(`\n[audit_runtime] ${blocked ? "🔴 BLOCKED" : "🟢 PASS"} (runtime a11y)`);
process.exit(blocked ? 1 : 0);
