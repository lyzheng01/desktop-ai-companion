import path from 'node:path';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [],
  clearScreen: false,
  publicDir: path.resolve(__dirname, './public-packaged'),
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    target: ['es2021', 'chrome100', 'safari15'],
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    sourcemap: !!process.env.TAURI_DEBUG,
    outDir: 'dist',
  },
});
