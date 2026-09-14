import path from "node:path";
import { defineConfig } from "vitest/config";

/** Vitest config for the frontend's unit tests (tests/unit/). Mirrors
 * tsconfig.json's `@/*` path alias so tests can import components/hooks the
 * same way app code does, and runs in a jsdom environment (not the default
 * "node" one) since these are React component tests that need `document`.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Next.js's own bundler uses the automatic JSX runtime (no `import React`
  // needed per file); esbuild defaults to the classic runtime unless told
  // otherwise, which would otherwise fail every test file with "React is not
  // defined" despite the app itself building fine under Next.js.
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/unit/**/*.test.{ts,tsx}"],
  },
});
