import { describe, it, expect, beforeAll } from 'vitest';
import { initializeApp } from 'firebase/app';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

describe('Firebase Configuration Integration Test', () => {
  let firestore;
  let firebaseApp;
  let firebaseConfig;

  beforeAll(() => {
    // Skip test suite if not in integration test environment
    if (!process.env.VITE_FIREBASE_PROJECT_ID || process.env.VITE_FIREBASE_PROJECT_ID === 'test-project') {
      console.log('⏭️  Skipping Firebase integration tests - no production credentials provided');
      console.log('   Set VITE_FIREBASE_* environment variables to run these tests');
      return; // Return early, tests will be skipped
    }

    // Build Firebase config from environment variables (same as production)
    firebaseConfig = {
      apiKey: process.env.VITE_FIREBASE_API_KEY,
      authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: process.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: process.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: process.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: process.env.VITE_FIREBASE_APP_ID,
    };

    // Validate all required config values are present and non-empty
    const missingKeys = Object.entries(firebaseConfig)
      .filter(([, value]) => !value || value === '')
      .map(([key]) => key);

    if (missingKeys.length > 0) {
      throw new Error(
        `Missing Firebase config values: ${missingKeys.join(', ')}. ` +
        'Set corresponding VITE_FIREBASE_* environment variables.'
      );
    }

    // Initialize Firebase (will throw if config is invalid)
    firebaseApp = initializeApp(firebaseConfig, 'integration-test');
    firestore = getFirestore(firebaseApp);
  });

  it('should validate all Firebase config values are properly injected from secrets', () => {
    // Verify no config value contains placeholder strings
    Object.entries(firebaseConfig).forEach(([key, value]) => {
      expect(value, `${key} should not be empty`).toBeTruthy();
      expect(value, `${key} should not contain %VITE_FIREBASE_`).not.toMatch(/%VITE_FIREBASE_/);
      expect(value, `${key} should not be undefined`).not.toBe('undefined');
      expect(value, `${key} should not be null string`).not.toBe('null');
    });

    console.log('✅ All Firebase config values are properly set');
    console.log(`   Project ID: ${firebaseConfig.projectId}`);
    console.log(`   Auth Domain: ${firebaseConfig.authDomain}`);
    console.log(`   Storage Bucket: ${firebaseConfig.storageBucket}`);
  });

  it('should successfully initialize Firebase app with injected config', () => {
    // Verify Firebase app was initialized
    expect(firebaseApp).toBeDefined();
    expect(firebaseApp.name).toBe('integration-test');
    expect(firebaseApp.options.projectId).toBe(firebaseConfig.projectId);
    expect(firebaseApp.options.apiKey).toBe(firebaseConfig.apiKey);

    console.log('✅ Firebase app initialized successfully');
    console.log(`   App name: ${firebaseApp.name}`);
    console.log(`   Project ID: ${firebaseApp.options.projectId}`);
  });

  it('should successfully initialize Firestore with production config', () => {
    // Verify Firestore instance was created
    expect(firestore).toBeDefined();
    expect(firestore.app).toBe(firebaseApp);
    expect(firestore.type).toBe('firestore');

    // Verify Firestore is NOT using emulator (production mode)
    // In production, the _settings will not have host/ssl set by connectFirestoreEmulator
    const settings = firestore._settings;
    const isUsingEmulator = settings.host && settings.host.includes('localhost');

    expect(isUsingEmulator, 'Firestore should NOT be using emulator in production').toBe(false);

    console.log('✅ Firestore initialized successfully in production mode');
    console.log(`   Type: ${firestore.type}`);
    console.log(`   App: ${firestore.app.name}`);
  });

  it('should validate Firebase config matches production project', () => {
    // Verify project ID matches expected production value
    expect(firebaseConfig.projectId).toBe('github-chatgpt-ggcloud');

    // Verify auth domain matches project
    expect(firebaseConfig.authDomain).toMatch(/github-chatgpt-ggcloud/);

    // Verify storage bucket matches project
    expect(firebaseConfig.storageBucket).toMatch(/github-chatgpt-ggcloud/);

    console.log('✅ Firebase config validated for production project');
    console.log('   All config values match expected production settings');
  });
});
