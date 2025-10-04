import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        return html.replace(
          /%VITE_FIREBASE_([A-Z_]+)%/g,
          (match, key) => process.env[`VITE_FIREBASE_${key}`] || ''
        );
      },
    },
  ],
  test: {
    // Exclude E2E tests from the Vitest runner
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/e2e/**',
    ],
    // Optional: Specify test environment if needed, e.g., jsdom
    environment: 'jsdom',
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
