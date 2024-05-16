import { createApp } from 'vue';
import { createGtm } from '@gtm-support/vue-gtm';
import { createI18n } from 'vue-i18n';
import { createVuestic } from "vuestic-ui";
import axios from 'axios';
import VueAxios from 'vue-axios';
import App from './App.vue';
import './registerServiceWorker';
import router from './router';
import store from './store';
import vuesticGlobalConfig from './services/vuestic-ui/global-config';
import VueKeyCloak from '@dsb-norge/vue-keycloak-js';
import type { VueKeycloakInstance } from "@dsb-norge/vue-keycloak-js/dist/types";
import 'material-icons/iconfont/material-icons.css';

import en from '@/i18n/en.json';
import fr from '@/i18n/fr.json';


const i18nConfig =  {
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: en,
    fr: fr
  }
}

const setToken = (token: any) => {
  store.dispatch('insertToken', token)
}

// Allow usage of this.$keycloak in components
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties  {
    $keycloak: VueKeycloakInstance;
  }
}

function instantiateVueApp () {
    const app = createApp({
      extends: App,
      created() {
        this.$watch('$keycloak.token', setToken, { immediate: true })
      }
    })
    app.config.globalProperties.window = window;
    app.use(VueKeyCloak, 
    {
      init: {
        onLoad: 'login-required'
      },
      config: {
        url: process.env.VUE_APP_OPENID_ISSUER,
        clientId: process.env.VUE_APP_OPENID_CLIENTID ?? '',
        realm: process.env.VUE_APP_OPENID_REALM ?? ''
      },
      onReady : (keycloak) => {
        // Store token immediately
        setToken(keycloak.token)
        app.use(store)
        app.use(router)
        if (process.env.VUE_APP_GTM_ENABLED === 'true') {
          const gtmConfig = {
            id: process.env.VUE_APP_GTM_KEY ?? makeid(20),
            debug: false,
            vueRouter: router,
          }
          app.use(createGtm(gtmConfig))
        }
        app.use(createI18n(i18nConfig))
        app.use(createVuestic({
          config : {
            components: vuesticGlobalConfig.components,
            colors: {
              variables : {
                primary: '#154ec1',
                secondary: '#767c88',
                background: '#f6f7f6',
                success: '#3d9209',
                info: '#2c82e0',
                danger: '#e42222',
                warning: '#ffd43a',
                white: '#ffffff',
                dark: '#262824',
                gray: '#767c88',
              }
            },
            icons: vuesticGlobalConfig.icons
          }
        }))
        app.use(VueAxios, axios)
        app.mount('#app')
      }
    })
}

function makeid(length: number) {
  let result = '';
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  const charactersLength = characters.length;
  let counter = 0;
  while (counter < length) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
    counter += 1;
  }
  return result;
}

instantiateVueApp()



