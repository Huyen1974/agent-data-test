import { ref, onUnmounted } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'firebase/auth';
import { auth } from './config.js';
import router from '@/router';

// Centralized state
const user = ref(null);
const authError = ref(null);
const isReady = ref(false);
const isSigningIn = ref(false);

// Track the auth state listener to prevent duplicates
let authStateUnsubscribe = null;

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
  /**
   * Waits for Firebase to complete initialization and determine the auth state.
   * This solves the issue where getAuth().currentUser is null on page refresh
   * because Firebase initializes asynchronously.
   */
  const checkAuthState = async () => {
    try {
      // Use a one-shot promise that waits for the first auth state emission
      await new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          reject(new Error('Auth state initialization timeout'));
        }, 10000); // 10 second timeout

        const unsubscribe = onAuthStateChanged(
          auth,
          (firebaseUser) => {
            clearTimeout(timeoutId);
            unsubscribe(); // Unsubscribe immediately after first emission
            user.value = firebaseUser;
            isReady.value = true;
            resolve();
          },
          (error) => {
            clearTimeout(timeoutId);
            unsubscribe();
            reject(error);
          }
        );
      });

      // After initial state is determined, set up a persistent listener
      // to keep the user state in sync for the app's lifetime
      if (!authStateUnsubscribe) {
        authStateUnsubscribe = onAuthStateChanged(
          auth,
          (firebaseUser) => {
            user.value = firebaseUser;
          },
          (error) => {
            console.error('[Auth State Listener Error]', error);
            authError.value = 'Lỗi theo dõi trạng thái xác thực';
          }
        );
      }
    } catch (error) {
      console.error('[Auth Initialization Error]', error);
      authError.value = 'Không thể khởi tạo xác thực. Vui lòng thử lại.';
      // Even on error, mark as ready to prevent infinite loading
      isReady.value = true;
    }
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

  /**
   * Cleanup function to unsubscribe from auth state listener.
   * Should be called when the app is being destroyed to prevent memory leaks.
   */
  const cleanup = () => {
    if (authStateUnsubscribe) {
      authStateUnsubscribe();
      authStateUnsubscribe = null;
    }
  };

  /**
   * Reset all state to initial values.
   * FOR TESTING ONLY - resets the module-level state.
   */
  const resetState = () => {
    user.value = null;
    authError.value = null;
    isReady.value = false;
    isSigningIn.value = false;
    if (authStateUnsubscribe) {
      authStateUnsubscribe();
      authStateUnsubscribe = null;
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
      cleanup,
      resetState,
    };
  }

  return {
    user,
    signInWithGoogle,
    signOut,
    isReady,
    isSigningIn,
    authError,
    checkAuthState,
    cleanup,
    resetState  // Export for testing
  };
}
