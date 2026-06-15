// Storybook-only browser stub for `@/lib/design-tokens`.
//
// The real module is `server-only` and reads the Figma export from disk via
// node:fs / node:path at import time — fine in Next's server runtime, but it
// breaks in Storybook's browser bundle. It's pulled in transitively because
// `components/docs/registry.tsx` imports the Foundations/Design-Token reference
// components at the top level. Those reference components are never RENDERED in
// any story, so these no-ops just need to exist to keep the graph browser-safe.
// (Foundations / Design-Token pages live in the server-rendered /docs site.)

export type ColorToken = { name: string; hex: string; [k: string]: unknown };
export type PaletteFamily = { name: string; shades: ColorToken[] };
export type NumberToken = { name: string; value: number; alias?: string };

export function getColors(): ColorToken[] {
  return [];
}
export function getPalette(): PaletteFamily[] {
  return [];
}
export function getNumbers(): NumberToken[] {
  return [];
}
export function getFontTokens(): Record<string, { name: string; value: number | string }[]> {
  return {};
}
export function getTotals(): { collection: string; count: number }[] {
  return [];
}
