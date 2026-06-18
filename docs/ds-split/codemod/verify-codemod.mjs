// Verifies the codemod WITHOUT a heavyweight npm install:
//  1. zero `@/` import specifiers remain
//  2. every rewritten `#...` specifier resolves to a real file on disk
//     (a dangling specifier is exactly what would break a real build)
//  3. package.json `imports` map is well-formed and covers every prefix used
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";

const dir = process.argv[2];
if (!dir) { console.error("usage: node verify-codemod.mjs <design-system-dir>"); process.exit(2); }

const SRC_EXT = [".ts", ".tsx", ".mts", ".json"];
const walk = (d, acc = []) => {
  for (const e of readdirSync(d, { withFileTypes: true })) {
    if (["node_modules", ".next", ".git", ".claude"].includes(e.name)) continue;
    const p = join(d, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (/\.(ts|tsx|mts)$/.test(e.name)) acc.push(p);
  }
  return acc;
};

const files = walk(dir);
const SPEC = /(?:from|import\(|require\()\s*["']([@#][^"']+)["']/g;

let pass = true;
const note = (ok, msg) => { console.log(`${ok ? "PASS" : "FAIL"}  ${msg}`); pass &&= ok; };

// imports map from package.json
const pkg = JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
const imap = pkg.imports || {};

// resolve a `#prefix/rest` specifier through the imports map to a real file
const resolveSubpath = (spec) => {
  for (const [key, val] of Object.entries(imap)) {
    const pfx = key.replace(/\*$/, "");
    const tgt = val.replace(/\*$/, "");
    if (spec.startsWith(pfx)) {
      const rest = spec.slice(pfx.length);
      const base = join(dir, tgt + rest);
      for (const ext of SRC_EXT) if (existsSync(base + ext)) return base + ext;
      if (existsSync(base) && statSync(base).isDirectory()) {
        for (const ext of SRC_EXT) if (existsSync(join(base, "index" + ext))) return join(base, "index" + ext);
      }
      if (existsSync(base)) return base;
      return null; // matched a prefix but no file → dangling
    }
  }
  return undefined; // no prefix matched (e.g. external pkg) — ignore
};

let oldAlias = 0, rewritten = 0, dangling = [];
const prefixesSeen = new Set();
for (const f of files) {
  const txt = readFileSync(f, "utf8");
  for (const m of txt.matchAll(SPEC)) {
    const spec = m[1];
    if (spec.startsWith("@/")) oldAlias++;
    if (spec.startsWith("#")) {
      rewritten++;
      prefixesSeen.add(spec.split("/")[0]);
      const r = resolveSubpath(spec);
      if (r === null) dangling.push(`${spec}  (in ${f.replace(dir, ".")})`);
    }
  }
}

note(oldAlias === 0, `no \`@/\` specifiers remain (found ${oldAlias})`);
note(rewritten > 0, `rewrote ${rewritten} specifiers to \`#\``);
note(dangling.length === 0, `every \`#\` specifier resolves to a real file (${dangling.length} dangling)`);
if (dangling.length) dangling.slice(0, 10).forEach((d) => console.log("        ✗ " + d));

// every prefix used has an imports-map entry
const missing = [...prefixesSeen].filter((p) => !Object.keys(imap).some((k) => k.replace(/\*$/, "").startsWith(p)));
note(missing.length === 0, `imports map covers every prefix used (${[...prefixesSeen].join(", ")})`);

console.log("");
console.log(pass ? "✅ CODEMOD VERIFIED on the real DS" : "❌ CODEMOD HAS ISSUES");
process.exit(pass ? 0 : 1);
