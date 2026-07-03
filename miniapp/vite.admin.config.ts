import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Только библиотечный режим (build.lib): обычная сборка через rollupOptions.input
// идёт с preserveEntrySignatures: false — Rollup выбрасывает export default { mount },
// и весь админ-код tree-shake'ится из бандла (остаётся голый React без экспортов).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': '/src' } },
  // В lib-режиме Vite не подставляет NODE_ENV — без define в браузере упадёт
  // обращение к process.env внутри react-dom.
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: '../static/miniapp-admin',
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: {
      entry: 'src/admin/main.tsx',
      formats: ['es'],
      fileName: () => 'entry.js',
    },
    rollupOptions: {
      output: { assetFileNames: 'entry[extname]' },
    },
  },
})
