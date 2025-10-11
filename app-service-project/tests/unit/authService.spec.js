import { useAuth } from '@/firebase/authService';

describe('authService', () => {
  it('should return the useAuth composable', () => {
    const { user, signInWithGoogle, signOut, isReady, isSigningIn, authError, checkAuthState } = useAuth();
    expect(user).toBeDefined();
    expect(signInWithGoogle).toBeDefined();
    expect(signOut).toBeDefined();
    expect(isReady).toBeDefined();
    expect(isSigningIn).toBeDefined();
    expect(authError).toBeDefined();
    expect(checkAuthState).toBeDefined();
  });
});
