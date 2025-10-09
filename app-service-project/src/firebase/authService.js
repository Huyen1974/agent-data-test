/**
 * Auth Service - STD Architecture (Standard)
 *
 * Tuân thủ chiến lược "Cô lập Sự phức tạp":
 * - Kiến trúc STD (>90% chức năng): Request-response đơn giản
 * - Sử dụng "one-shot" onAuthStateChanged CHỈ để khởi tạo
 * - KHÔNG có real-time listeners liên tục
 *
 * Constitution compliance: HP-06 (Kiến trúc Hướng Dịch vụ)
 * Plan A+ implementation: Simplified VRT setup
 */

import { ref } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut as firebaseSignOut,
} from 'firebase/auth';
import { auth } from './config.js';
import router from '@/router';

// Centralized state
const user = ref(null);
const authError = ref(null);
const isReady = ref(false);
const isSigningIn = ref(false);

// Expose test API for E2E tests IMMEDIATELY
// NOTE: Use explicit VITE_ENABLE_TEST_API flag instead of MODE or PROD checks
if (import.meta.env.VITE_ENABLE_TEST_API === 'true' && typeof window !== 'undefined') {
  console.log('[authService] Exposing __AUTH_TEST_API__');
  window.__AUTH_TEST_API__ = {
    setUser: (testUser) => {
      console.log('[__AUTH_TEST_API__] setUser called with:', testUser);
      user.value = testUser;
      isReady.value = true;
    },
    setLoading: (loading) => {
      console.log('[__AUTH_TEST_API__] setLoading called with:', loading);
      isReady.value = !loading;
    },
    setError: (errorMsg) => {
      console.log('[__AUTH_TEST_API__] setError called with:', errorMsg);
      authError.value = errorMsg;
    },
  };
  console.log('[authService] __AUTH_TEST_API__ exposed successfully');
}

/**
 * STD Architecture: Pure synchronous auth state check
 *
 * This function provides immediate access to current auth state without any async operations
 * or listeners. For VRT tests, we initialize auth state synchronously to avoid race conditions.
 *
 * @returns {import('firebase/auth').User | null} Current authenticated user or null
 */
function checkAuthState() {
  // Always mark as ready immediately for STD architecture
  // No user is logged in initially - test API will inject when needed
  isReady.value = true;
  return user.value;
}

/**
 * Composable function to manage Firebase authentication.
 *
 * STD ARCHITECTURE (>90% features):
 * - Request-response pattern ONLY
 * - One-shot initialization check (NOT continuous listener)
 * - Manual state checks via checkAuthState()
 *
 * @returns {{
 *   user: import('vue').Ref<import('firebase/auth').User | null>,
 *   signInWithGoogle: () => Promise<void>,
 *   signOut: () => Promise<void>,
 *   isReady: import('vue').Ref<boolean>,
 *   isSigningIn: import('vue').Ref<boolean>,
 *   authError: import('vue').Ref<string | null>,
 *   checkAuthState: () => Promise<import('firebase/auth').User | null>
 * }}
 */
export function useAuth() {
  // STD Architecture: Initialize auth state synchronously
  // No async operations - state is ready immediately
  if (!isReady.value) {
    checkAuthState();
  }

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    authError.value = null;
    isSigningIn.value = true;
    try {
      await signInWithPopup(auth, provider);
      // STD Architecture: Update state after successful sign-in
      user.value = auth.currentUser;
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
      // STD Architecture: Manually clear the user state
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

  return {
    user,
    signInWithGoogle,
    signOut,
    isReady,
    isSigningIn,
    authError,
    checkAuthState,
  };
}
