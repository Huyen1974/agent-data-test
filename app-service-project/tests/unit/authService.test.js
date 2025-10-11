import { describe, it, expect, vi } from 'vitest';
import { useAuth } from '@/firebase/authService';
import { getAuth, signInWithPopup, signOut } from 'firebase/auth';

// Mock Firebase Auth
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({ useDeviceLanguage: vi.fn(), currentUser: null })),
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}));

describe('authService', () => {
  it('checkAuthState should set user to null if not logged in', async () => {
    const { checkAuthState, user } = useAuth();
    await checkAuthState();
    expect(user.value).toBeNull();
  });

  it('signInWithGoogle should set user on successful sign-in', async () => {
    const { signInWithGoogle, user } = useAuth();
    const mockUser = { uid: '123', displayName: 'Test User' };
    signInWithPopup.mockResolvedValue({ user: mockUser });

    await signInWithGoogle();

    expect(user.value).toEqual(mockUser);
  });

  it('signInWithGoogle should set error on failed sign-in', async () => {
    const { signInWithGoogle, authError } = useAuth();
    const mockError = new Error('Sign-in failed');
    signInWithPopup.mockRejectedValue(mockError);

    await signInWithGoogle();

    expect(authError.value).toBe(mockError.message);
  });

  it('signOut should clear user on successful sign-out', async () => {
    const { signOut: signOutUser, user } = useAuth();
    user.value = { uid: '123', displayName: 'Test User' };
    signOut.mockResolvedValue(undefined);

    await signOutUser();

    expect(user.value).toBeNull();
  });

  it('signOut should set error on failed sign-out', async () => {
    const { signOut: signOutUser, authError } = useAuth();
    const mockError = new Error('Sign-out failed');
    signOut.mockRejectedValue(mockError);

    await signOutUser();

    expect(authError.value).toBe(mockError.message);
  });
});
