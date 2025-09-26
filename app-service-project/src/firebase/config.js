import { getApp, getApps, initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const runtimeConfig =
  typeof window !== 'undefined'
    ? window.__FIREBASE_CONFIG__
    : globalThis?.__FIREBASE_CONFIG__;

const fallbackConfig = {
  apiKey: 'AIzaSyDUMMY0000000000000000000000000',
  authDomain: 'localhost.localdomain',
  projectId: 'test-project',
  storageBucket: 'test-project.appspot.com',
  messagingSenderId: '000000000000',
  appId: '1:000000000000:web:0000000000000000',
};

const firebaseConfig = {
  apiKey:
    runtimeConfig?.apiKey ?? import.meta.env.VITE_FIREBASE_API_KEY ?? fallbackConfig.apiKey,
  authDomain:
    runtimeConfig?.authDomain ??
    import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ??
    fallbackConfig.authDomain,
  projectId:
    runtimeConfig?.projectId ??
    import.meta.env.VITE_FIREBASE_PROJECT_ID ??
    fallbackConfig.projectId,
  storageBucket:
    runtimeConfig?.storageBucket ??
    import.meta.env.VITE_FIREBASE_STORAGE_BUCKET ??
    fallbackConfig.storageBucket,
  messagingSenderId:
    runtimeConfig?.messagingSenderId ??
    import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID ??
    fallbackConfig.messagingSenderId,
  appId:
    runtimeConfig?.appId ??
    import.meta.env.VITE_FIREBASE_APP_ID ??
    fallbackConfig.appId,
};

const firebaseApp = getApps().length ? getApp() : initializeApp(firebaseConfig);

const auth = getAuth(firebaseApp);
auth.useDeviceLanguage();

export { auth, firebaseApp };
