<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import WorkspaceLayout from '../layouts/WorkspaceLayout.vue';

const route = useRoute();

const pageTitle = computed(() => route.meta?.title ?? 'Knowledge Hub');
const placeholderDescription = computed(
  () => route.meta?.description ?? 'Nội dung đang được xây dựng.'
);
</script>

<template>
  <WorkspaceLayout :title="pageTitle">
    <template #toolbar-actions>
      <v-btn density="compact" variant="tonal">Tác vụ chính</v-btn>
      <v-btn density="compact" variant="outlined" class="ms-2">Tác vụ phụ</v-btn>
    </template>

    <v-sheet class="pa-6" rounded="lg" color="surface" elevation="0">
      <h2 class="text-h6 mb-2">{{ pageTitle }}</h2>
      <p class="text-body-2 text-medium-emphasis">
        {{ placeholderDescription }}
      </p>
      <p class="text-body-2 mt-4">
        Khu vực này dành cho nội dung chi tiết của từng phân khu. Hãy cập nhật
        theo tài liệu quy hoạch khi có thông tin cụ thể.
      </p>
    </v-sheet>
  </WorkspaceLayout>
</template>
