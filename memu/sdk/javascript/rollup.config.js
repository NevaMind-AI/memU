import typescript from 'rollup-plugin-typescript2';
import { readFileSync } from 'fs';

const pkg = JSON.parse(readFileSync('./package.json', 'utf8'));

export default {
  // ESM build only
  input: 'src/index.ts',
  output: {
    file: pkg.module,
    format: 'es',
    sourcemap: true,
  },
  plugins: [
    typescript({
      typescript: require('typescript'),
      tsconfig: 'tsconfig.json',
      tsconfigOverride: {
        compilerOptions: {
          declaration: true,
          declarationMap: true,
        },
      },
    }),
  ],
  external: ['axios'],
};
