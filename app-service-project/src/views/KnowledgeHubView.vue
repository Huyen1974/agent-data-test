<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import WorkspaceLayout from '../layouts/WorkspaceLayout.vue';
import ContentEditor from '../components/ContentEditor.vue';
import { useKnowledgeState } from '../firebase/knowledgeState.js';

const route = useRoute();
const { selectedDocument } = useKnowledgeState();

const pageTitle = computed(() => route.meta?.title ?? 'Knowledge Hub');
</script>

<template>
  <WorkspaceLayout :title="pageTitle">
    <template #toolbar-actions>
      <v-btn density="compact" variant="tonal">Tác vụ chính</v-btn>
      <v-btn density="compact" variant="outlined" class="ms-2">Tác vụ phụ</v-btn>
    </template>

    <ContentEditor :document="selectedDocument" />
  </WorkspaceLayout>
</template>
