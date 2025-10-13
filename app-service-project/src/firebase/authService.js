import { ref, onUnmounted } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signOut as firebaseSignOut,
  onAuthStateChanged,
} from 'firebase/auth';
import { auth } from './config.js';
import router from '@/router';

const mockAuthEnabled = import.meta.env.VITE_E2E_AUTH_MOCK === 'true';

const createMockUser = () => ({
  uid: 'mock-user',
  displayName: 'E2E Test User',
  email: 'e2e-tester@example.com',
  photoURL: null,
  providerData: []
});

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
 * Features:
 * - Google Sign-in with popup (preferred)
 * - Automatic fallback to redirect if popup is blocked
 * - Comprehensive error handling for all auth scenarios
 * - Graceful handling of user-initiated cancellations
 * - Redirect result processing on app initialization
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
      if (mockAuthEnabled) {
        // In mock mode we skip Firebase initialization entirely
        user.value = null;
        authError.value = null;
        isReady.value = true;
        return;
      }

      // First, check if we're returning from a redirect sign-in
      // This handles the case where signInWithRedirect was used as fallback
      try {
        const redirectResult = await getRedirectResult(auth);
        if (redirectResult) {
          // User successfully signed in via redirect
          console.log('[Redirect Success] User signed in via redirect');
          user.value = redirectResult.user;
          // Clear any previous error message
          authError.value = null;
        }
      } catch (redirectError) {
        // Handle redirect errors
        console.error('[Redirect Result Error]', redirectError);
        if (redirectError.code !== 'auth/invalid-api-key') {
          // Don't show error for invalid API key (config issue, not user error)
          authError.value = 'Lỗi xử lý kết quả đăng nhập. Vui lòng thử lại.';
        }
      }

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
      if (mockAuthEnabled) {
        // Simulate async network delay so UI state transitions remain realistic
        await new Promise((resolve) => setTimeout(resolve, 150));
        const mockUser = createMockUser();
        user.value = mockUser;
        isSigningIn.value = false;
        return;
      }

      // Try popup first (better UX as user stays on same page)
      const result = await signInWithPopup(auth, provider);
      user.value = result.user;
      // Sign-in succeeded, reset the signing-in state
      isSigningIn.value = false;
    } catch (error) {
      console.error('[Sign-in Error]', error);

      // Handle popup-blocked error with fallback to redirect
      if (error.code === 'auth/popup-blocked') {
        console.warn('[Popup Blocked] Falling back to redirect method');
        authError.value = 'Cửa sổ đăng nhập bị chặn. Đang chuyển hướng...';

        try {
          // Use redirect as fallback
          // Note: This will cause a full page reload
          await signInWithRedirect(auth, provider);
          // The page will reload, so the code below won't execute
          // The result will be handled by getRedirectResult in checkAuthState
          // IMPORTANT: Do NOT reset isSigningIn here because the page will reload
        } catch (redirectError) {
          console.error('[Redirect Error]', redirectError);
          authError.value = 'Không thể đăng nhập. Vui lòng kiểm tra cài đặt trình duyệt và thử lại.';
          isSigningIn.value = false;
        }
      } else if (error.code === 'auth/popup-closed-by-user') {
        // User closed the popup - not an error, just reset state
        console.log('[User Action] Sign-in popup closed by user');
        authError.value = null;  // Don't show error for user cancellation
        isSigningIn.value = false;
      } else if (error.code === 'auth/cancelled-popup-request') {
        // Multiple popup requests - only show warning in console
        console.warn('[Multiple Popups] A sign-in popup is already open');
        authError.value = null;
        isSigningIn.value = false;
      } else {
        // Generic error handling
        const errorMessages = {
          'auth/network-request-failed': 'Lỗi kết nối mạng. Vui lòng kiểm tra internet và thử lại.',
          'auth/too-many-requests': 'Quá nhiều yêu cầu đăng nhập. Vui lòng thử lại sau ít phút.',
          'auth/user-disabled': 'Tài khoản này đã bị vô hiệu hóa.',
          'auth/operation-not-allowed': 'Phương thức đăng nhập này chưa được kích hoạt.'
        };

        authError.value = errorMessages[error.code] || `Lỗi đăng nhập: ${error.message}`;
        isSigningIn.value = false;
      }
    }
  };

  const signOut = async () => {
    authError.value = null;
    try {
      if (!mockAuthEnabled) {
        await firebaseSignOut(auth);
      }
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
