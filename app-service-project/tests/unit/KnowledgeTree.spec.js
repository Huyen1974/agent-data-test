import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import KnowledgeTree from '@/components/KnowledgeTree.vue';

const buildTree = () => ([
  {
    id: 'root',
    title: 'Root',
    status: 'green',
    children: [
      {
        id: 'child-1',
        title: 'Child 1',
        status: 'yellow'
      },
      {
        id: 'child-2',
        title: 'Child 2',
        status: 'red'
      }
    ]
  }
]);

describe('KnowledgeTree', () => {
  it('activates node that matches selectedId prop', async () => {
    const wrapper = mount(KnowledgeTree, {
      props: {
        items: buildTree(),
        selectedId: 'child-1'
      }
    });

    await nextTick();
    expect(wrapper.vm.activated).toEqual(['child-1']);

    await wrapper.setProps({ selectedId: 'child-2' });
    await nextTick();
    expect(wrapper.vm.activated).toEqual(['child-2']);
  });

  it('emits item-selected when user activates a different node', async () => {
    const wrapper = mount(KnowledgeTree, {
      props: {
        items: buildTree(),
        selectedId: 'root'
      }
    });

    await nextTick();

    wrapper.vm.activated = ['child-1'];
    await nextTick();

    const emitted = wrapper.emitted('item-selected');
    expect(emitted).toBeTruthy();
    expect(emitted[0][0]).toMatchObject({ id: 'child-1', title: 'Child 1' });
  });

  it('handles null or undefined items array gracefully', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const wrapper = mount(KnowledgeTree, {
      props: {
        items: null,
        selectedId: null
      }
    });

    await nextTick();

    // Activate a node when items is null
    wrapper.vm.activated = ['some-id'];
    await nextTick();

    // Should not emit anything and should warn
    expect(wrapper.emitted('item-selected')).toBeFalsy();
    expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining('not found in tree'));

    consoleWarnSpy.mockRestore();
  });

  it('warns when activated node ID is not found in tree', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const wrapper = mount(KnowledgeTree, {
      props: {
        items: buildTree(),
        selectedId: 'root'
      }
    });

    await nextTick();

    // Activate a non-existent node
    wrapper.vm.activated = ['non-existent-id'];
    await nextTick();

    // Should not emit anything and should warn
    expect(wrapper.emitted('item-selected')).toBeFalsy();
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      '[KnowledgeTree] Item with id "non-existent-id" not found in tree'
    );

    consoleWarnSpy.mockRestore();
  });

  it('does not emit when activated node is same as selectedId', async () => {
    const wrapper = mount(KnowledgeTree, {
      props: {
        items: buildTree(),
        selectedId: 'child-1'
      }
    });

    await nextTick();

    // Activate the same node that's already selected
    wrapper.vm.activated = ['child-1'];
    await nextTick();

    // Should not emit because it's the same as selectedId
    expect(wrapper.emitted('item-selected')).toBeFalsy();
  });
});
