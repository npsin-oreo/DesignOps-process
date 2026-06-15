#!/usr/bin/env node
/**
 * Generate one Storybook story per component, sourced from the design-system
 * registry (components/docs/registry.tsx) — the single source of truth for
 * demos + code. Each story renders the registry entry's `demo` and shows its
 * `code` in the Docs panel. Re-run after editing the registry:
 *
 *   npm run gen:stories
 *
 * Scope: the `c("slug", "Title", "Category", …)` component entries (client-safe).
 * The object-literal Foundations/Design-Token entries are intentionally skipped
 * — they depend on the server-only `lib/design-tokens.ts` (fs read) and live in
 * the /docs site, not Storybook.
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const registrySrc = readFileSync(join(root, "components/docs/registry.tsx"), "utf8");
// Generated demo stories live here; hand-authored Playground stories with
// interactive controls live in `stories/manual/` and are NOT regenerated.
const outDir = join(root, "stories/generated");

// Slugs that have a hand-written `stories/manual/*.stories.tsx` (component +
// args + argTypes). Skip them here so the sidebar has one entry per component.
const MANUAL = new Set([
  "badge", "button", "input", "textarea", "label", "switch", "checkbox",
  "toggle", "slider", "progress", "separator", "kbd", "alert", "avatar",
  "spinner", "skeleton",
  // wave 1 — overlay/composite with meaningful knobs
  "accordion", "tabs", "card", "collapsible", "radio-group", "select",
  "dialog", "tooltip", "popover", "sheet", "hover-card", "drawer",
  // wave 2
  "aspect-ratio", "button-group", "carousel", "field", "input-otp",
  "native-select", "scroll-area", "toggle-group", "alert-dialog", "dropdown-menu",
  // wave 3
  "empty", "sonner", "breadcrumb", "pagination", "item", "command",
  "table", "calendar", "sidebar",
]);

const kebab = (s) => s.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

// Match: c("slug", "Title", "Category", …
const re = /\bc\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"/g;
const entries = [];
let m;
while ((m = re.exec(registrySrc)) !== null) {
  if (MANUAL.has(m[1])) continue; // hand-authored in stories/manual/
  entries.push({ slug: m[1], title: m[2], category: m[3] });
}
if (entries.length === 0) {
  console.error("No component entries found in registry.tsx — aborting.");
  process.exit(1);
}

// Fresh output (only the generated tree)
if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const storyFor = ({ slug, title, category }) => `// AUTO-GENERATED from components/docs/registry.tsx — run \`npm run gen:stories\`. Do not edit.
import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { getEntry } from "@/components/docs/registry";

const entry = getEntry(${JSON.stringify(slug)})!;

const meta: Meta = {
  title: ${JSON.stringify(`${category}/${title}`)},
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: { component: entry.description },
      source: { code: entry.code, language: "tsx" },
    },
  },
};
export default meta;

export const Demo: StoryObj = { name: ${JSON.stringify(title)}, render: () => <>{entry.demo}</> };
`;

const byCat = {};
for (const e of entries) {
  const dir = join(outDir, kebab(e.category));
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `${e.slug}.stories.tsx`), storyFor(e));
  (byCat[e.category] ??= []).push(e.title);
}

console.log(`Generated ${entries.length} stories → stories/`);
for (const [cat, items] of Object.entries(byCat)) {
  console.log(`  ${cat} (${items.length}): ${items.join(", ")}`);
}
