import { createRouter, createWebHistory } from 'vue-router';
import { auth } from '@/firebase/config'; // Using alias for cleaner path

import KnowledgeHubView from '../views/KnowledgeHubView.vue';

// Helper to get current user state asynchronously
const getCurrentUser = () => {
  return new Promise((resolve, reject) => {
    const unsubscribe = auth.onAuthStateChanged(
      user => {
        unsubscribe();
        resolve(user);
      },
      reject
    );
  });
};

const routes = [
  {
    path: '/',
    name: 'home',
    component: KnowledgeHubView,
    meta: {
      title: 'Knowledge Hub',
      description: 'Tổng quan trung tâm tri thức.',
    },
  },
  {
    path: '/portal/noi-bo',
    name: 'portal-noi-bo',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Nội Bộ',
      description: 'Phân khu nội bộ.',
      requiresAuth: true, // This route requires authentication
    },
  },
  {
    path: '/portal/kinh-doanh',
    name: 'portal-kinh-doanh',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Kinh Doanh',
      description: 'Phân khu kinh doanh.',
      requiresAuth: true, // This route requires authentication
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

// Global Navigation Guard
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);

  if (requiresAuth) {
    const user = await getCurrentUser();
    if (!user) {
      // User is not logged in, redirect to the home page.
      console.log('Unauthorized access attempt to a protected route. Redirecting to /.');
      next({ name: 'home' });
    } else {
      // User is logged in, allow access.
      next();
    }
  } else {
    // Route does not require auth, allow access.
    next();
  }
});

export default router;
