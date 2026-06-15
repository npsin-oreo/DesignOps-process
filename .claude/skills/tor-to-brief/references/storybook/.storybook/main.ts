import type { StorybookConfig } from "@storybook/nextjs-vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const config: StorybookConfig = {
  framework: "@storybook/nextjs-vite",
  stories: ["../stories/**/*.stories.@(tsx|mdx)"],
  addons: [
    "@storybook/addon-docs",
    "@storybook/addon-a11y",
    "@storybook/addon-themes",
    "@storybook/addon-vitest",
  ],
  async viteFinal(viteConfig) {
    // Tailwind v4 — process app/globals.css (@import "tailwindcss" + @theme inline)
    const { default: tailwindcss } = await import("@tailwindcss/vite");
    viteConfig.plugins = [...(viteConfig.plugins ?? []), tailwindcss()];

    // Preserve any framework-provided aliases, then prepend ours (first match wins).
    const existing = viteConfig.resolve?.alias;
    const existingArr = Array.isArray(existing)
      ? existing
      : Object.entries(existing ?? {}).map(([find, replacement]) => ({ find, replacement }));
    viteConfig.resolve = {
      ...viteConfig.resolve,
      alias: [
        // Stub the server-only token reader (node:fs/path) for the browser bundle.
        // Reached transitively via registry → Foundations reference components,
        // which are never rendered in stories. See design-tokens.stub.ts.
        { find: "@/lib/design-tokens", replacement: resolve(projectRoot, ".storybook/design-tokens.stub.ts") },
        // Mirror tsconfig paths so "@/..." resolves the same as in the app.
        { find: "@", replacement: projectRoot },
        ...existingArr,
      ],
    };
    return viteConfig;
  },
};

export default config;
