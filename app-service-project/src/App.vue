<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { marked } from 'marked';

marked.setOptions({ gfm: true, breaks: true });

const API_BASE_URL = 'https://agent-data-test-service-pfne2mqwja-as.a.run.app';

const state = reactive({
  treeItems: [],
  isLoadingTree: false,
  treeError: '',
  active: [],
});

const contentState = reactive({
  isLoading: false,
  error: '',
  title: 'Chọn một tài liệu',
  bodyHtml:
    '<p class="text-body-2">Chọn một tài liệu trong cây tri thức để xem nội dung.</p>',
});

const isDrawerOpen = ref(true);

const userDisplayName = ref('Khách');

const flatNodes = computed(() => {
  const result = new Map();
  const stack = [...state.treeItems];
  while (stack.length) {
    const node = stack.pop();
    if (!node) continue;
    result.set(node.id, node);
    if (Array.isArray(node.children) && node.children.length) {
      stack.push(...node.children);
    }
  }
  return result;
});

function normaliseTree(items = []) {
  return items.map((item) => {
    const documentId = item.source_document_id || inferDocumentId(item.id);
    return {
      id: item.id,
      title: item.title,
      documentId,
      children: normaliseTree(item.children || []),
    };
  });
}

function inferDocumentId(identifier) {
  return typeof identifier === 'string' && identifier.includes('-')
    ? identifier
    : null;
}

async function fetchTree() {
  state.isLoadingTree = true;
  state.treeError = '';
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-tree`);
    if (!response.ok) {
      throw new Error(`Fetch tree failed with status ${response.status}`);
    }
    const payload = await response.json();
    state.treeItems = normaliseTree(payload?.tree ?? []);
    if (!state.treeItems.length) {
      state.treeError = 'Không tìm thấy dữ liệu cây tri thức.';
    }
  } catch (error) {
    console.error('Failed to load tree', error);
    state.treeError = 'Không thể tải cây tri thức. Vui lòng thử lại sau.';
    state.treeItems = [];
  } finally {
    state.isLoadingTree = false;
  }
}

async function loadDocumentContent(documentId, title) {
  if (!documentId) {
    contentState.title = title || 'Tài liệu';
    contentState.bodyHtml =
      '<p class="text-body-2">Không có nội dung để hiển thị cho mục đã chọn.</p>';
    return;
  }

  contentState.isLoading = true;
  contentState.error = '';
  contentState.title = title || 'Đang tải tài liệu...';

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/documents/${documentId}`
    );
    if (!response.ok) {
      throw new Error(`Document fetch failed with status ${response.status}`);
    }
    const data = await response.json();
    const body = data?.content?.body;
    if (!body) {
      contentState.bodyHtml =
        '<p class="text-body-2">Tài liệu không chứa nội dung hiển thị.</p>';
    } else {
      contentState.bodyHtml = marked.parse(body);
    }
    contentState.title = data?.metadata?.title || title || 'Tài liệu';
  } catch (error) {
    console.error('Failed to load document content', error);
    contentState.error = 'Không thể tải nội dung tài liệu từ backend.';
    contentState.bodyHtml = '';
  } finally {
    contentState.isLoading = false;
  }
}

watch(
  () => state.active,
  (active) => {
    if (!active?.length) {
      contentState.title = 'Chọn một tài liệu';
      contentState.bodyHtml =
        '<p class="text-body-2">Chọn một tài liệu trong cây tri thức để xem nội dung.</p>';
      contentState.error = '';
      return;
    }
    const node = flatNodes.value.get(active[0]);
    if (!node) return;
    if (!node.documentId) {
      contentState.title = node.title;
      contentState.bodyHtml =
        '<p class="text-body-2">Mục này không chứa tài liệu. Chọn một tập tin để xem nội dung.</p>';
      contentState.error = '';
      return;
    }
    loadDocumentContent(node.documentId, node.title);
  },
  { deep: false }
);

onMounted(() => {
  fetchTree();
});
</script>

<template>
  <v-app>
    <v-app-bar density="comfortable" color="white" elevate-on-scroll>
      <v-app-bar-nav-icon class="d-sm-none" @click="isDrawerOpen = !isDrawerOpen" />
      <v-toolbar-title class="text-primary font-weight-bold">Agent Data Console</v-toolbar-title>
      <v-spacer />
      <div class="d-flex align-center mr-4">
        <v-icon color="success" size="small">mdi-lightning-bolt</v-icon>
        <span class="text-caption ml-2">Live backend connected</span>
      </div>
      <v-chip
        prepend-icon="mdi-account-circle"
        color="primary"
        variant="tonal"
        class="text-body-2"
      >
        {{ userDisplayName }}
      </v-chip>
    </v-app-bar>

    <v-navigation-drawer
      v-model="isDrawerOpen"
      class="pa-0"
      :rail="false"
      :temporary="$vuetify.display.smAndDown"
      width="320"
    >
      <div class="pa-4">
        <h3 class="text-subtitle-1 font-weight-medium mb-1">Cây tri thức</h3>
        <p class="text-caption text-medium-emphasis mb-4">
          Chọn tài liệu để xem nội dung mới nhất từ backend.
        </p>
        <v-alert
          v-if="state.treeError"
          type="error"
          density="compact"
          class="mb-4"
        >
          {{ state.treeError }}
        </v-alert>
        <div v-if="state.isLoadingTree" class="d-flex justify-center py-6">
          <v-progress-circular indeterminate color="primary" />
        </div>
        <v-treeview
          v-else
          v-model:activated="state.active"
          :items="state.treeItems"
          item-title="title"
          item-value="id"
          activatable
          open-on-click
          :rounded="true"
          density="compact"
          color="primary"
        >
          <template #prepend="{ item }">
            <v-icon size="small" :color="item.children?.length ? 'primary' : 'grey-darken-2'">
              {{ item.children?.length ? 'mdi-folder-outline' : 'mdi-file-document-outline' }}
            </v-icon>
          </template>
        </v-treeview>
      </div>
    </v-navigation-drawer>

    <v-main class="bg-grey-lighten-5">
      <v-container class="py-8" fluid>
        <v-row>
          <v-col cols="12">
            <v-card elevation="2" class="pa-6">
              <div class="d-flex align-center justify-space-between mb-4">
                <div>
                  <h2 class="text-h5 font-weight-medium mb-1">{{ contentState.title }}</h2>
                  <p class="text-caption text-medium-emphasis">
                    Nội dung hiển thị trực tiếp từ Firestore (kb_documents).
                  </p>
                </div>
                <div class="d-flex align-center text-caption">
                  <v-icon color="primary" class="mr-1">mdi-database-outline</v-icon>
                  Revision live sync
                </div>
              </div>

              <v-alert
                v-if="contentState.error"
                type="error"
                density="comfortable"
                class="mb-4"
              >
                {{ contentState.error }}
              </v-alert>

              <div v-if="contentState.isLoading" class="py-10 text-center">
                <v-progress-circular indeterminate size="48" color="primary" />
              </div>

              <div
                v-else
                class="document-body"
                v-html="contentState.bodyHtml"
              />
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<style scoped>
.document-body {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: inset 0 0 0 1px rgba(25, 118, 210, 0.08);
  max-height: 65vh;
  overflow-y: auto;
}

.document-body :deep(h1),
.document-body :deep(h2),
.document-body :deep(h3) {
  color: #0d47a1;
  font-weight: 600;
}

.document-body :deep(pre) {
  background: #0d1117;
  color: #f8f8f2;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.document-body :deep(code) {
  background: rgba(25, 118, 210, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.document-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.document-body :deep(th),
.document-body :deep(td) {
  border: 1px solid rgba(33, 150, 243, 0.2);
  padding: 8px 12px;
  text-align: left;
}
</style>
