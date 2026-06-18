// This file stands in for generated/screens/* in the product repo.
// It IMPORTS the design system from node_modules — it does NOT copy it.
import { readFileSync, lstatSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

import { cn, badgeClass } from "@acme/ds-poc";

const require = createRequire(import.meta.url);
const here = fileURLToPath(new URL(".", import.meta.url));
let pass = true;
const check = (name, ok) => { console.log(`${ok ? "PASS" : "FAIL"}  ${name}`); pass &&= ok; };

// PROOF #1 — DS is consumed as a dependency in node_modules (a symlink for a
// file:/workspace dep), and the product repo vendors ZERO DS source of its own.
const nmEntry = here + "node_modules/@acme/ds-poc";
const linkedAsDep = existsSync(nmEntry) && lstatSync(nmEntry).isSymbolicLink();
const vendorsNothing = !existsSync(here + "lib") && !existsSync(here + "components");
check("DS installed as dependency in node_modules (not copied)", linkedAsDep);
check("product repo vendors no DS source of its own", vendorsNothing);

// PROOF #2 — DS internal subpath import (#lib/utils) resolved at runtime.
check("component code runs (internal #lib/* resolved)", cn("a", false, "b") === "a b");
check("badgeClass() composes via DS internals", badgeClass("outline") === "badge badge-outline outline");

// PROOF #3 — token preset resolvable through the package's export map.
const tokensPath = require.resolve("@acme/ds-poc/tokens.css");
const tokens = readFileSync(tokensPath, "utf8");
check("tokens.css distributed via export map", tokens.includes("--primary"));

// PROOF #4 — component contract resolvable (feeds the regenerate-safe seam).
const contract = require("@acme/ds-poc/contracts/button.contract.json");
check("Button contract importable via subpath", contract.component === "Button");

console.log("");
console.log(pass ? "✅ ALL PROOFS PASSED — import-not-copy works" : "❌ SOME PROOFS FAILED");
process.exit(pass ? 0 : 1);
