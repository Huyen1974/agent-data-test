import { ref, onUnmounted } from 'vue';
import { getFirestore, collection, onSnapshot } from 'firebase/firestore';
import { firebaseApp } from './config.js';

/**
 * Transforms a flat list of documents (with parentId) into a hierarchical tree structure.
 * @param {Array} items - The flat list of documents from Firestore.
 * @returns {Array} The structured tree data.
 */
function buildTree(items) {
  const tree = [];
  const map = {};

  // First, map all items by their ID
  items.forEach(item => {
    map[item.id] = { ...item, children: [] };
  });

  // Then, build the tree by assigning children to their parents
  Object.values(map).forEach(item => {
    if (item.parentId && map[item.parentId]) {
      map[item.parentId].children.push(item);
    } else {
      // If no parentId or parent not found, it's a root node
      tree.push(item);
    }
  });

  return tree;
}

/**
 * Composable function to fetch and manage the knowledge tree from Firestore.
 *
 * @returns {{
 *   tree: import('vue').Ref<Array>,
 *   loading: import('vue').Ref<boolean>,
 *   error: import('vue').Ref<string | null>
 * }}
 */
export function useKnowledgeTree() {
  const db = getFirestore(firebaseApp);
  const tree = ref([]);
  const loading = ref(true);
  const error = ref(null);

  // Timeout to prevent infinite loading state in case of connection issues
  const loadingTimeout = setTimeout(() => {
    if (loading.value) {
      console.warn("Firestore connection timed out.");
      error.value = "Lỗi kết nối tới kho tri thức.";
      loading.value = false;
    }
  }, 8000);

  const unsubscribe = onSnapshot(
    collection(db, 'knowledge_documents'),
    (snapshot) => {
      clearTimeout(loadingTimeout);
      error.value = null;
      const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      tree.value = buildTree(items);
      loading.value = false;
    },
    (err) => {
      clearTimeout(loadingTimeout);
      console.error("Error fetching knowledge documents:", err);
      error.value = "Không thể tải sơ đồ tri thức.";
      loading.value = false;
    }
  );

  // Stop listening for updates when the component is unmounted
  onUnmounted(() => {
    unsubscribe();
    clearTimeout(loadingTimeout);
  });

  return { tree, loading, error };
}
