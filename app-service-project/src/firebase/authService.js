import { ref, onUnmounted } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'firebase/auth';
import { auth } from './config.js';

// Centralized state
const user = ref(null);
const authError = ref(null);
const isReady = ref(false);

/**
 * Composable function to manage Firebase authentication.
 *
 * @returns {{
 *   user: import('vue').Ref<import('firebase/auth').User | null>,
 *   signInWithGoogle: () => Promise<void>,
 *   signOut: () => Promise<void>,
 *   isReady: import('vue').Ref<boolean>,
 *   authError: import('vue').Ref<string | null>
 * }}
 */
export function useAuth() {
  const unsubscribe = onAuthStateChanged(
    auth,
    (firebaseUser) => {
      user.value = firebaseUser;
      isReady.value = true;
    },
    (err) => {
      console.error('Auth state error:', err);
      authError.value = err.message;
      isReady.value = true;
    }
  );

  onUnmounted(() => {
    unsubscribe();
  });

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    authError.value = null;
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      authError.value = error.message;
      console.error('Error during sign-in:', error);
    }
  };

  const signOut = async () => {
    authError.value = null;
    try {
      await firebaseSignOut(auth);
    } catch (error) {
      authError.value = error.message;
      console.error('Error during sign-out:', error);
    }
  };

  // Expose a test API in non-production environments
  if (import.meta.env.MODE !== 'production' && typeof window !== 'undefined') {
    window.__AUTH_TEST_API__ = {
      setUser: (testUser) => {
        user.value = testUser;
      },
      setLoading: (loading) => {
        isReady.value = !loading;
      },
      setError: (errorMsg) => {
        authError.value = errorMsg;
      },
    };
  }

  return { user, signInWithGoogle, signOut, isReady, authError };
}
