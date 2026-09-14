import { defineConfig, devices } from "@playwright/test";

/** Playwright config for tests/e2e/. Boots the Next.js dev server
 * automatically (see `webServer` below) so `npm run test:e2e` works with no
 * manual setup beyond `npm install` — matches the backend already being
 * expected on localhost:8000 (agent/src/api), which these specs hit via the
 * app's own apiClient, not via Playwright directly.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
