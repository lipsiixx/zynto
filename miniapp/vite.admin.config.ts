import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': '/src' } },
  build: {
    outDir: '../static/miniapp-admin',
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: 'src/admin/main.tsx',
      output: {
        entryFileNames: 'entry.js',
        inlineDynamicImports: true,
        assetFileNames: 'entry[extname]',
      },
    },
  },
})
