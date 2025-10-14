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
    // Reset all mocks to initial state
    mockAuthReady.value = true;
    mockTree.value = [
      { id: 'doc-1', title: 'Document 1', status: 'green' }
    ];
    mockLoading.value = false;
    mockError.value = null;
    loadDataSpy.mockClear();
    loadDataSpy.mockResolvedValue();
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

  it('prevents duplicate loadData calls (race condition fix)', async () => {
    // Start with auth not ready
    mockAuthReady.value = false;
    const wrapper = mount(KnowledgeHubView);
    await flushPromises();

    // loadData should not be called yet
    expect(loadDataSpy).not.toHaveBeenCalled();

    // Now make auth ready - this triggers the watch
    mockAuthReady.value = true;
    await flushPromises();

    // loadData should be called exactly once, not twice
    // (without the fix, both onMounted and watch would call loadData)
    expect(loadDataSpy).toHaveBeenCalledTimes(1);

    // Even if auth changes multiple times, loadData should still be called only once
    mockAuthReady.value = false;
    await flushPromises();
    mockAuthReady.value = true;
    await flushPromises();

    expect(loadDataSpy).toHaveBeenCalledTimes(1);
  });

  it('does not call loadData when auth is not ready', async () => {
    mockAuthReady.value = false;
    mount(KnowledgeHubView);
    await flushPromises();

    expect(loadDataSpy).not.toHaveBeenCalled();
  });

  it('only loads data once even when mounted with auth already ready', async () => {
    // Explicitly clear the spy before this test to ensure clean state
    loadDataSpy.mockClear();

    // Auth is ready from the start
    mockAuthReady.value = true;
    mount(KnowledgeHubView);
    await flushPromises();

    // Should be called exactly once (the guard prevents duplicate calls)
    // This verifies that both onMounted and watch don't both trigger loadData
    expect(loadDataSpy).toHaveBeenCalledTimes(1);
  });

  it('shows loading state while data is being fetched', async () => {
    mockLoading.value = true;
    const wrapper = mount(KnowledgeHubView);
    await flushPromises();

    expect(wrapper.find('[data-testid="knowledge-tree"]').exists()).toBe(false);
    expect(wrapper.text()).toContain(''); // Loading spinner has no text
  });

  it('shows error state when data fetch fails', async () => {
    mockError.value = 'Failed to load knowledge tree';
    const wrapper = mount(KnowledgeHubView);
    await flushPromises();

    expect(wrapper.text()).toContain('Failed to load knowledge tree');
  });

  it('shows empty state when tree has no items', async () => {
    mockTree.value = [];
    const wrapper = mount(KnowledgeHubView);
    await flushPromises();

    expect(wrapper.text()).toContain('Không có dữ liệu tri thức');
  });
});
