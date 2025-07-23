import axios from "axios";
import { createStore } from "vuex";
import router from "../router";

export default createStore({
  strict: true, // process.env.NODE_ENV !== 'production',
  state: {
    endpoint: {
      api: process.env.VUE_APP_API_ENDPOINT_URL,
    },
    token: null,
    isSidebarMinimized: false,
    userName: null,
    // Table misc
    isPolicyTableReady: false,
    isPoolTableReady: false,
    isHostTableReady: false,
    isvmTableReady: false,
    isjobTableReady: false,
    isStorageTableReady: false,
    isbackupTaskTableReady: false,
    isrestoreTaskTableReady: false,
    areCeleryTasksReady: false,
    isexternalHookTableReady: false,
    isconnectorTableReady: false,
    // Resources list
    resources: {
      policyList: [],
      poolList: [],
      hostList: [],
      vmList: [],
      externalHookList: [],
      connectorList: [],
    },
    jobList: [],
    backupTaskList: [],
    restoreTaskList: [],
    celeryTaskList: [],
    storageList: [],
  },
  getters: {
    isAuthenticated: (state) => state.token != null,
    policiesCount(state) {
      return state.resources.policyList.length;
    },
    poolsCount(state) {
      return state.resources.poolList.length;
    },
    hostsCount(state) {
      return state.resources.hostList.length;
    },
    vmsCount(state) {
      return state.resources.vmList.length;
    },
  },
  actions: {
    // Handle OpenID token
    insertToken(context, token) {
      context.commit("insertToken", token);
    },
    // Ask and retrieve pools from BackROLL API
    async requestPool(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/pools`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parsePool", { location: data.Location });
    },
    async parsePool(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parsePool", { location: location });
        }, 2000);
      } else {
        context.commit("loadingPool", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updatePoolList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    async updatePool(context, { vm, poolValues }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/pools/${poolValues.id}`,
          poolValues,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestPool");
            router.push("/admin/resources/pools");
            vm.$vaToast.init({
              message: "Pool has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updatePoolList(context, poolsList) {
      context.commit("poolList", poolsList);
    },
    // Ask and retrieve policies from BackROLL API
    async requestPolicy(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/backup_policies`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parsePolicy", {
        location: data.Location,
      });
    },
    async parsePolicy(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parsePolicy", { location: location });
        }, 2000);
      } else {
        context.commit("loadingPolicy", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updatePolicyList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    async updatePolicy(context, { vm, policyValues }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/backup_policies/${policyValues.id}`,
          {
            name: policyValues.name,
            description: policyValues.description,
            retention: policyValues.retention,
            schedule: policyValues.schedule,
            storage: policyValues.storage,
            externalhook: policyValues.externalhook,
            enabled: policyValues.state,
          },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestPolicy");
            router.push("/admin/configuration/policies");
            vm.$vaToast.init({
              message: "Policy has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updatePolicyList(context, policiesList) {
      context.commit("policyList", policiesList);
    },
    // Ask and retrieve hypervisors from BackROLL API
    async requestHost(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/hosts`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parseHost", { location: data.Location });
    },
    async parseHost(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseHost", { location: location });
        }, 2000);
      } else {
        context.commit("loadingHost", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateHostList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    async updateHost(context, { vm, hostValues }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/hosts/${hostValues.id}`,
          hostValues,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestHost");
            router.push("/admin/resources/hypervisors");
            vm.$vaToast.init({
              message: "Hypervisor has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updateHostList(context, hostList) {
      context.commit("hostList", hostList);
    },
    // Ask and retrieve virtual machines from BackROLL API
    async requestVirtualMachine(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/virtualmachines`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parseVirtualMachine", {
        location: data.Location,
      });
    },
    async parseVirtualMachine(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseVirtualMachine", {
            location: location,
          });
        }, 2000);
      } else {
        context.commit("loadingVm", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateVMList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    updateVMList(context, vmList) {
      context.commit("vmList", vmList);
    },
    // Ask and retrieve storage from BackROLL API
    async requestStorage(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/storage`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parseStorage", {
        location: data.Location,
      });
    },
    async parseStorage(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseStorage", {
            location: location,
          });
        }, 2000);
      } else {
        context.commit("loadingStorage", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateStorageList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    async updateStorage(context, { vm, storageId, name, path }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/storage/${storageId}`,
          { name: name, path: path },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestStorage");
            router.push("/admin/configuration/storage");
            vm.$vaToast.init({
              message: "Storage has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updateStorageList(context, storageList) {
      context.commit("storageList", storageList);
    },
    // Ask and retrieve backup task from BackROLL API
    async requestBackupTask(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/tasks/backup`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      context.commit("loadingBackupTask", true);
      context.dispatch("updateBackupTaskList", data.info);
    },
    updateBackupTaskList(context, taskList) {
      context.commit("backupTaskList", taskList);
    },
    // Ask and retrieve restore task from BackROLL API
    async requestRestoreTask(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/tasks/restore`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      context.commit("loadingRestoreTask", true);
      context.dispatch("updateRestoreTaskList", data.info);
    },
    updateRestoreTaskList(context, taskList) {
      context.commit("restoreTaskList", taskList);
    },
    // Ask and retrive celery tasks from BackROLL API
    async requestCeleryTasks(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/tasks`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      context.commit("loadingCeleryTasks", true);
      context.dispatch("updateCeleryTaskList", data.info);
    },
    updateCeleryTaskList(context, taskList) {
      context.commit("celeryTaskList", taskList);
    },
    // Ask and retrieve jobs (task types) from BackROLL API
    async requestJob(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/jobs`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      context.dispatch("parseJob", { location: data.Location });
    },
    async parseJob(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseJob", { location: location });
        }, 2000);
      } else {
        context.commit("loadingJob", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateJobList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    updateJobList(context, taskList) {
      context.commit("jobList", taskList);
    },
    // Ask and retrieve external hooks from BackROLL API
    async requestExternalHook(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/externalhooks`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parseExternalHooks", {
        location: data.Location,
      });
    },
    async parseExternalHooks(context, { location }) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}${location}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseExternalHooks", {
            location: location,
          });
        }, 2000);
      } else {
        context.commit("loadingExternalHook", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateExternalHooksList", data.info);
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    async updateExternalHook(context, { vm, hookValues }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/externalhooks/${hookValues.id}`,
          { name: hookValues.name, value: hookValues.value },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestExternalHook");
            router.push("/admin/configuration/externalhooks");
            vm.$vaToast.init({
              message: "External hook has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updateExternalHooksList(context, externalHookList) {
      context.commit("externalHookList", externalHookList);
    },

    // Ask and retrieve connectors from BackROLL API
    async requestConnector(context) {
      const token = context.state.token;
      const { data } = await axios.get(
        `${this.state.endpoint.api}/api/v1/connectors`,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      context.dispatch("parseConnectors", {
        location: data.Location,
      });
    },
    async parseConnectors(context, { location }) {
      const token = context.state.token;
      try {
        const { data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (data.state === "PENDING" || data.state == "STARTED") {
          setTimeout(() => {
            context.dispatch("parseConnectors", {
              location: location,
            });
          }, 2000);
        } else {
          context.commit("loadingConnector", true);
          if (data.state === "SUCCESS") {
            context.dispatch("updateConnectorsList", data.info);
          } else if (data.state === "FAILURE") {
            console.error(data.status);
          }
        }
      } catch (error) {
        console.error("Error fetching connectors:", error);
        context.commit("loadingConnector", false);
        context.dispatch("updateConnectorsList", []);
      }
    },
    async updateConnector(context, { vm, connectorValues }) {
      const token = context.state.token;
      await axios
        .patch(
          `${this.state.endpoint.api}/api/v1/connectors/${connectorValues.id}`,
          {
            name: connectorValues.name,
            url: connectorValues.url,
            login: connectorValues.login,
            password: connectorValues.password,
          },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        )
        .then((response) => {
          if (response.status === 200) {
            context.dispatch("requestConnector");
            router.push("/admin/configuration/connectors");
            vm.$vaToast.init({
              message: "Connector has been successfully updated",
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: "Error !",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    updateConnectorsList(context, connectorList) {
      context.commit("connectorList", connectorList);
    },
  },
  mutations: {
    logout(state) {
      state.token = null;
      state.userName = null;
    },
    insertToken(state, token) {
      state.token = token;
    },
    insertUserName(state, userName) {
      state.userName = userName;
    },
    poolList(state, poolsList) {
      state.resources.poolList = poolsList;
    },
    loadingPool(state, loadingState) {
      state.isPoolTableReady = loadingState;
    },
    policyList(state, policiesList) {
      state.resources.policyList = policiesList;
    },
    loadingPolicy(state, loadingState) {
      state.isPolicyTableReady = loadingState;
    },
    hostList(state, hostList) {
      state.resources.hostList = hostList;
    },
    loadingHost(state, loadingState) {
      state.isHostTableReady = loadingState;
    },
    vmList(state, vmList) {
      state.resources.vmList = vmList;
    },
    loadingVm(state, loadingState) {
      state.isvmTableReady = loadingState;
    },
    jobList(state, jobsList) {
      state.jobList = jobsList;
    },
    loadingJob(state, loadingState) {
      state.isjobTableReady = loadingState;
    },
    storageList(state, storageList) {
      state.storageList = storageList;
    },
    loadingStorage(state, loadingState) {
      state.isStorageTableReady = loadingState;
    },
    externalHookList(state, externalHookList) {
      state.resources.externalHookList = externalHookList;
    },
    loadingExternalHook(state, loadingState) {
      state.isexternalHookTableReady = loadingState;
    },
    connectorList(state, connectorList) {
      state.resources.connectorList = connectorList;
    },
    loadingConnector(state, loadingState) {
      state.isconnectorTableReady = loadingState;
    },
    backupTaskList(state, taskList) {
      state.backupTaskList = taskList;
    },
    loadingBackupTask(state, loadingState) {
      state.isbackupTaskTableReady = loadingState;
    },
    restoreTaskList(state, taskList) {
      state.isrestoreTaskTableReady = true;
      state.restoreTaskList = taskList;
    },
    loadingRestoreTask(state, loadingState) {
      state.isrestoreTaskTableReady = loadingState;
    },
    celeryTaskList(state, taskList) {
      // TODO Sure ?
      state.areCeleryTasksReady = true;
      state.celeryTaskList = taskList;
    },
    loadingCeleryTasks(state, loadingState) {
      // TODO Sure ?
      state.areCeleryTasksReady = loadingState;
    },
    updateSidebarCollapsedState(state, isSidebarMinimized) {
      state.isSidebarMinimized = isSidebarMinimized;
    },
  },
});
