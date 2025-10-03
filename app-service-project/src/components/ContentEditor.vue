<script setup>
import { computed } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  document: {
    type: Object,
    default: null,
  },
});

const renderedContent = computed(() => {
  if (props.document && props.document.content) {
    // Use marked to convert Markdown to HTML
    return marked(props.document.content);
  }
  return '';
});
</script>

<template>
  <v-sheet class="pa-6" rounded="lg" color="surface" elevation="0" min-height="400">
    <div v-if="document">
      <h1 class="text-h4 mb-4">{{ document.title }}</h1>
      <div class="prose" v-html="renderedContent"></div>
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