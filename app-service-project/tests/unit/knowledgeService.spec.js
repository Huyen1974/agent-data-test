import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';

// Mock Firebase
const mockGetDocs = vi.fn();
const mockCollection = vi.fn();
const mockQuery = vi.fn();

vi.mock('firebase/firestore', () => ({
  getFirestore: vi.fn(() => ({})),
  collection: (...args) => mockCollection(...args),
  query: (...args) => mockQuery(...args),
  getDocs: (...args) => mockGetDocs(...args),
}));

// Mock auth service
const mockUser = ref(null);
const mockIsReady = ref(false);

vi.mock('@/firebase/authService.js', () => ({
  useAuth: () => ({
    user: mockUser,
    isReady: mockIsReady,
  }),
}));

// Mock environment selector
const mockCollectionNames = ref(['test_documents']);

vi.mock('@/firebase/environmentSelector.js', () => ({
  useEnvironmentSelector: () => ({
    collectionNames: mockCollectionNames,
  }),
}));

// Mock Firebase app
vi.mock('@/firebase/config.js', () => ({
  firebaseApp: {},
}));

describe('knowledgeService', () => {
  let useKnowledgeTree;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Reset refs
    mockUser.value = { uid: '123', email: 'test@example.com' };
    mockIsReady.value = true;
    mockCollectionNames.value = ['test_documents'];

    // Reset module to get fresh instance
    vi.resetModules();
    const module = await import('@/firebase/knowledgeService.js');
    useKnowledgeTree = module.useKnowledgeTree;
  });

  describe('loadData', () => {
    it('should wait if auth is not ready', async () => {
      mockIsReady.value = false;
      const { loadData, error } = useKnowledgeTree();

      await loadData();

      expect(error.value).toBe('Đang khởi tạo xác thực...');
      expect(mockGetDocs).not.toHaveBeenCalled();
    });

    it('should show error if user is not authenticated', async () => {
      mockUser.value = null;
      const { loadData, error, tree } = useKnowledgeTree();

      await loadData();

      expect(error.value).toBe('Vui lòng đăng nhập để xem sơ đồ tri thức.');
      expect(tree.value).toEqual([]);
      expect(mockGetDocs).not.toHaveBeenCalled();
    });

    it('should successfully load documents', async () => {
      const mockDocs = [
        {
          id: 'doc1',
          data: () => ({ title: 'Document 1', status: 'green', parent: null, order: 1 })
        },
        {
          id: 'doc2',
          data: () => ({ title: 'Document 2', status: 'yellow', parent: 'doc1', order: 2 })
        },
      ];

      mockGetDocs.mockResolvedValue({
        size: 2,
        forEach: (callback) => mockDocs.forEach(callback),
      });

      const { loadData, tree, loading, error } = useKnowledgeTree();

      await loadData();

      expect(mockGetDocs).toHaveBeenCalled();
      expect(error.value).toBeNull();
      expect(loading.value).toBe(false);
      expect(tree.value.length).toBeGreaterThan(0);
    });

    it('should handle permission-denied error', async () => {
      const permissionError = new Error('Permission denied');
      permissionError.code = 'permission-denied';
      mockGetDocs.mockRejectedValue(permissionError);

      const { loadData, error } = useKnowledgeTree();

      await loadData();

      expect(error.value).toContain('Không có quyền truy cập');
      expect(error.value).toContain('test_documents');
    });

    it('should handle unavailable error', async () => {
      const unavailableError = new Error('Unavailable');
      unavailableError.code = 'unavailable';
      mockGetDocs.mockRejectedValue(unavailableError);

      const { loadData, error } = useKnowledgeTree();

      await loadData();

      expect(error.value).toContain('Không thể kết nối');
      expect(error.value).toContain('mạng');
    });

    it('should continue when collection not found', async () => {
      const notFoundError = new Error('Not found');
      notFoundError.code = 'not-found';
      mockGetDocs.mockRejectedValue(notFoundError);

      mockCollectionNames.value = ['test_documents', 'production_documents'];

      const { loadData, error, tree } = useKnowledgeTree();

      await loadData();

      // Should show empty data message, not throw error
      expect(error.value).toContain('Chưa có dữ liệu');
      expect(tree.value).toEqual([]);
    });

    it('should show message when no documents found', async () => {
      mockGetDocs.mockResolvedValue({
        size: 0,
        forEach: () => {},
      });

      const { loadData, error, tree } = useKnowledgeTree();

      await loadData();

      expect(error.value).toContain('Chưa có dữ liệu tri thức');
      expect(tree.value).toEqual([]);
    });

    it('should handle multiple collections', async () => {
      mockCollectionNames.value = ['test_documents', 'production_documents'];

      const mockTestDocs = [
        {
          id: 'test1',
          data: () => ({ title: 'Test Doc', status: 'green', parent: null, order: 1 })
        },
      ];

      const mockProdDocs = [
        {
          id: 'prod1',
          data: () => ({ title: 'Prod Doc', status: 'green', parent: null, order: 2 })
        },
      ];

      // Mock different responses for different collections
      mockGetDocs
        .mockResolvedValueOnce({
          size: 1,
          forEach: (callback) => mockTestDocs.forEach(callback),
        })
        .mockResolvedValueOnce({
          size: 1,
          forEach: (callback) => mockProdDocs.forEach(callback),
        });

      const { loadData, tree, error } = useKnowledgeTree();

      await loadData();

      expect(mockGetDocs).toHaveBeenCalledTimes(2);
      expect(error.value).toBeNull();
      expect(tree.value.length).toBe(2);
    });
  });

  describe('refresh', () => {
    it('should call loadData when refresh is called', async () => {
      mockGetDocs.mockResolvedValue({
        size: 0,
        forEach: () => {},
      });

      const { refresh, loadData } = useKnowledgeTree();
      const loadDataSpy = vi.spyOn({ loadData }, 'loadData');

      await refresh();

      // Verify loadData logic was executed
      expect(mockGetDocs).toHaveBeenCalled();
    });
  });

  describe('buildTree', () => {
    it('should build hierarchical tree from flat documents', async () => {
      const mockDocs = [
        {
          id: 'root',
          data: () => ({ title: 'Root', status: 'green', parent: null, order: 1 })
        },
        {
          id: 'child1',
          data: () => ({ title: 'Child 1', status: 'yellow', parent: 'root', order: 2 })
        },
        {
          id: 'child2',
          data: () => ({ title: 'Child 2', status: 'red', parent: 'root', order: 3 })
        },
        {
          id: 'grandchild',
          data: () => ({ title: 'Grandchild', status: 'green', parent: 'child1', order: 4 })
        },
      ];

      mockGetDocs.mockResolvedValue({
        size: 4,
        forEach: (callback) => mockDocs.forEach(callback),
      });

      const { loadData, tree } = useKnowledgeTree();

      await loadData();

      expect(tree.value.length).toBe(1); // One root node
      expect(tree.value[0].children.length).toBe(2); // Two children
      expect(tree.value[0].children[0].children.length).toBe(1); // One grandchild
    });
  });
});
