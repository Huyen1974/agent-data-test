import { ref } from 'vue';

/**
 * A simple shared state for the currently selected document.
 */
const selectedDocument = ref(null);

/**
 * Composable to access and manage the selected knowledge document.
 * @returns {{
 *   selectedDocument: import('vue').Ref<Object | null>
 * }}
 */
export function useKnowledgeState() {
  return {
    selectedDocument,
  };
}
