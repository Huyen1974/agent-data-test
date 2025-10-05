<script setup>
import { computed, ref, watch } from 'vue';
import { useDisplay } from 'vuetify';
import { useKnowledgeTree } from '../firebase/knowledgeService.js';
import { useKnowledgeState } from '../firebase/knowledgeState.js';

const props = defineProps({
  title: {
    type: String,
    default: 'Action Toolbar',
  },
});

const { tree, loading, error } = useKnowledgeTree();
const { selectedDocument } = useKnowledgeState();

// Local state for the v-treeview's activated node
const activatedNode = ref([]);
const openedNodes = ref([]);

const display = useDisplay();
const isMobile = computed(() => display.smAndDown.value);
const drawer = ref(!isMobile.value);

watch(isMobile, (value) => {
  drawer.value = !value;
});

// Helper function to find a node in the tree by its ID
function findNodeById(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findNodeById(node.children, id);
      if (found) return found;
    }
  }
  return null;
}

// Watch for changes in the activated node and update the shared state
const collectExpandableNodes = (nodes, bucket) => {
  nodes.forEach(node => {
    if (node.children?.length) {
      bucket.push(node.id);
      collectExpandableNodes(node.children, bucket);
    }
  });
};

const findFirstLeaf = (nodes) => {
  for (const node of nodes) {
    if (!node.children || node.children.length === 0) {
      return node;
    }
    const child = findFirstLeaf(node.children);
    if (child) {
      return child;
    }
  }
  return null;
};

watch(tree, (newTree) => {
  const expanded = [];
  collectExpandableNodes(newTree, expanded);
  openedNodes.value = expanded;

  if (activatedNode.value.length === 0) {
    const firstLeaf = findFirstLeaf(newTree);
    activatedNode.value = firstLeaf ? [firstLeaf.id] : [];
  }
}, { deep: true });

watch(activatedNode, (newVal) => {
  if (newVal.length > 0) {
    const nodeId = newVal[0];
    const node = findNodeById(tree.value, nodeId);
    selectedDocument.value = node ?? null;
  } else {
    selectedDocument.value = null;
  }
}, { deep: true });

function toggleDrawer() {
  drawer.value = !drawer.value;
}

function getStatusColor(status) {
  switch (status) {
    case 'green':
      return 'success';
    case 'yellow':
      return 'warning';
    case 'red':
      return 'error';
    default:
      return 'grey';
  }
}
</script>

<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!isMobile"
      :temporary="isMobile"
      class="workspace-drawer"
      width="280"
      app
    >
      <v-toolbar density="compact" flat class="px-4">
        <v-toolbar-title class="text-subtitle-2 font-weight-medium">
          Danh mục
        </v-toolbar-title>
      </v-toolbar>
      <v-divider />
      <div class="drawer-scroll pa-2">
        <div v-if="loading" class="text-center pa-4">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
        </div>
        <v-alert v-else-if="error" type="error" density="compact" variant="tonal">
          {{ error }}
        </v-alert>
        <div v-else data-testid="knowledge-tree">
          <v-treeview
            v-model:activated="activatedNode"
            v-model:opened="openedNodes"
            :items="tree"
            activatable
            open-all
            density="compact"
            item-title="title"
            item-value="id"
            open-on-click
            color="primary"
          >
            <template v-slot:item="{ props, item }">
              <div v-bind="props" class="d-flex align-center">
                <v-icon
                  :color="getStatusColor(item.raw.status)"
                  size="x-small"
                  class="me-2"
                >
                  mdi-circle
                </v-icon>
                <span>{{ item.title }}</span>
              </div>
            </template>
          </v-treeview>
        </div>
      </div>
    </v-navigation-drawer>

    <v-main class="workspace-main">
      <v-toolbar density="compact" flat class="workspace-toolbar">
        <v-btn
          v-if="isMobile"
          icon="mdi-menu"
          variant="text"
          density="compact"
          class="me-2"
          @click="toggleDrawer"
        />
        <v-toolbar-title class="text-subtitle-2 font-weight-medium">
          {{ title }}
        </v-toolbar-title>
        <v-spacer />
        <slot name="toolbar-actions">
          <v-btn density="compact" variant="tonal">Thao tác mẫu</v-btn>
        </slot>
      </v-toolbar>

      <div class="workspace-wrapper">
        <slot>
          <div class="content-placeholder text-body-2 text-medium-emphasis">
            Nội dung khu vực làm việc (placeholder).
          </div>
        </slot>
      </div>
    </v-main>
  </v-app>
</template>

<style scoped>
.workspace-drawer {
  border-right: 1px solid rgba(0, 0, 0, 0.08);
}

.drawer-scroll {
  height: calc(100% - 49px);
  overflow-y: auto;
  padding: 8px 4px 16px;
}

.workspace-main {
  background: #f4f6fb;
}

.workspace-toolbar {
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.workspace-wrapper {
  min-height: calc(100vh - 49px);
  padding: 24px;
}

.content-placeholder {
  background: #ffffff;
  border: 1px dashed rgba(25, 118, 210, 0.4);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
}

.auth-controls {
  gap: 8px;
}
</style>
