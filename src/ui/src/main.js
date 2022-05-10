// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.


import VueKeyCloakJS from '@dsb-norge/vue-keycloak-js'

import Vue from 'vue'
import { BootstrapVue, BootstrapVueIcons } from 'bootstrap-vue'
// Import Bootstrap an BootstrapVue CSS files (order is important)
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import PortalVue from 'portal-vue'
import { createPopper } from '@popperjs/core'
import Vuelidate from 'vuelidate'

import App from './App.vue'
import router from './router'

// Style
import "@/assets/global.scss"
// Store

import store from './store'

Vue.config.productionTip = false
// Make BootstrapVue available throughout your project
Vue.use(BootstrapVue)
// Optionally install the BootstrapVue icon components plugin
Vue.use(BootstrapVueIcons)
// Requirements
Vue.use(PortalVue)
Vue.use(createPopper)
Vue.use(Vuelidate)

Vue.use(VueKeyCloakJS, {
  init: {
    onLoad: 'login-required'
  },
  config: {
    url: window.BACKROLL_OPENID_ISSUER_URL,
    clientId: window.BACKROLL_OPENID_CLIENTID,
    realm: window.BACKROLL_OPENID_REALM
  },
  onReady () {
    Vue.use({ BootstrapVue, store })
  
    new Vue({
      router,
      store,
      render: h => h(App)
    }).$mount('#app')
  }
})
