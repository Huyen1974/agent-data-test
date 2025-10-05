module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:deprecation/recommended',
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: './tsconfig.json',
    extraFileExtensions: ['.vue'],
  },
  plugins: ['deprecation'],
  rules: {
    // Deprecation rule will show warnings by default
    'deprecation/deprecation': 'warn',
    // Allow unused vars for props in Vue components (they're used in templates)
    'no-unused-vars': ['error', {
      varsIgnorePattern: '^props$',
      argsIgnorePattern: '^_',
    }],
  },
};
