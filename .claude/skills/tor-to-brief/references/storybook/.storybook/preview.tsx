import type { Preview } from "@storybook/nextjs-vite";
import { withThemeByClassName } from "@storybook/addon-themes";
import { Geist, Geist_Mono } from "next/font/google";
import "../app/globals.css";

// Same fonts the app loads in app/layout.tsx. Storybook doesn't run layout.tsx,
// so without this the `--font-sans` variable is undefined and components fall
// back to the browser serif (Times). Applying the .variable classNames on the
// canvas wrapper restores Geist (font-sans → var(--font-sans)).
const fontSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const fontMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const preview: Preview = {
  parameters: {
    // We center via the decorator below (CSS grid), so let Storybook give us
    // the full canvas with no padding/centering of its own.
    layout: "fullscreen",
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } },
    a11y: { test: "todo" },
    backgrounds: { disable: true },
  },
  decorators: [
    // Toolbar light/dark switch — toggles `.dark` on <html>, matching next-themes.
    withThemeByClassName({
      themes: { light: "", dark: "dark" },
      defaultTheme: "light",
      parentSelector: "html",
    }),
    // Center the story in the canvas with GRID (not flex): `place-content-center`
    // sizes the auto track to the child's max-content, so wide components (forms,
    // cards) keep their natural width instead of being squished to one word/line.
    // `min-h-svh` lets the themed background fill the whole canvas (incl. dark).
    (Story) => (
      // flex-col + items-center centers the story horizontally WITHOUT shrinking
      // it: the container keeps a definite width (w-full), so demos that use
      // `w-full max-w-*` resolve to their intended width instead of collapsing
      // to min-content (the per-word-wrap bug). justify-center centers vertically.
      <div
        className={`${fontSans.variable} ${fontMono.variable} font-sans flex min-h-svh w-full flex-col items-center justify-center gap-4 bg-background p-10 text-foreground`}
      >
        <Story />
      </div>
    ),
  ],
};

export default preview;
