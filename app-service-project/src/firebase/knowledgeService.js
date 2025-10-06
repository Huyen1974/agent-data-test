import { ref, onUnmounted, watch } from 'vue';
import { getFirestore, collection, onSnapshot } from 'firebase/firestore';
import { onAuthStateChanged } from 'firebase/auth';

import { firebaseApp, auth } from './config.js';
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
 * Composable function to fetch and manage the knowledge tree from Firestore.
 * Implements Constitution-compliant strategy (QD-LAW §2) using separate collections.
 *
 * @returns {{
 *   tree: import('vue').Ref<Array>,
 *   loading: import('vue').Ref<boolean>,
 *   error: import('vue').Ref<string | null>
 * }}
 */
export function useKnowledgeTree() {
  const tree = ref([]);
  const loading = ref(true);
  const error = ref(null);

  if (USE_MOCK_DATA) {
    tree.value = buildTree(MOCK_DOCUMENTS);
    loading.value = false;
    error.value = null;

    return { tree, loading, error };
  }

  const db = getFirestore(firebaseApp);
  const { collectionNames } = useEnvironmentSelector();

  let unsubscribeSnapshots = [];
  let loadingTimeout = null;
  let currentUser = null;

  const resetSubscriptions = () => {
    unsubscribeSnapshots.forEach(unsub => unsub());
    unsubscribeSnapshots = [];
    if (loadingTimeout) {
      clearTimeout(loadingTimeout);
      loadingTimeout = null;
    }
  };

  const startSubscriptions = (user, collections) => {
    resetSubscriptions();
    currentUser = user;

    if (!user) {
      tree.value = [];
      loading.value = false;
      error.value = "Vui lòng đăng nhập để xem sơ đồ tri thức.";
      return;
    }

    loading.value = true;
    error.value = null;

    loadingTimeout = setTimeout(() => {
      if (loading.value) {
        console.warn('Firestore connection timed out.');
        error.value = 'Lỗi kết nối tới kho tri thức.';
        loading.value = false;
      }
    }, 8000);

    // Aggregate documents from multiple collections
    const allDocs = new Map();
    let completedCollections = 0;

    collections.forEach(collectionName => {
      const collectionRef = collection(db, collectionName);
      const unsub = onSnapshot(
        collectionRef,
        (snapshot) => {
          // Store documents with collection info for debugging
          snapshot.docs.forEach(doc => {
            allDocs.set(doc.id, {
              id: doc.id,
              ...doc.data(),
              _source: collectionName, // for debugging
            });
          });

          completedCollections++;

          // Only update tree when all collections have loaded
          if (completedCollections >= collections.length) {
            clearTimeout(loadingTimeout);
            error.value = null;
            const items = Array.from(allDocs.values());
            tree.value = buildTree(items);
            loading.value = false;
          }
        },
        (err) => {
          clearTimeout(loadingTimeout);
          console.error(`Error fetching from ${collectionName}:`, err);
          error.value = `Không thể tải dữ liệu từ ${collectionName}.`;
          loading.value = false;
        }
      );
      unsubscribeSnapshots.push(unsub);
    });
  };

  // Watch for auth changes
  const unsubscribeAuth = onAuthStateChanged(auth, (user) => {
    startSubscriptions(user, collectionNames.value);
  });

  // Watch for environment changes and restart subscriptions
  watch(collectionNames, (newCollections) => {
    if (currentUser) {
      startSubscriptions(currentUser, newCollections);
    }
  });

  onUnmounted(() => {
    resetSubscriptions();
    unsubscribeAuth();
  });

  return { tree, loading, error };
}
