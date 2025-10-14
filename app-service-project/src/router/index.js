import { createRouter, createWebHistory } from 'vue-router';
import { auth } from '@/firebase/config'; // Using alias for cleaner path

// Layouts
import PublicLayout from '../layouts/PublicLayout.vue';

// Views
import HomeView from '../views/HomeView.vue';
import AboutView from '../views/AboutView.vue';
import ContactView from '../views/ContactView.vue';
import KnowledgeHubView from '../views/KnowledgeHubView.vue';
import GoodbyeView from '../views/GoodbyeView.vue';

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
  // --- Public Pages ---
  {
    path: '/',
    component: PublicLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: HomeView,
        meta: { title: 'Trang chủ' },
      },
      {
        path: 'about',
        name: 'about',
        component: AboutView,
        meta: { title: 'Giới thiệu' },
      },
      {
        path: 'lien-he',
        name: 'lien-he',
        component: ContactView,
        meta: { title: 'Liên hệ' },
      },
    ],
  },

  // --- Authenticated Workspace ---
  {
    path: '/workspace',
    name: 'workspace',
    component: KnowledgeHubView,
    meta: {
      title: 'Knowledge Hub',
      description: 'Tổng quan trung tâm tri thức.',
      requiresAuth: true,
    },
  },
  {
    path: '/portal/noi-bo',
    name: 'portal-noi-bo',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Nội Bộ',
      description: 'Phân khu nội bộ.',
      requiresAuth: true,
    },
  },
  {
    path: '/portal/kinh-doanh',
    name: 'portal-kinh-doanh',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Kinh Doanh',
      description: 'Phân khu kinh doanh.',
      requiresAuth: true,
    },
  },

  // --- Other Routes ---
  {
    path: '/goodbye',
    name: 'goodbye',
    component: GoodbyeView,
    meta: {
      title: 'Đã đăng xuất',
      description: 'Trang thông báo đăng xuất thành công.',
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
  try {
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
  } catch (error) {
    // Log the error and allow navigation to continue to avoid blocking the app
    console.error('[Router Guard Error]', error);
    next();
  }
});

export default router;
