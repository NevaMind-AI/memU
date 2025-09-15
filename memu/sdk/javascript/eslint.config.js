import { defineConfig } from '@moeru/eslint-config'

export default defineConfig({}, {
  files: ['**/examples/**'],
  rules: {
    '@masknet/no-top-level': 'off',
    'no-console': 'off',
    'sonarjs/cognitive-complexity': 'off',
    'ts/restrict-template-expressions': 'off',
  },
}, {
  rules: {
    'depend/ban-dependencies': 'warn',
  },
})
