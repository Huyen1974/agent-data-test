<script setup>
import { computed, ref } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  document: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['approve-suggestion', 'reject-suggestion']);

// Track processing state
const isProcessing = ref(false);

// Check if document has AI suggestions pending approval
const hasPendingSuggestion = computed(() => {
  return props.document?.aiSuggestion && props.document?.aiSuggestion.status === 'pending';
});

// Render current content
const renderedContent = computed(() => {
  if (props.document && props.document.content) {
    return DOMPurify.sanitize(marked(props.document.content));
  }
  return '';
});

// Render suggested content
const renderedSuggestion = computed(() => {
  if (hasPendingSuggestion.value && props.document.aiSuggestion.suggestedContent) {
    return DOMPurify.sanitize(marked(props.document.aiSuggestion.suggestedContent));
  }
  return '';
});

// STD Architecture: Request-response pattern for approval actions
async function handleApprove() {
  if (!hasPendingSuggestion.value || isProcessing.value) return;

  isProcessing.value = true;
  try {
    await emit('approve-suggestion', {
      documentId: props.document.id,
      suggestionId: props.document.aiSuggestion.id,
    });
  } finally {
    isProcessing.value = false;
  }
}

async function handleReject() {
  if (!hasPendingSuggestion.value || isProcessing.value) return;

  isProcessing.value = true;
  try {
    await emit('reject-suggestion', {
      documentId: props.document.id,
      suggestionId: props.document.aiSuggestion.id,
    });
  } finally {
    isProcessing.value = false;
  }
}
</script>

<template>
  <v-sheet class="pa-6" rounded="lg" color="surface" elevation="0" min-height="400">
    <div v-if="document">
      <h1 class="text-h4 mb-4">{{ document.title }}</h1>

      <!-- AI Suggestion Approval Banner -->
      <v-alert
        v-if="hasPendingSuggestion"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon size="small" class="me-2">mdi-robot</v-icon>
            <span class="text-body-2">AI đã đề xuất thay đổi nội dung</span>
          </div>
          <div class="d-flex ga-2">
            <v-btn
              size="small"
              color="success"
              variant="flat"
              :loading="isProcessing"
              @click="handleApprove"
            >
              <v-icon start>mdi-check</v-icon>
              Chấp thuận
            </v-btn>
            <v-btn
              size="small"
              color="error"
              variant="outlined"
              :loading="isProcessing"
              @click="handleReject"
            >
              <v-icon start>mdi-close</v-icon>
              Từ chối
            </v-btn>
          </div>
        </div>
      </v-alert>

      <!-- Diff View: Current vs Suggested -->
      <div v-if="hasPendingSuggestion" class="mb-6">
        <v-row>
          <v-col cols="12" md="6">
            <div class="diff-panel diff-current">
              <div class="diff-header">
                <v-icon size="small" class="me-2">mdi-file-document</v-icon>
                <span class="text-subtitle-2 font-weight-medium">Nội dung hiện tại</span>
              </div>
              <div class="diff-content prose" v-html="renderedContent"></div>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="diff-panel diff-suggested">
              <div class="diff-header">
                <v-icon size="small" class="me-2">mdi-robot</v-icon>
                <span class="text-subtitle-2 font-weight-medium">Nội dung đề xuất</span>
              </div>
              <div class="diff-content prose" v-html="renderedSuggestion"></div>
            </div>
          </v-col>
        </v-row>
      </div>

      <!-- Regular Content View (when no pending suggestions) -->
      <div v-else class="prose" v-html="renderedContent"></div>
    </div>
    <div v-else class="d-flex align-center justify-center fill-height">
      <div class="text-center text-medium-emphasis">
        <v-icon size="48" class="mb-2">mdi-file-document-outline</v-icon>
        <p>Chọn một tài liệu từ cây thư mục để xem nội dung.</p>
      </div>
    </div>
  </v-sheet>
</template>

<style scoped>
.fill-height {
  min-height: 350px;
}

.prose {
  line-height: 1.7;
}

/* Diff Panel Styling */
.diff-panel {
  border: 2px solid;
  border-radius: 8px;
  overflow: hidden;
  height: 100%;
}

.diff-current {
  border-color: #f44336; /* red - for deletion/current */
  background: rgba(244, 67, 54, 0.02);
}

.diff-suggested {
  border-color: #4caf50; /* green - for addition/suggested */
  background: rgba(76, 175, 80, 0.02);
}

.diff-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.03);
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.diff-content {
  padding: 16px;
  max-height: 600px;
  overflow-y: auto;
}

/* Basic styling for rendered HTML content */
.prose :deep(h1),
.prose :deep(h2),
.prose :deep(h3) {
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  font-weight: 600;
}

.prose :deep(p) {
  margin-bottom: 1em;
}

.prose :deep(ul),
.prose :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 1em;
}

.prose :deep(li) {
  margin-bottom: 0.5em;
}

.prose :deep(code) {
  background-color: rgba(0,0,0,0.05);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}

.prose :deep(pre) {
  background-color: #f5f5f5;
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
}

.prose :deep(pre) code {
  background-color: transparent;
  padding: 0;
}
</style>
