import { defineConfig } from "vitest/config";
import { storybookTest } from "@storybook/addon-vitest/vitest-plugin";
import { playwright } from "@vitest/browser-playwright";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

// Runs every story as a test in a real browser (Playwright/Chromium):
// each story is smoke-tested (renders without throwing) and any `play`
// function is executed. Powers Storybook's sidebar "Testing" widget and
// `npm run test-storybook` in CI.
export default defineConfig({
  plugins: [storybookTest({ configDir: join(here, ".storybook") })],
  test: {
    name: "storybook",
    browser: {
      enabled: true,
      provider: playwright(),
      headless: true,
      instances: [{ browser: "chromium" }],
    },
    setupFiles: [join(here, ".storybook/vitest.setup.ts")],
  },
});
