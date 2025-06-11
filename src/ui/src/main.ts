import { VuesticPlugin } from 'vuestic-ui';
import { createApp } from 'vue'
import { createGtm } from 'vue-gtm'
import { createI18n } from 'vue-i18n'
import axios from 'axios'
import VueAxios from 'vue-axios'
import VueKeyCloak from '@dsb-norge/vue-keycloak-js'
import { VueKeycloakInstance } from "@dsb-norge/vue-keycloak-js/dist/types";
import App from './App.vue'
import './registerServiceWorker'
import router from './router'
import store from './store'
import vuesticGlobalConfig from './services/vuestic-ui/global-config'


const i18nConfig = {
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: require('@/i18n/en.json'),
    fr: require('@/i18n/fr.json')
  }
}

const setToken = (token: any) => {
  store.dispatch('insertToken', token)
}

// Allow usage of this.$keycloak in components
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $keycloak: VueKeycloakInstance;
  }
}

function instantiateVueApp() {
  const app = createApp({
    extends: App,
    created() {
      this.$watch('$keycloak.token', setToken, { immediate: true })
    }
  })
  app.config.globalProperties.window = window
  app.use(VueKeyCloak, {
    init: {
      onLoad: 'login-required'
    },
    config: {
      url: process.env.VUE_APP_OPENID_ISSUER,
      realm: process.env.VUE_APP_OPENID_REALM,
      clientId: process.env.VUE_APP_OPENID_CLIENT_UI_ID
    },
    onReady(kc: { token: any }) {
      // Store token immediately
      setToken(kc.token)
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
  })
}


instantiateVueApp()



