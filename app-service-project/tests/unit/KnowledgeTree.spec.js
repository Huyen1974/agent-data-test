import { describe, it, expect } from 'vitest';
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
});
