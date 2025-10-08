/**
 * Knowledge Service - STD Architecture (Standard)
 *
 * Tuân thủ chiến lược "Cô lập Sự phức tạp":
 * - Kiến trúc STD (>90% chức năng): Request-response đơn giản
 * - KHÔNG sử dụng real-time listeners (onSnapshot)
 * - Tải dữ liệu một lần khi cần thiết
 *
 * Constitution compliance: HP-06 (Kiến trúc Hướng Dịch vụ)
 */

import { ref } from 'vue';
import { getFirestore, collection, getDocs, query } from 'firebase/firestore';

import { firebaseApp } from './config.js';
import { useAuth } from './authService.js';
import { useEnvironmentSelector } from './environmentSelector.js';

const USE_MOCK_DATA = import.meta.env.VITE_KNOWLEDGE_TREE_MOCK === 'true';

const MOCK_DOCUMENTS = [
  {
    id: 'knowledge-root',
    title: 'Dự án Incomex Corp',
    status: 'green',
    parent: null,
    order: 1,
  },
  {
    id: 'planning-docs',
    title: 'Tài liệu Kế hoạch',
    status: 'green',
    parent: 'knowledge-root',
    order: 2,
  },
  {
    id: 'sales-enablement',
    title: 'Sales Enablement',
    status: 'yellow',
    parent: 'knowledge-root',
    order: 3,
  },
  {
    id: 'app-service-plan',
    title: 'APP Service Plan v6.0.docx',
    status: 'green',
    parent: 'planning-docs',
    order: 1,
  },
  {
    id: 'training-kit',
    title: 'Bộ tài liệu đào tạo',
    status: 'red',
    parent: 'sales-enablement',
    order: 1,
  },
];

/**
 * Transforms a flat list of documents (with parentId) into a hierarchical tree structure.
 * @param {Array} items - The flat list of documents from Firestore.
 * @returns {Array} The structured tree data.
 */
function buildTree(items) {
  const tree = [];
  const map = new Map();

  items.forEach(rawItem => {
    const parentId = rawItem.parentId ?? rawItem.parent ?? null;
    const item = {
      ...rawItem,
      parentId,
      children: [],
    };
    map.set(item.id, item);
  });

  const sortNodes = nodes => {
    nodes.sort((a, b) => {
      const aOrder = a.order ?? a.position ?? 0;
      const bOrder = b.order ?? b.position ?? 0;
      if (aOrder !== bOrder) return aOrder - bOrder;
      const aTitle = a.title ?? '';
      const bTitle = b.title ?? '';
      return aTitle.localeCompare(bTitle, 'vi', { sensitivity: 'base' });
    });

    nodes.forEach(child => {
      if (child.children.length > 0) {
        sortNodes(child.children);
      }
    });
  };

  map.forEach(item => {
    if (item.parentId && map.has(item.parentId)) {
      map.get(item.parentId).children.push(item);
    } else {
      tree.push(item);
    }
  });

  sortNodes(tree);

  return tree;
}

/**
 * STD Architecture: Fetch data once using request-response pattern
 * NO real-time listeners (onSnapshot)
 *
 * @param {Array} collectionNames - List of collection names to fetch from
 * @returns {Promise<Array>} Array of documents
 */
async function fetchKnowledgeDocuments(collectionNames) {
  const db = getFirestore(firebaseApp);
  const allDocs = [];

  // Fetch from each collection sequentially
  for (const collectionName of collectionNames) {
    try {
      const collectionRef = collection(db, collectionName);
      const q = query(collectionRef);
      const querySnapshot = await getDocs(q);

      querySnapshot.forEach((doc) => {
        allDocs.push({
          id: doc.id,
          ...doc.data(),
          _source: collectionName, // for debugging
        });
      });
    } catch (err) {
      console.error(`Error fetching from ${collectionName}:`, err);
      throw new Error(`Không thể tải dữ liệu từ ${collectionName}.`);
    }
  }

  return allDocs;
}

/**
 * Composable function to fetch and manage the knowledge tree from Firestore.
 *
 * STD ARCHITECTURE (>90% features):
 * - Request-response pattern ONLY
 * - NO real-time listeners
 * - Manual refresh via loadData() method
 *
 * @returns {{
 *   tree: import('vue').Ref<Array>,
 *   loading: import('vue').Ref<boolean>,
 *   error: import('vue').Ref<string | null>,
 *   loadData: () => Promise<void>,
 *   refresh: () => Promise<void>
 * }}
 */
export function useKnowledgeTree() {
  const tree = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Mock data mode
  if (USE_MOCK_DATA) {
    tree.value = buildTree(MOCK_DOCUMENTS);
    loading.value = false;
    error.value = null;

    return {
      tree,
      loading,
      error,
      loadData: async () => {}, // noop for mock
      refresh: async () => {},  // noop for mock
    };
  }

  const { user: authUser, isReady } = useAuth();
  const { collectionNames } = useEnvironmentSelector();

  /**
   * STD Architecture: Load data once using request-response
   * NO real-time subscriptions
   */
  const loadData = async () => {
    // Wait for auth to be ready
    if (!isReady.value) {
      error.value = 'Đang khởi tạo xác thực...';
      return;
    }

    // Check if user is authenticated
    if (!authUser.value) {
      tree.value = [];
      loading.value = false;
      error.value = 'Vui lòng đăng nhập để xem sơ đồ tri thức.';
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      // STD: Simple request-response, no listeners
      const documents = await fetchKnowledgeDocuments(collectionNames.value);
      tree.value = buildTree(documents);
      loading.value = false;
    } catch (err) {
      console.error('Error loading knowledge tree:', err);
      error.value = err.message || 'Không thể tải dữ liệu tri thức.';
      loading.value = false;
      tree.value = [];
    }
  };

  /**
   * Refresh data manually
   */
  const refresh = async () => {
    await loadData();
  };

  return {
    tree,
    loading,
    error,
    loadData,
    refresh,
  };
}
