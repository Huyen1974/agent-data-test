import { ref, computed, readonly } from 'vue';
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
} from 'firebase/auth';

import { auth } from '../firebase/config';

// Reactive state
const user = ref(null);
const loading = ref(true);
const error = ref('');
const isAuthActionInProgress = ref(false);

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

// Error handling utility
function normalizeAuthError(authError) {
  if (!authError) return 'Đã xảy ra lỗi không xác định.';

  const code = authError.code || '';
  const message = authError.message || '';

  switch (code) {
    case 'auth/popup-closed-by-user':
      return 'Bạn đã đóng cửa sổ đăng nhập. Vui lòng thử lại.';
    case 'auth/popup-blocked':
      return 'Cửa sổ đăng nhập bị chặn. Vui lòng cho phép popup và thử lại.';
    case 'auth/account-exists-with-different-credential':
      return 'Email đã được đăng ký với phương thức khác. Hãy đăng nhập bằng phương thức phù hợp.';
    case 'auth/email-already-in-use':
      return 'Email này đã được sử dụng. Vui lòng đăng nhập hoặc chọn email khác.';
    case 'auth/weak-password':
      return 'Mật khẩu quá yếu. Vui lòng sử dụng ít nhất 8 ký tự.';
    case 'auth/network-request-failed':
      return 'Lỗi mạng, vui lòng kiểm tra kết nối và thử lại.';
    case 'auth/too-many-requests':
      return 'Quá nhiều yêu cầu. Vui lòng đợi một phút trước khi thử lại.';
    case 'auth/user-disabled':
      return 'Tài khoản đã bị khóa. Vui lòng liên hệ hỗ trợ.';
    case 'auth/user-not-found':
      return 'Không tìm thấy tài khoản với thông tin đăng nhập này.';
    case 'auth/wrong-password':
      return 'Mật khẩu không đúng. Vui lòng kiểm tra lại.';
    case 'auth/invalid-email':
      return 'Định dạng email không hợp lệ.';
    case 'auth/operation-not-allowed':
      return 'Phương thức đăng nhập này không được phép.';
    case 'auth/invalid-api-key':
      return 'Lỗi cấu hình Firebase. Vui lòng liên hệ nhà phát triển.';
    case 'auth/app-deleted':
      return 'Ứng dụng Firebase đã bị xóa.';
    case 'auth/app-not-authorized':
      return 'Ứng dụng Firebase chưa được ủy quyền.';
    case 'auth/argument-error':
      return 'Tham số không hợp lệ. Vui lòng thử lại.';
    case 'auth/requires-recent-login':
      return 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
    default:
      return message || 'Đã xảy ra lỗi. Vui lòng thử lại.';
  }
}

// Retry utility for network failures
async function retryOperation(operation, maxRetries = 2, delayMs = 1000) {
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt < maxRetries && error.code === 'auth/network-request-failed') {
        console.warn(`Auth operation failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying...`, error);
        await new Promise(resolve => setTimeout(resolve, delayMs * (attempt + 1)));
      } else {
        break;
      }
    }
  }

  throw lastError;
}

// Computed properties
const isAuthenticated = computed(() => !!user.value);
const userDisplayName = computed(
  () => user.value?.displayName || user.value?.email || 'Tài khoản'
);

// State update functions (to be called from App.vue)
function updateAuthState(currentUser) {
  user.value = currentUser;
  error.value = '';
  loading.value = false;
}

function updateAuthError(authError) {
  user.value = null;
  error.value = authError?.message ?? 'Không thể xác thực người dùng.';
  loading.value = false;
}

// Auth methods
async function signInWithGoogle() {
  // Guard against race conditions
  if (isAuthActionInProgress.value) {
    console.warn('Sign in operation already in progress, skipping...');
    return;
  }

  error.value = '';
  loading.value = true;
  isAuthActionInProgress.value = true;

  try {
    // Use retry mechanism for network failures
    await retryOperation(async () => {
      return await signInWithPopup(auth, googleProvider);
    });

    // onAuthStateChanged will handle the success state
  } catch (authError) {
    const friendlyMessage = normalizeAuthError(authError);
    error.value = friendlyMessage;

    // Log error for debugging
    console.error('Authentication Error (Sign In):', {
      code: authError.code,
      message: authError.message,
      fullError: authError
    });

    throw authError; // Re-throw for component handling
  } finally {
    loading.value = false;
    isAuthActionInProgress.value = false;
  }
}

async function signOutUser() {
  // Guard against race conditions
  if (isAuthActionInProgress.value) {
    console.warn('Sign out operation already in progress, skipping...');
    return;
  }

  error.value = '';
  loading.value = true;
  isAuthActionInProgress.value = true;

  try {
    // Use retry mechanism for network failures
    await retryOperation(async () => {
      return await signOut(auth);
    });

    // onAuthStateChanged will handle the null user state
  } catch (authError) {
    const friendlyMessage = normalizeAuthError(authError);
    error.value = friendlyMessage;

    // Log error for debugging
    console.error('Authentication Error (Sign Out):', {
      code: authError.code,
      message: authError.message,
      fullError: authError
    });

    throw authError; // Re-throw for component handling
  } finally {
    loading.value = false;
    isAuthActionInProgress.value = false;
  }
}

// Export reactive state and methods
export function useAuth() {
  return {
    // Reactive state
    user: readonly(user),
    loading: readonly(loading),
    error: readonly(error),
    isAuthActionInProgress: readonly(isAuthActionInProgress),

    // Computed properties
    isAuthenticated,
    userDisplayName,

    // Methods
    signInWithGoogle,
    signOutUser,

    // State update functions (for App.vue to call)
    updateAuthState,
    updateAuthError,
  };
}

// Export utility functions for testing or advanced usage
export { normalizeAuthError, retryOperation };
