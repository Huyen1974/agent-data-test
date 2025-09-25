import { createRouter, createWebHistory } from 'vue-router';

import KnowledgeHubView from '../views/KnowledgeHubView.vue';

const routes = [
  {
    path: '/',
    name: 'home',
    component: KnowledgeHubView,
    meta: {
      title: 'Knowledge Hub',
      description: 'Tổng quan trung tâm tri thức (placeholder).',
    },
  },
  {
    path: '/portal/noi-bo',
    name: 'portal-noi-bo',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Nội Bộ',
      description: 'Phân khu nội bộ (placeholder).',
    },
  },
  {
    path: '/portal/kinh-doanh',
    name: 'portal-kinh-doanh',
    component: KnowledgeHubView,
    meta: {
      title: 'Portal Kinh Doanh',
      description: 'Phân khu kinh doanh (placeholder).',
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

export default router;
