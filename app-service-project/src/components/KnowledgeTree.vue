<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  selectedId: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(['item-selected']);

const activated = ref([]);

// Watch for external changes to selectedId
watch(() => props.selectedId, (newId) => {
  activated.value = newId ? [newId] : [];
}, { immediate: true });

// Watch for user interaction with the tree
watch(activated, (newActivated) => {
  const newId = newActivated?.[0];
  if (newId && newId !== props.selectedId) {
    // Find the full item object to emit
    const findItem = (nodes, id) => {
      if (!nodes || !Array.isArray(nodes)) return null;

      for (const node of nodes) {
        if (node.id === id) return node;
        if (node.children) {
          const found = findItem(node.children, id);
          if (found) return found;
        }
      }
      return null;
    };

    try {
      const selectedItem = findItem(props.items, newId);
      if (selectedItem) {
        emit('item-selected', selectedItem);
      } else {
        console.warn(`[KnowledgeTree] Item with id "${newId}" not found in tree`);
      }
    } catch (error) {
      console.error('[KnowledgeTree] Error finding selected item:', error);
    }
  }
});
</script>

<template>
  <v-treeview
    v-model:activated="activated"
    :items="items"
    item-title="title"
    item-value="id"
    item-children="children"
    density="compact"
    activatable
    return-object="false"
  >
    <template #prepend="{ item }">
      <v-icon
        v-if="item.status === 'green'"
        color="success"
        size="small"
        class="me-1"
      >
        mdi-circle-slice-8
      </v-icon>
      <v-icon
        v-else-if="item.status === 'yellow'"
        color="warning"
        size="small"
        class="me-1"
      >
        mdi-circle-slice-3
      </v-icon>
      <v-icon
        v-else-if="item.status === 'red'"
        color="error"
        size="small"
        class="me-1"
      >
        mdi-alert-circle-outline
      </v-icon>
    </template>
  </v-treeview>
</template>
