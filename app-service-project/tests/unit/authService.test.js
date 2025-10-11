import { describe, it, expect, vi } from 'vitest';
import { useAuth } from '@/firebase/authService';
import { getAuth, signInWithPopup, signOut } from 'firebase/auth';

// Mock Firebase Auth
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({ useDeviceLanguage: vi.fn() })),
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}));

describe('authService', () => {
  it('signInWithGoogle should set user on successful sign-in', async () => {
    const { signInWithGoogle, user } = useAuth();
    const mockUser = { uid: '123', displayName: 'Test User' };
    signInWithPopup.mockResolvedValue({ user: mockUser });

    await signInWithGoogle();

    expect(user.value).toEqual(mockUser);
  });

  it('signOut should clear user on successful sign-out', async () => {
    const { signOut: signOutUser, user } = useAuth();
    user.value = { uid: '123', displayName: 'Test User' };
    signOut.mockResolvedValue(undefined);

    await signOutUser();

    expect(user.value).toBeNull();
  });
});