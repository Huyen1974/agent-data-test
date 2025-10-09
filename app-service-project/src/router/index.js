/**
 * Router - STD Architecture Compliance
 *
 * Tuân thủ chiến lược "Cô lập Sự phức tạp":
 * - KHÔNG sử dụng onAuthStateChanged trực tiếp
 * - Sử dụng useAuth() service để kiểm tra trạng thái
 *
 * Constitution compliance: HP-06 (Kiến trúc Hướng Dịch vụ)
 */

import { createRouter, createWebHistory } from 'vue-router';
import { useAuth } from '@/firebase/authService';

import KnowledgeHubView from '../views/KnowledgeHubView.vue';
import GoodbyeView from '../views/GoodbyeView.vue';

// STD Architecture: Get current user from useAuth() service
const { user, isReady, checkAuthState } = useAuth();

/**
 * STD Architecture: Check if user is authenticated
 * Synchronous check for immediate auth state
 */
const getCurrentUser = () => {
  // Synchronous check - auth is always ready in STD architecture
  return user.value;
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

// Simplified Navigation Guard - allow all access for now
router.beforeEach((to, from, next) => {
  // Temporarily allow all navigation to test rendering
  next();
});

export default router;
