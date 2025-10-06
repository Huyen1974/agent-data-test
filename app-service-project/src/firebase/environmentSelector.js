import { ref, computed } from 'vue';

/**
 * Environment types for data filtering
 * Following Constitution QD-LAW §2: Separate collections per environment
 */
export const ENVIRONMENTS = {
  ALL: 'all',
  TEST: 'test',
  PRODUCTION: 'production',
};

/**
 * Shared state for selected environment
 * @private
 */
const selectedEnvironment = ref(ENVIRONMENTS.ALL);

/**
 * Composable to manage environment selection for knowledge data
 *
 * This implements the Constitution-compliant strategy (QD-LAW §2.1):
 * "Việc phân tách dữ liệu giữa các môi trường BẮT BUỘC phải được thực hiện
 * bằng cách sử dụng các collection riêng biệt"
 *
 * @returns {{
 *   selectedEnvironment: import('vue').Ref<string>,
 *   setEnvironment: (env: string) => void,
 *   collectionNames: import('vue').ComputedRef<string[]>,
 *   displayLabel: import('vue').ComputedRef<string>
 * }}
 */
export function useEnvironmentSelector() {
  /**
   * Set the current environment filter
   * @param {string} env - One of ENVIRONMENTS values
   */
  const setEnvironment = (env) => {
    if (Object.values(ENVIRONMENTS).includes(env)) {
      selectedEnvironment.value = env;
    } else {
      console.warn(`Invalid environment: ${env}. Using ALL.`);
      selectedEnvironment.value = ENVIRONMENTS.ALL;
    }
  };

  /**
   * Get the collection names to query based on selected environment
   * Following naming pattern: test_documents, production_documents
   */
  const collectionNames = computed(() => {
    switch (selectedEnvironment.value) {
      case ENVIRONMENTS.TEST:
        return ['test_documents'];
      case ENVIRONMENTS.PRODUCTION:
        return ['production_documents'];
      case ENVIRONMENTS.ALL:
      default:
        return ['test_documents', 'production_documents'];
    }
  });

  /**
   * Get display label for current environment
   */
  const displayLabel = computed(() => {
    switch (selectedEnvironment.value) {
      case ENVIRONMENTS.TEST:
        return 'Test';
      case ENVIRONMENTS.PRODUCTION:
        return 'Production';
      case ENVIRONMENTS.ALL:
      default:
        return 'Tất cả';
    }
  });

  return {
    selectedEnvironment,
    setEnvironment,
    collectionNames,
    displayLabel,
  };
}
