import { defineConfig } from '@playwright/test';

const LOCAL_BASE_URL = 'http://127.0.0.1:4173';

const baseURL = process.env.WEB_APP_URL || LOCAL_BASE_URL;

const webServer = process.env.WEB_APP_URL
  ? undefined
  : {
      command:
        "bash -lc 'export VITE_FIREBASE_API_KEY=test VITE_FIREBASE_AUTH_DOMAIN=test VITE_FIREBASE_PROJECT_ID=test VITE_FIREBASE_STORAGE_BUCKET=test VITE_FIREBASE_MESSAGING_SENDER_ID=test VITE_FIREBASE_APP_ID=test VITE_KNOWLEDGE_TREE_MOCK=true; npm run build -- --mode development; npm run preview -- --host 127.0.0.1 --port 4173'",
      port: 4173,
      reuseExistingServer: true,
      timeout: 120000,
    };

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000, // 60 seconds per test
  expect: {
    timeout: 10000, // 10 seconds for assertions
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.1,
      animations: 'disabled', // Disable animations globally for VRT
    },
  },
  use: {
    baseURL,
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    actionTimeout: 15000, // 15 seconds for actions
  },
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFileName}/{arg}{ext}',
  retries: process.env.CI ? 2 : 0, // Retry failed tests twice in CI
  workers: process.env.CI ? 2 : undefined, // Limit parallelism in CI
  webServer,
});
