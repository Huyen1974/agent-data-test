import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { ref } from 'vue';
import KnowledgeHubView from '@/views/KnowledgeHubView.vue';

const mockAuthReady = ref(true);
const loadDataSpy = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({
    meta: { title: 'Mock Knowledge Hub' }
  })
}));

vi.mock('@/firebase/authService.js', () => ({
  useAuth: () => ({
    isReady: mockAuthReady
  })
}));

const mockTree = ref([
  { id: 'doc-1', title: 'Document 1', status: 'green' },
  { id: 'doc-2', title: 'Document 2', status: 'yellow' }
]);

const mockLoading = ref(false);
const mockError = ref(null);

vi.mock('@/firebase/knowledgeService.js', () => ({
  useKnowledgeTree: () => ({
    tree: mockTree,
    loading: mockLoading,
    error: mockError,
    loadData: loadDataSpy
  })
}));

vi.mock('@/layouts/WorkspaceLayout.vue', () => ({
  default: {
    name: 'WorkspaceLayout',
    props: ['title'],
    template: '<div data-testid="workspace-layout"><slot /></div>'
  }
}));

vi.mock('@/components/KnowledgeTree.vue', () => ({
  default: {
    name: 'KnowledgeTree',
    props: ['items', 'selectedId'],
    emits: ['item-selected'],
    template: `
      <div data-testid="knowledge-tree" @click="$emit('item-selected', items[0])">
        <slot></slot>
      </div>
    `
  }
}));

vi.mock('@/components/ContentEditor.vue', () => ({
  default: {
    name: 'ContentEditor',
    props: ['document'],
    template: '<div data-testid="content-editor">{{ document ? document.title : "empty" }}</div>'
  }
}));

describe('KnowledgeHubView', () => {
  beforeEach(() => {
    mockAuthReady.value = true;
    mockTree.value = [
      { id: 'doc-1', title: 'Document 1', status: 'green' }
    ];
    mockLoading.value = false;
    mockError.value = null;
    loadDataSpy.mockClear();
  });

  it('loads knowledge tree data once when auth is ready', async () => {
    mount(KnowledgeHubView);
    await flushPromises();

    expect(loadDataSpy).toHaveBeenCalledTimes(1);
  });

  it('loads data when auth transitions from not ready to ready', async () => {
    mockAuthReady.value = false;
    mount(KnowledgeHubView);

    await flushPromises();
    expect(loadDataSpy).not.toHaveBeenCalled();

    mockAuthReady.value = true;
    await flushPromises();

    expect(loadDataSpy).toHaveBeenCalledTimes(1);
  });

  it('passes selected document to content editor when tree emits selection', async () => {
    const wrapper = mount(KnowledgeHubView);
    await flushPromises();

    await wrapper.find('[data-testid="knowledge-tree"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="content-editor"]').text()).toContain('Document 1');
  });
});
