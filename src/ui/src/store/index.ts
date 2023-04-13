import axios from 'axios'
import { createStore } from 'vuex'
import router from '../router'

export default createStore({
  strict: true, // process.env.NODE_ENV !== 'production',
  state: {
    endpoint: {
      api: process.env.VUE_APP_API_ENDPOINT_URL
    },
    token: null,
    isSidebarMinimized: false,
    userName: null,
    // Table misc
    ispolicyTableReady: false,
    ispoolTableReady: false,
    ishostTableReady: false,
    isvmTableReady: false,
    isjobTableReady: false,
    isstorageTableReady: false,
    isbackupTaskTableReady: false,
    isrestoreTaskTableReady: false,
    isexternalHookTableReady: false,
    isconnectorTableReady: false,
    // Resources list
    resources: {
      policyList: [],
      poolList: [],
      hostList: [],
      vmList: [],
      externalHookList: [],
      connectorList: []
    },
    jobList: [],
    backupTaskList: [],
    restoreTaskList: [],
    storageList: []
    
  },
  getters: {
    policiesCount (state) {
      return state.resources.policyList.length
    },
    poolsCount (state) {
      return state.resources.poolList.length
    },
    hostsCount (state) {
      return state.resources.hostList.length
    },
    vmsCount (state) {
      return state.resources.vmList.length
    },
  },
  actions: {
    // Handle OpenID token
    insertToken(context, token) {
      context.commit('insertToken', token)
    },
    // Ask and retrieve pools from BackROLL API
    async requestPool(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/pools`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parsePool", { token: token, location: data.Location })
    },
    async parsePool(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parsePool", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingPool', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updatePoolList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updatePool(context, { vm, token, poolValues }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/pools/${poolValues.id}`, { name: poolValues.name, policy_id: poolValues.policy_id }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestPool", { token: token })
          router.push('/admin/resources/pools')
          vm.$vaToast.init(({ message: "Pool has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
          vm.$vaToast.init(({ title: 'Error !', message: error.response.data.detail, color: 'danger' }))
        }
      })
    },
    updatePoolList(context, poolsList) {
      context.commit('poolList', poolsList)
    },
    // Ask and retrieve policies from BackROLL API
    async requestPolicy(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/backup_policies`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parsePolicy", { token: token, location: data.Location })
    },
    async parsePolicy(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parsePolicy", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingPolicy', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updatePolicyList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updatePolicy(context, { vm, token, policyValues }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/backup_policies/${policyValues.id}`, { name: policyValues.name, description: policyValues.description, retention: policyValues.retention, schedule: policyValues.schedule, storage: policyValues.storage.value, externalhook: policyValues.externalhook, enabled: policyValues.state }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestPolicy", { token: token })
          router.push('/admin/configuration/policies')
          vm.$vaToast.init(({ message: "Policy has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
          vm.$vaToast.init(({ title: 'Error !', message: error.response.data.detail, color: 'danger' }))
        }
      })
    },
    updatePolicyList(context, policiesList) {
      context.commit('policyList', policiesList)
    },
    // Ask and retrieve hypervisors from BackROLL API
    async requestHost(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/hosts`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parseHost", { token: token, location: data.Location })
    },
    async parseHost(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseHost", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingHost', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateHostList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updateHost(context, { vm, token, hostValues }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/hosts/${hostValues.id}`, hostValues, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestHost", { token: token })
          router.push('/admin/resources/hypervisors')
          vm.$vaToast.init(({ message: "Hypervisor has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
          vm.$vaToast.init(({ title: 'Error !', message: error.response.data.detail, color: 'danger' }))
        }
      })
    },
    updateHostList(context, hostList) {
      context.commit('hostList', hostList)
    },
    // Ask and retrieve virtual machines from BackROLL API
    async requestVirtualMachine(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/virtualmachines`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parseVirtualMachine", { token: token, location: data.Location })
    },
    async parseVirtualMachine(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseVirtualMachine", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingVm', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateVMList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    updateVMList(context, vmList) {
      context.commit('vmList', vmList)
    },
    // Ask and retrieve storage from BackROLL API
    async requestStorage(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/storage`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parseStorage", { token: token, location: data.Location })
    },
    async parseStorage(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseStorage", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingStorage', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateStorageList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updateStorage(context, { vm, token, storageId, name, path }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/storage/${storageId}`, { name: name, path: path }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestStorage", { token: token })
          router.push('/admin/configuration/storage')
          vm.$vaToast.init(({ message: "Storage has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
        }
      })
    },
    updateStorageList(context, storageList) {
      context.commit('storageList', storageList)
    },
    // Ask and retrieve backup task from BackROLL API
    async requestBackupTask(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/tasks/backup`, {headers: { 'Authorization': `Bearer ${token}` }})
      context.commit('loadingBackupTask', true)
      context.dispatch('updateBackupTaskList', data.info)
      setTimeout(()=>{
        context.dispatch("requestBackupTask", { token: token })
      },10000)
    },
    updateBackupTaskList(context, taskList) {
      context.commit('backupTaskList', taskList)
    },
    // Ask and retrieve restore task from BackROLL API
    async requestRestoreTask(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/tasks/restore`, {headers: { 'Authorization': `Bearer ${token}` }})
      context.commit('loadingRestoreTask', true)
      context.dispatch('updateRestoreTaskList', data.info)
      setTimeout(()=>{
        context.dispatch("requestRestoreTask", { token: token })
      },10000)
    },
    updateRestoreTaskList(context, taskList) {
      context.commit('restoreTaskList', taskList)
    },
    // Ask and retrieve restore task from BackROLL API
    async requestJob(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/jobs`, {headers: { 'Authorization': `Bearer ${token}` }})
      context.dispatch("parseJob", { token: token, location: data.Location })
    },
    async parseJob(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseJob", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingJob', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateJobList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    updateJobList(context, taskList) {
      context.commit('jobList', taskList)
    },
    // Ask and retrieve external hooks from BackROLL API
    async requestExternalHook(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/externalhooks`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parseExternalHooks", { token: token, location: data.Location })
    },
    async parseExternalHooks(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseExternalHooks", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingExternalHook', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateExternalHooksList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updateExternalHook(context, { vm, token, hookValues }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/externalhooks/${hookValues.id}`, { name: hookValues.name, value: hookValues.value }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestExternalHook", { token: token })
          router.push('/admin/configuration/externalhooks')
          vm.$vaToast.init(({ message: "External hook has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
          vm.$vaToast.init(({ title: 'Error !', message: error.response.data.detail, color: 'danger' }))
        }
      })
    },
    updateExternalHooksList(context, externalHookList) {
      context.commit('externalHookList', externalHookList)
    },

    // Ask and retrieve connectors from BackROLL API
    async requestConnector(context, { token }) {
      const { data } = await axios.get(`${this.state.endpoint.api}/api/v1/connectors`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      context.dispatch("parseConnectors", { token: token, location: data.Location })
    },
    async parseConnectors(context, { token, location }) {
      const { data } = await axios.get(`${this.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${token}` }})
      if (data.state === 'PENDING' || data.state == 'STARTED') {
        setTimeout(()=>{
          context.dispatch("parseConnectors", { token: token, location: location })
        },2000)
      } else {
        context.commit('loadingConnector', true)
        if (data.state === 'SUCCESS') {
          context.dispatch('updateConnectorsList', data.info)
        } else if (data.state === 'FAILURE') {
          console.error(data.status)
        }
      }
    },
    async updateConnector(context, { vm, token, connectorValues }) {
      await axios.patch(`${this.state.endpoint.api}/api/v1/connectors/${connectorValues.id}`, { name: connectorValues.name, url: connectorValues.url, login: connectorValues.login, password: connectorValues.password }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`}})
      .then(response => {
        if (response.status === 200) {
          context.dispatch("requestConnector", { token: token })
          router.push('/admin/configuration/connectors')
          vm.$vaToast.init(({ message: "Connector has been successfully updated", color: 'success' }))
        }
      })
      .catch(function (error) {
        if (error.response) {
          console.error(error.response.data.detail)
          vm.$vaToast.init(({ title: 'Error !', message: error.response.data.detail, color: 'danger' }))
        }
      })
    },
    updateConnectorsList(context, connectorList) {
      context.commit('connectorList', connectorList)
    }

  },
  mutations: {
    insertToken(state, token) {
      state.token = token
    },
    poolList(state, poolsList) {
      state.resources.poolList = poolsList
    },
    loadingPool(state, loadingState) {
      state.ispoolTableReady = loadingState
    },
    policyList(state, policiesList) {
      state.resources.policyList = policiesList
    },
    loadingPolicy(state, loadingState) {
      state.ispolicyTableReady = loadingState
    },
    hostList(state, hostList) {
      state.resources.hostList = hostList
    },
    loadingHost(state, loadingState) {
      state.ishostTableReady = loadingState
    },
    vmList(state, vmList) {
      state.resources.vmList = vmList
    },
    loadingVm(state, loadingState) {
      state.isvmTableReady = loadingState
    },
    jobList(state, jobsList) {
      state.jobList = jobsList
    },
    loadingJob(state, loadingState) {
      state.isjobTableReady = loadingState
    },
    storageList(state, storageList) {
      state.storageList = storageList
    },
    loadingStorage(state, loadingState) {
      state.isstorageTableReady = loadingState
    },
    externalHookList(state, externalHookList) {
      state.resources.externalHookList = externalHookList
    },
    loadingExternalHook(state, loadingState) {
      state.isexternalHookTableReady = loadingState
    },
    connectorList(state, connectorList) {
      state.resources.connectorList = connectorList
    },
    loadingConnector(state, loadingState) {
      state.isconnectorTableReady = loadingState
    },
    backupTaskList(state, taskList) {
      state.backupTaskList = taskList
    },
    loadingBackupTask(state, loadingState) {
      state.isbackupTaskTableReady = loadingState
    },
    restoreTaskList(state, taskList) {
      state.isrestoreTaskTableReady = true
      state.restoreTaskList = taskList
    },
    loadingRestoreTask(state, loadingState) {
      state.isrestoreTaskTableReady = loadingState
    },
    updateSidebarCollapsedState(state, isSidebarMinimized) {
      state.isSidebarMinimized = isSidebarMinimized
    }
  }
})
