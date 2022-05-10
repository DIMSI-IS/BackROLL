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

import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    endpoint: {
      api: window.BACKROLL_API_ENDPOINT_URL
    },
    connectionStatus: null,
    /* Message */
    messages: {},
    messagesOrder: [],
    /* Release Version */
    release: '1.0.0-1',
    /* BackROLL backend pubkey */
    sshPublicKey: null,
    /* Resources */
    backup_jobs: [],
    restoreJobs: [],
    backupPolicyList: [],
    poolsList: [],
    hostsList: [],
    vmsList: [],
    /* Loading */
    loadingBackupTasks: false,
    loadingRestoreJobs: false,
    loadingBackupPolicies: true,
    loadingPools: true,
    loadingHosts: true,
    loadingVMs: true

  }
})