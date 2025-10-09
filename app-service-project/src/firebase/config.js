import { getApp, getApps, initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const runtimeConfig =
  typeof window !== 'undefined'
    ? window.__FIREBASE_CONFIG__
    : globalThis?.__FIREBASE_CONFIG__;

console.log('[firebase/config.js] Runtime config:', runtimeConfig);

const ENV_KEY_MAP = {
  apiKey: 'VITE_FIREBASE_API_KEY',
  authDomain: 'VITE_FIREBASE_AUTH_DOMAIN',
  projectId: 'VITE_FIREBASE_PROJECT_ID',
  storageBucket: 'VITE_FIREBASE_STORAGE_BUCKET',
  messagingSenderId: 'VITE_FIREBASE_MESSAGING_SENDER_ID',
  appId: 'VITE_FIREBASE_APP_ID',
};

const sanitizeValue = value => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed === '' ? undefined : trimmed;
  }

  return value ?? undefined;
};

const resolveConfigValue = key => {
  const runtimeValue = sanitizeValue(runtimeConfig?.[key]);
  if (runtimeValue !== undefined) {
    return runtimeValue;
  }

  const envKey = ENV_KEY_MAP[key];
  const envValue = sanitizeValue(import.meta.env?.[envKey]);
  if (envValue !== undefined) {
    return envValue;
  }

  return fallbackConfig[key];
};

// Use test config for VRT tests to avoid Firebase initialization issues
const fallbackConfig = {
  apiKey: 'test-api-key',
  authDomain: 'test-domain.firebaseapp.com',
  projectId: 'test-project',
  storageBucket: 'test-project.appspot.com',
  messagingSenderId: '123456789',
  appId: '1:123456789:web:abcdef123456',
};

const firebaseConfig = Object.fromEntries(
  Object.keys(ENV_KEY_MAP).map(key => [key, resolveConfigValue(key)])
);

// Check if any config value still relies on the fallback defaults
const fallbackIssues = Object.entries(firebaseConfig)
  .filter(([key, value]) => value === fallbackConfig[key])
  .map(([key]) => key);

if (fallbackIssues.length > 0 && process.env.NODE_ENV !== 'test') {
  console.warn(
    '[Firebase Config] Using fallback values for: ' +
      fallbackIssues.join(', ') +
      '. This should only happen in development or test environments.'
  );
}

// Simplified Firebase initialization for testing
const firebaseApp = getApps().length ? getApp() : initializeApp(firebaseConfig);
console.log('[firebase/config.js] Firebase app initialized');

const auth = getAuth(firebaseApp);
console.log('[firebase/config.js] Firebase auth initialized');

export { auth, firebaseApp };
