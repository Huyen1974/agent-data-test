import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('firebase/app', async (importOriginal) => {
  const mod = await importOriginal();
  let apps = [];

  return {
    ...mod,
    getApps: vi.fn(() => apps),
    getApp: vi.fn(() => {
      if (!apps.length) throw new Error('no apps initialised');
      return apps[0];
    }),
    initializeApp: vi.fn((config) => {
      const instance = { config };
      apps.push(instance);
      return instance;
    }),
    __setApps(next) {
      apps = next;
    },
  };
});

vi.mock('firebase/auth', async (importOriginal) => {
  const mod = await importOriginal();
  return {
    ...mod,
    getAuth: vi.fn(() => ({ useDeviceLanguage: vi.fn() })),
  };
});

describe('firebase singleton initialisation', () => {
  beforeEach(async () => {
    const { __setApps } = await import('firebase/app');
    __setApps([]);
    vi.resetModules();
  });

  it('should reuse the same Firebase app instance on repeated imports', async () => {
    const first = await import('../../src/firebase/config.js');

    expect(first.firebaseApp).toBeDefined();

    const second = await import('../../src/firebase/config.js');

    expect(second.firebaseApp).toBe(first.firebaseApp);
  });
});
