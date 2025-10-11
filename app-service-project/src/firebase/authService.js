import { ref } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  getAuth,
} from 'firebase/auth';
import { auth } from './config.js';
import router from '@/router';

// Centralized state
const user = ref(null);
const authError = ref(null);
const isReady = ref(false);
const isSigningIn = ref(false);

/**
 * Composable function to manage Firebase authentication.
 *
 * @returns {{
 *   user: import('vue').Ref<import('firebase/auth').User | null>,
 *   signInWithGoogle: () => Promise<void>,
 *   signOut: () => Promise<void>,
 *   isReady: import('vue').Ref<boolean>,
 *   isSigningIn: import('vue').Ref<boolean>,
 *   authError: import('vue').Ref<string | null>,
 *   checkAuthState: () => Promise<void>
 * }}
 */
export function useAuth() {
  const checkAuthState = async () => {
    const authInstance = getAuth();
    // This is a one-time check of the current user state
    user.value = authInstance.currentUser;
    isReady.value = true;
  };

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    authError.value = null;
    isSigningIn.value = true;
    try {
      const result = await signInWithPopup(auth, provider);
      user.value = result.user;
    } catch (error) {
      authError.value = error.message;
      console.error('Error during sign-in:', error);
    } finally {
      isSigningIn.value = false;
    }
  };

  const signOut = async () => {
    authError.value = null;
    try {
      await firebaseSignOut(auth);
      // Manually clear the user state to ensure immediate UI update
      user.value = null;
      // Redirect to the goodbye page after successful sign-out
      try {
        await router.push({ name: 'goodbye' });
      } catch (navError) {
        // Navigation error (e.g., navigation guard cancellation) - not critical
        console.warn('Navigation after sign-out was cancelled:', navError);
      }
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

  return { user, signInWithGoogle, signOut, isReady, isSigningIn, authError, checkAuthState };
}