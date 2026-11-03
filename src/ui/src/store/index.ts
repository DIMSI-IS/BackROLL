import axios from "axios";
import { createStore } from "vuex";
import router from "../router";

const SESSION_KEY = "backroll.session";

// The lists are asked to a task that is polled until it ends. A refresh starts a new request: the previous one of
// the same list is dropped (they piled up while a worker was busy or stopped), and a task that never answers is
// given up after a while.
const pollEpochs: Record<string, number> = {};
const POLL_LIMIT_MS = 120000;

function nextEpoch(name: string): number {
  pollEpochs[name] = (pollEpochs[name] || 0) + 1;
  return pollEpochs[name];
}

function isSuperseded(name: string, epoch?: number, since?: number): boolean {
  if (epoch !== undefined && epoch !== pollEpochs[name]) {
    return true;
  }
  return since !== undefined && Date.now() - since > POLL_LIMIT_MS;
}

// The session survives a page refresh but not closing the tab.
function loadSession(): any {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
    return session && session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

function saveSession(session: any) {
  try {
    if (session) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      sessionStorage.removeItem(SESSION_KEY);
    }
  } catch {
    // Storage may be unavailable, the session then lives in memory only.
  }
}

const initialSession = loadSession();

const REFRESH_KEY = "backroll.refresh";
const REFRESH_CHOICES = [0, 5, 10, 30, 60];

// The refresh period is a preference of the person, kept in this browser. 0 means off.
function loadRefreshSeconds(): number {
  try {
    const value = Number(localStorage.getItem(REFRESH_KEY));
    return REFRESH_CHOICES.includes(value) && localStorage.getItem(REFRESH_KEY) !== null ? value : 10;
  } catch {
    return 10;
  }
}

export default createStore({
  strict: true, // process.env.NODE_ENV !== 'production',
  state: {
    endpoint: {
      api: `${window.location.origin}`,
    },
    token: initialSession ? initialSession.token : null,
    user: initialSession ? initialSession.user : null,
    isSidebarMinimized: false,
    userName: initialSession ? initialSession.user.name : null,
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
      // What went wrong during the last listing of the machines (a connector that does not answer, for instance).
      vmWarnings: [] as string[],
      externalHookList: [],
      connectorList: [],
    },
    jobList: [],
    backupTaskList: [],
    restoreTaskList: [],
    celeryTaskList: [],
    storageList: [],
    // Automatic refresh of the data. `tick` changes at each refresh: the pages that
    // read their own data watch it.
    refresh: {
      seconds: loadRefreshSeconds(),
      lastAt: null as number | null,
      tick: 0,
      running: false,
    },
  },
  getters: {
    isAuthenticated: (state) => state.token != null,
    role: (state: any) => (state.user ? state.user.role : null),
    canEdit: (state: any) =>
      state.user != null && ["editor", "admin"].includes(state.user.role),
    isAdmin: (state: any) => state.user != null && state.user.role === "admin",
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
    // Reloads the lists. The lists that an open form is editing are left alone: a refresh
    // would replace what the person is typing.
    async refreshAll(context) {
      if (!context.state.token || context.state.refresh.running) {
        return;
      }
      context.commit("refreshStarted");
      try {
        const path = router.currentRoute.value.path;
        const editing = /\/new$/.test(path)
          || /\/(pools|hypervisors|policy|storage|connectors|externalhooks)\/[^/]+$/.test(path);
        const actions = [
          "requestJob",
          "requestBackupTask",
          "requestRestoreTask",
          "requestVirtualMachine",
        ];
        if (!editing) {
          actions.push("requestPool", "requestHost", "requestPolicy", "requestStorage",
            "requestConnector", "requestExternalHook");
        }
        await Promise.allSettled(actions.map((action) => context.dispatch(action)));
      } finally {
        context.commit("refreshFinished");
      }
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
      context.dispatch("parsePool", {
        location: data.Location,
        epoch: nextEpoch("Pool"),
        since: Date.now(),
      });
    },
    async parsePool(context, { location, epoch, since }) {
      if (isSuperseded("Pool", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingPool", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parsePool", { location: location, epoch: epoch, since: since });
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
              message: vm.$t("pages.navbar.poolUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
        epoch: nextEpoch("Policy"),
        since: Date.now(),
      });
    },
    async parsePolicy(context, { location, epoch, since }) {
      if (isSuperseded("Policy", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingPolicy", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parsePolicy", { location: location, epoch: epoch, since: since });
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
            // The form gives the state of the list as "enabled": without it the policy would be switched off.
            enabled: policyValues.state ?? policyValues.enabled,
            file_paths: policyValues.file_paths,
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
              message: vm.$t("pages.navbar.policyUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
      context.dispatch("parseHost", {
        location: data.Location,
        epoch: nextEpoch("Host"),
        since: Date.now(),
      });
    },
    async parseHost(context, { location, epoch, since }) {
      if (isSuperseded("Host", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingHost", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseHost", { location: location, epoch: epoch, since: since });
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
              message: vm.$t("pages.navbar.hypervisorUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
        epoch: nextEpoch("VirtualMachine"),
        since: Date.now(),
      });
    },
    async parseVirtualMachine(context, { location, epoch, since }) {
      if (isSuperseded("VirtualMachine", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingVm", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseVirtualMachine", { location: location, epoch: epoch, since: since });
        }, 2000);
      } else {
        context.commit("loadingVm", true);
        if (data.state === "SUCCESS") {
          context.dispatch("updateVMList", data.info);
          context.dispatch("requestVmWarnings");
        } else if (data.state === "FAILURE") {
          console.error(data.status);
        }
      }
    },
    // The listing of the machines does not fail when a connector does not answer: it says so here.
    async requestVmWarnings(context) {
      try {
        const { data } = await axios.get(
          `${this.state.endpoint.api}/api/v1/virtualmachines/warnings`,
          { headers: { Authorization: `Bearer ${context.state.token}` } }
        );
        context.commit("vmWarnings", Array.isArray(data.warnings) ? data.warnings : []);
      } catch (error) {
        context.commit("vmWarnings", []);
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
        epoch: nextEpoch("Storage"),
        since: Date.now(),
      });
    },
    async parseStorage(context, { location, epoch, since }) {
      if (isSuperseded("Storage", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingStorage", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseStorage", { location: location, epoch: epoch, since: since });
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
              message: vm.$t("pages.navbar.storageUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
      context.dispatch("parseJob", {
        location: data.Location,
        epoch: nextEpoch("Job"),
        since: Date.now(),
      });
    },
    async parseJob(context, { location, epoch, since }) {
      if (isSuperseded("Job", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingJob", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseJob", { location: location, epoch: epoch, since: since });
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
        epoch: nextEpoch("ExternalHooks"),
        since: Date.now(),
      });
    },
    async parseExternalHooks(context, { location, epoch, since }) {
      if (isSuperseded("ExternalHooks", epoch, since)) {
        return;
      }
      const token = context.state.token;
      let data: any;
      try {
        ({ data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ));
      } catch (error) {
        // A task that failed answers with an HTTP error: the wait ends and the page stops showing its spinner.
        console.error(error);
        context.commit("loadingExternalHook", true);
        return;
      }
      if (data.state === "PENDING" || data.state == "STARTED") {
        setTimeout(() => {
          context.dispatch("parseExternalHooks", { location: location, epoch: epoch, since: since });
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
              message: vm.$t("pages.navbar.hookUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
        epoch: nextEpoch("Connectors"),
        since: Date.now(),
      });
    },
    async parseConnectors(context, { location, epoch, since }) {
      if (isSuperseded("Connectors", epoch, since)) {
        return;
      }
      const token = context.state.token;
      try {
        const { data } = await axios.get(
          `${this.state.endpoint.api}${location}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (data.state === "PENDING" || data.state == "STARTED") {
          setTimeout(() => {
            context.dispatch("parseConnectors", { location: location, epoch: epoch, since: since });
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
              message: vm.$t("pages.navbar.connectorUpdated"),
              color: "success",
            });
          }
        })
        .catch((error) => {
          console.error(error);
          vm.$vaToast.init({
            title: vm.$t("pages.navbar.errorTitle"),
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
    // Payload of the login and password change routes.
    setSession(state: any, payload: any) {
      state.token = payload.access_token;
      state.user = payload.user;
      state.userName = payload.user.name;
      saveSession({
        token: payload.access_token,
        user: payload.user,
        expiresAt: Date.now() + payload.expires_in * 1000,
      });
    },
    refreshStarted(state: any) {
      state.refresh.running = true;
    },
    refreshFinished(state: any) {
      state.refresh.running = false;
      state.refresh.lastAt = Date.now();
      state.refresh.tick += 1;
    },
    setRefreshSeconds(state: any, seconds: number) {
      state.refresh.seconds = seconds;
      try {
        localStorage.setItem(REFRESH_KEY, String(seconds));
      } catch {
        // The choice is then kept until the page is closed.
      }
    },
    logout(state: any) {
      state.token = null;
      state.user = null;
      state.userName = null;
      saveSession(null);
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
    vmWarnings(state, warnings) {
      state.resources.vmWarnings = warnings;
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
