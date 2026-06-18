import { defineConfig } from "tsup";
import { preserveDirectivesPlugin } from "esbuild-plugin-preserve-directives";

// Build the design system as an importable package.
// Strategy: transpile-only (bundle:false) so each component stays its own module
// and keeps its "use client" directive. Internal imports are all `#...` subpaths
// (from the codemod), kept as-is and resolved at runtime by package.json#imports.
export default defineConfig({
  entry: ["components/ui/*.tsx", "lib/*.ts", "hooks/*.ts"],
  format: ["esm"],
  outDir: "dist",
  bundle: false,            // keep file structure + per-file "use client"
  dts: false,               // d.ts generated separately via tsc (reads tsconfig paths for #)
  clean: true,
  splitting: false,
  sourcemap: false,
  // react/radix/etc are peerDeps; #-subpaths resolve at runtime — never inline them.
  external: [/^#/, /^react/, /^@radix-ui/, "radix-ui", /^lucide/],
  esbuildPlugins: [
    preserveDirectivesPlugin({
      directives: ["use client", "use server"],
      include: /\.(js|ts|jsx|tsx)$/,
      exclude: /node_modules/,
    }),
  ],
});
