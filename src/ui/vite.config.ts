import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

// https://vitejs.dev/config/
export default defineConfig(({command, mode}) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => ['dashboard-tabs', 'notification-dropdown', 'dashboard-map'].includes(tag),
        }
      }
    }),
    vueJsx(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@public': fileURLToPath(new URL('./public', import.meta.url))
    },
    extensions: ['.js', '.jsx', '.ts', '.tsx', '.json', '.vue']
  },
  server: {
    port : 8080,
    host: '0.0.0.0'
  },
  define: {
    'process.env': env,
  }
}})
