import { beforeAll } from "vitest";
import { setProjectAnnotations } from "@storybook/nextjs-vite";
import * as previewAnnotations from "./preview";

// Apply the same decorators/parameters the browser preview uses (globals.css,
// theme decorator, etc.) so stories render identically under the test runner.
const project = setProjectAnnotations([previewAnnotations]);

beforeAll(project.beforeAll);
