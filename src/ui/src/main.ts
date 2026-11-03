import { VuesticPlugin } from 'vuestic-ui';
import { createApp } from 'vue'
import { createGtm } from 'vue-gtm'
import { createI18n } from 'vue-i18n'
import axios from 'axios'
import VueAxios from 'vue-axios'
import App from './App.vue'
import './registerServiceWorker'
import router from './router'
import store from './store'
import vuesticGlobalConfig from './services/vuestic-ui/global-config'


// The texts of the pages are in src/i18n/pages/<area>.<language>.json, one file per area of the
// interface. The content of a file is available as pages.<area>.
function loadPageMessages(language: string) {
  // @ts-ignore webpack's require.context
  const context = require.context('@/i18n/pages', false, /\.json$/)
  const pages: Record<string, unknown> = {}
  for (const key of context.keys()) {
    const match = /^\.\/(.+)\.(en|fr)\.json$/.exec(key)
    if (match && match[2] === language) {
      pages[match[1]] = context(key)
    }
  }
  return { pages }
}

// The language chosen by the person is kept in this browser.
function savedLanguage(): string {
  try {
    const language = localStorage.getItem('backroll.language')
    return language === 'fr' || language === 'en' ? language : 'en'
  } catch {
    return 'en'
  }
}

const i18nConfig = {
  locale: savedLanguage(),
  fallbackLocale: 'en',
  messages: {
    en: { ...require('@/i18n/en.json'), ...loadPageMessages('en') },
    fr: { ...require('@/i18n/fr.json'), ...loadPageMessages('fr') }
  }
}

// An expired or revoked session sends the user back to the login page.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && store.getters.isAuthenticated) {
      store.commit('logout')
      router.push({ name: 'login' })
    }
    return Promise.reject(error)
  }
)

async function instantiateVueApp() {
  const app = createApp(App)
  app.config.globalProperties.window = window

  app.use(store)
  app.use(router)

  if (process.env.VUE_APP_GTM_ENABLED === 'true') {
    const gtmConfig = {
      id: process.env.VUE_APP_GTM_KEY,
      debug: false,
      vueRouter: router,
    }
    app.use(createGtm(gtmConfig))
  }

  app.use(createI18n(i18nConfig))
  app.use(VuesticPlugin, vuesticGlobalConfig)
  app.use(VueAxios, axios)
  app.mount('#app')
}

instantiateVueApp()
