import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAuth } from '@/firebase/authService';
import { signInWithPopup, signOut as firebaseSignOut, onAuthStateChanged } from 'firebase/auth';

// Mock Firebase Auth
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({ useDeviceLanguage: vi.fn(), currentUser: null })),
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  onAuthStateChanged: vi.fn(),
}));

// Mock router
vi.mock('@/router', () => ({
  default: {
    push: vi.fn(() => Promise.resolve()),
  },
}));

// Mock auth config
vi.mock('@/firebase/config.js', () => ({
  auth: {},
}));

describe('authService', () => {
  let onAuthStateChangedCallback;
  let onAuthStateChangedErrorCallback;
  let unsubscribeMock;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Reset module-level state before each test
    const { resetState } = useAuth();
    resetState();

    // Setup default onAuthStateChanged mock
    unsubscribeMock = vi.fn();
    onAuthStateChanged.mockImplementation((auth, successCallback, errorCallback) => {
      onAuthStateChangedCallback = successCallback;
      onAuthStateChangedErrorCallback = errorCallback;
      return unsubscribeMock;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('checkAuthState', () => {
    it('should initialize auth state when user is logged in', async () => {
      const { checkAuthState, user, isReady } = useAuth();
      const mockUser = { uid: '123', displayName: 'Test User' };

      // Start checkAuthState
      const promise = checkAuthState();

      // Simulate Firebase emitting the auth state
      onAuthStateChangedCallback(mockUser);

      await promise;

      expect(user.value).toEqual(mockUser);
      expect(isReady.value).toBe(true);
      expect(unsubscribeMock).toHaveBeenCalledTimes(1); // One-shot unsubscribe
    });

    it('should initialize auth state when user is not logged in', async () => {
      const { checkAuthState, user, isReady } = useAuth();

      const promise = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise;

      expect(user.value).toBeNull();
      expect(isReady.value).toBe(true);
    });

    it('should handle timeout after 10 seconds', async () => {
      const { checkAuthState, authError, isReady } = useAuth();

      // Start checkAuthState but don't emit any auth state
      const promise = checkAuthState();

      // Fast-forward time by 10 seconds to trigger timeout
      await vi.advanceTimersByTimeAsync(10000);

      // Wait for all pending promises
      await vi.runAllTimersAsync();

      // Should set error message and mark as ready
      expect(authError.value).toBe('Không thể khởi tạo xác thực. Vui lòng thử lại.');
      expect(isReady.value).toBe(true);
    });

    it('should handle initialization errors', async () => {
      const { checkAuthState, authError, isReady } = useAuth();
      const mockError = new Error('Firebase initialization failed');

      const promise = checkAuthState();
      onAuthStateChangedErrorCallback(mockError);
      await promise;

      expect(authError.value).toBe('Không thể khởi tạo xác thực. Vui lòng thử lại.');
      expect(isReady.value).toBe(true);
      expect(unsubscribeMock).toHaveBeenCalled();
    });

    it('should set up persistent listener after initialization', async () => {
      const { checkAuthState, user } = useAuth();
      const mockUser1 = { uid: '123', displayName: 'User 1' };
      const mockUser2 = { uid: '456', displayName: 'User 2' };

      // First call to onAuthStateChanged (one-shot)
      let firstCallback;
      let callCount = 0;
      onAuthStateChanged.mockImplementation((auth, successCallback) => {
        callCount++;
        if (callCount === 1) {
          firstCallback = successCallback;
        }
        return unsubscribeMock;
      });

      const promise = checkAuthState();
      firstCallback(mockUser1);
      await promise;

      // onAuthStateChanged should be called twice:
      // 1. One-shot initialization
      // 2. Persistent listener
      expect(onAuthStateChanged).toHaveBeenCalledTimes(2);
      expect(user.value).toEqual(mockUser1);
    });

    // Note: Testing persistent listener error handling is complex due to
    // the async nature of the setup. The error handler is verified by:
    // 1. Code inspection in authService.js lines 72-75
    // 2. Manual testing with network failures
    // 3. The error handler sets authError.value to 'Lỗi theo dõi trạng thái xác thực'

    it('should not create duplicate persistent listeners', async () => {
      const { checkAuthState } = useAuth();

      // Call checkAuthState twice
      const promise1 = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise1;

      onAuthStateChanged.mockClear();

      const promise2 = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise2;

      // Second call should only create one-shot listener, not persistent
      // (because persistent listener already exists)
      expect(onAuthStateChanged).toHaveBeenCalledTimes(1);
    });

    it('should handle race condition when called multiple times concurrently', async () => {
      const { checkAuthState, user, isReady, authError } = useAuth();
      const mockUser = { uid: '123', displayName: 'Test User' };

      // Track all callbacks for concurrent calls
      const callbacks = [];
      onAuthStateChanged.mockImplementation((auth, successCallback, errorCallback) => {
        callbacks.push({ success: successCallback, error: errorCallback });
        return unsubscribeMock;
      });

      // Start multiple concurrent calls
      const promise1 = checkAuthState();
      const promise2 = checkAuthState();

      // Wait for next tick to ensure callbacks are registered
      await Promise.resolve();

      // Emit auth state to ALL callbacks - this should resolve both promises
      callbacks.forEach(cb => cb.success(mockUser));

      await Promise.all([promise1, promise2]);

      // Should handle gracefully without errors
      expect(user.value).toEqual(mockUser);
      expect(isReady.value).toBe(true);
      expect(authError.value).toBeNull();
    });
  });

  describe('signInWithGoogle', () => {
    it('should set user on successful sign-in', async () => {
      const { signInWithGoogle, user, isSigningIn } = useAuth();
      const mockUser = { uid: '123', displayName: 'Test User' };
      signInWithPopup.mockResolvedValue({ user: mockUser });

      expect(isSigningIn.value).toBe(false);
      const promise = signInWithGoogle();
      expect(isSigningIn.value).toBe(true);

      await promise;

      expect(user.value).toEqual(mockUser);
      expect(isSigningIn.value).toBe(false);
    });

    it('should set error on failed sign-in', async () => {
      const { signInWithGoogle, authError, isSigningIn } = useAuth();
      const mockError = new Error('Sign-in failed');
      signInWithPopup.mockRejectedValue(mockError);

      await signInWithGoogle();

      expect(authError.value).toBe(mockError.message);
      expect(isSigningIn.value).toBe(false);
    });

    it('should clear previous errors before signing in', async () => {
      const { signInWithGoogle, authError } = useAuth();
      const mockUser = { uid: '123', displayName: 'Test User' };

      authError.value = 'Previous error';
      signInWithPopup.mockResolvedValue({ user: mockUser });

      await signInWithGoogle();

      expect(authError.value).toBeNull();
    });
  });

  describe('signOut', () => {
    it('should clear user on successful sign-out', async () => {
      const { signOut, user } = useAuth();
      user.value = { uid: '123', displayName: 'Test User' };
      firebaseSignOut.mockResolvedValue(undefined);

      await signOut();

      expect(user.value).toBeNull();
    });

    it('should set error on failed sign-out', async () => {
      const { signOut, authError } = useAuth();
      const mockError = new Error('Sign-out failed');
      firebaseSignOut.mockRejectedValue(mockError);

      await signOut();

      expect(authError.value).toBe(mockError.message);
    });

    it('should clear previous errors before signing out', async () => {
      const { signOut, authError } = useAuth();

      authError.value = 'Previous error';
      firebaseSignOut.mockResolvedValue(undefined);

      await signOut();

      expect(authError.value).toBeNull();
    });

    it('should handle router navigation errors gracefully', async () => {
      const { signOut } = useAuth();
      const router = await import('@/router');

      firebaseSignOut.mockResolvedValue(undefined);
      router.default.push.mockRejectedValue(new Error('Navigation cancelled'));

      // Should not throw even if navigation fails
      await expect(signOut()).resolves.not.toThrow();
    });
  });

  describe('cleanup', () => {
    it('should unsubscribe from persistent listener', async () => {
      const { checkAuthState, cleanup } = useAuth();

      // Initialize auth state to create persistent listener
      const promise = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise;

      // Cleanup should call unsubscribe
      cleanup();

      expect(unsubscribeMock).toHaveBeenCalled();
    });

    it('should handle cleanup when no listener exists', () => {
      const { cleanup } = useAuth();

      // Should not throw error
      expect(() => cleanup()).not.toThrow();
    });

    it('should allow cleanup to be called multiple times', async () => {
      const { checkAuthState, cleanup } = useAuth();

      const promise = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise;

      cleanup();
      cleanup(); // Second call

      // Should not throw error
      expect(unsubscribeMock).toHaveBeenCalled();
    });

    it('should reset listener reference after cleanup', async () => {
      const { checkAuthState, cleanup } = useAuth();

      // First initialization
      const promise1 = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise1;

      cleanup();

      // After cleanup, calling checkAuthState again should create new listener
      onAuthStateChanged.mockClear();
      unsubscribeMock.mockClear();

      const promise2 = checkAuthState();
      onAuthStateChangedCallback(null);
      await promise2;

      // Should create both one-shot and persistent listener again
      expect(onAuthStateChanged).toHaveBeenCalledTimes(2);
    });
  });

  describe('state management', () => {
    it('should share state across multiple useAuth calls', async () => {
      const auth1 = useAuth();
      const auth2 = useAuth();

      const mockUser = { uid: '123', displayName: 'Test User' };
      signInWithPopup.mockResolvedValue({ user: mockUser });

      await auth1.signInWithGoogle();

      // Both instances should see the same user
      expect(auth1.user.value).toEqual(mockUser);
      expect(auth2.user.value).toEqual(mockUser);
      expect(auth1.user).toBe(auth2.user); // Same ref object
    });

    it('should initialize isReady as false', () => {
      const { isReady } = useAuth();
      expect(isReady.value).toBe(false);
    });

    it('should initialize isSigningIn as false', () => {
      const { isSigningIn } = useAuth();
      expect(isSigningIn.value).toBe(false);
    });

    it('should initialize authError as null', () => {
      const { authError } = useAuth();
      expect(authError.value).toBeNull();
    });

    it('should initialize user as null', () => {
      const { user } = useAuth();
      expect(user.value).toBeNull();
    });
  });
});
