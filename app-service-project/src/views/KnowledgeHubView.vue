<script setup>
import { ref, watch, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';

import WorkspaceLayout from '../layouts/WorkspaceLayout.vue';
import KnowledgeTree from '../components/KnowledgeTree.vue';
import ContentEditor from '../components/ContentEditor.vue';
import { useAuth } from '../firebase/authService.js';
import { useKnowledgeTree } from '../firebase/knowledgeService.js';

const route = useRoute();
const pageTitle = computed(() => route.meta?.title ?? 'Knowledge Hub');

const { isReady: isAuthReady } = useAuth();
const { tree, loading, error, loadData } = useKnowledgeTree();

const selectedDocument = ref(null);

// Track if data has been loaded to prevent duplicate loads
const hasLoadedData = ref(false);

// Function to handle item selection from the tree
const handleItemSelected = (item) => {
  selectedDocument.value = item;
};

// Unified function to load data (prevents race condition)
const loadDataOnce = async () => {
  if (hasLoadedData.value || !isAuthReady.value) {
    return;
  }
  hasLoadedData.value = true;
  await loadData();
};

// Load data when authentication is ready
onMounted(() => {
  loadDataOnce();
});

// Watch for auth readiness changes (handles async auth initialization)
watch(isAuthReady, (ready) => {
  if (ready) {
    loadDataOnce();
  }
});
</script>

<template>
  <WorkspaceLayout :title="pageTitle">
    <v-row>
      <!-- Knowledge Tree Panel -->
      <v-col cols="12" md="4" lg="3">
        <v-sheet rounded="lg" color="surface" elevation="0" class="pa-4" min-height="400">
          <!-- Loading State -->
          <div v-if="loading" class="d-flex justify-center align-center fill-height">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </div>

          <!-- Error State -->
          <div v-else-if="error">
            <v-alert type="error" variant="tonal" density="compact">
              {{ error }}
            </v-alert>
          </div>

          <!-- Empty State -->
          <div v-else-if="!tree.length" class="text-center text-medium-emphasis fill-height d-flex align-center justify-center">
            <div>
              <v-icon size="32" class="mb-2">mdi-database-off-outline</v-icon>
              <p class="text-body-2">Không có dữ liệu tri thức.</p>
            </div>
          </div>

          <!-- Tree View -->
          <KnowledgeTree
            v-else
            :items="tree"
            :selected-id="selectedDocument?.id"
            @item-selected="handleItemSelected"
            data-testid="knowledge-tree"
          />
        </v-sheet>
      </v-col>

      <!-- Content Editor Panel -->
      <v-col cols="12" md="8" lg="9">
        <ContentEditor :document="selectedDocument" />
      </v-col>
    </v-row>
  </WorkspaceLayout>
</template>

<style scoped>
.fill-height {
  min-height: 350px;
}
</style>
