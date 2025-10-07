import { describe, it, expect, beforeAll } from 'vitest';
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, query, limit, getDocs } from 'firebase/firestore';

describe('Firestore Live Connection Integration Test', () => {
  let firestore;
  let firebaseApp;

  beforeAll(() => {
    // Skip test if not in integration test environment
    if (!process.env.VITE_FIREBASE_PROJECT_ID || process.env.VITE_FIREBASE_PROJECT_ID === 'test-project') {
      throw new Error(
        'Integration test requires real Firebase credentials. ' +
        'Set VITE_FIREBASE_* environment variables to run this test.'
      );
    }

    // Initialize Firebase with environment variables
    const firebaseConfig = {
      apiKey: process.env.VITE_FIREBASE_API_KEY,
      authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: process.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: process.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: process.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: process.env.VITE_FIREBASE_APP_ID,
    };

    // Validate all required config values are present
    const missingKeys = Object.entries(firebaseConfig)
      .filter(([, value]) => !value || value === '')
      .map(([key]) => key);

    if (missingKeys.length > 0) {
      throw new Error(
        `Missing Firebase config values: ${missingKeys.join(', ')}. ` +
        'Set corresponding VITE_FIREBASE_* environment variables.'
      );
    }

    firebaseApp = initializeApp(firebaseConfig);
    firestore = getFirestore(firebaseApp);
  });

  it('should successfully connect to Firestore and read from production_documents collection', async () => {
    // Attempt to query the production_documents collection
    const collectionRef = collection(firestore, 'production_documents');
    const q = query(collectionRef, limit(1));

    // Execute the query
    const querySnapshot = await getDocs(q);

    // Verify the query executed successfully (no errors thrown)
    expect(querySnapshot).toBeDefined();

    // Log the result for debugging in CI
    if (querySnapshot.empty) {
      console.log('✅ Firestore connection successful - collection is empty (expected for new deployments)');
    } else {
      console.log(`✅ Firestore connection successful - read ${querySnapshot.size} document(s) from production_documents`);

      // Verify document structure
      querySnapshot.forEach((doc) => {
        console.log(`  Document ID: ${doc.id}`);
        expect(doc.id).toBeDefined();
        expect(doc.data()).toBeDefined();
      });
    }

    // Test passes if we get here without errors
    expect(true).toBe(true);
  }, 10000); // 10 second timeout for network call

  it('should successfully connect to Firestore and read from test_documents collection', async () => {
    // Attempt to query the test_documents collection
    const collectionRef = collection(firestore, 'test_documents');
    const q = query(collectionRef, limit(1));

    // Execute the query
    const querySnapshot = await getDocs(q);

    // Verify the query executed successfully
    expect(querySnapshot).toBeDefined();

    // Log the result
    if (querySnapshot.empty) {
      console.log('✅ Firestore connection successful - test_documents collection is empty');
    } else {
      console.log(`✅ Firestore connection successful - read ${querySnapshot.size} document(s) from test_documents`);

      // Verify document structure
      querySnapshot.forEach((doc) => {
        console.log(`  Document ID: ${doc.id}`);
        expect(doc.id).toBeDefined();
        expect(doc.data()).toBeDefined();
      });
    }

    // Test passes if we get here without errors
    expect(true).toBe(true);
  }, 10000); // 10 second timeout for network call
});
