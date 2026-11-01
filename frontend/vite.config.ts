import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/static/frontend/',
  build: {
    outDir: '../static/frontend',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/vue/') || id.includes('node_modules/vue-router/')) return 'vue-vendor'
          if (id.includes('node_modules/element-plus/') || id.includes('node_modules/@element-plus/icons-vue/')) return 'element-plus-vendor'
          return undefined
        },
      },
    },
  },
  plugins: [vue()],
})
