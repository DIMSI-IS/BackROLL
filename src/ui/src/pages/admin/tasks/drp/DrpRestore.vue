<template>
  <div>
    <va-card class="mb-3">
      <va-card-title>
        <h1>{{ $t('pages.tasks.drp.title') }}</h1>
      </va-card-title>
      <va-card-content>
        <p class="info">
          {{ $t('pages.tasks.drp.descriptionBefore') }} <b>{{ $t('pages.tasks.drp.descriptionNew') }}</b> {{ $t('pages.tasks.drp.descriptionAfter') }}
        </p>
      </va-card-content>
    </va-card>

    <va-card class="mb-3">
      <va-card-title>
        <h2>{{ $t('pages.tasks.drp.step1') }}</h2>
      </va-card-title>
      <va-card-content>
        <div class="row">
          <va-select v-model="storageId" :label="$t('pages.tasks.drp.backupStorage')" :options="storageOptions" value-by="value"
            text-by="text" @update:modelValue="loadRepositories" />
          <va-select v-model="repository" :label="$t('pages.tasks.drp.vmBackedUp')" :options="repositories" :disabled="!storageId"
            searchable @update:modelValue="loadArchives" />
        </div>

        <va-data-table :no-data-html="$t('pages.common.noItems')" v-if="disks.length" class="mt-3" :items="disks" :columns="diskColumns">
          <template #cell(include)="{ rowIndex }">
            <simple-checkbox v-model="disks[rowIndex].include" @update:modelValue="ensureRoot" />
          </template>
          <template #cell(root)="{ rowIndex }">
            <va-radio v-model="rootDisk" :option="disks[rowIndex].disk" :disabled="!disks[rowIndex].include" />
          </template>
          <template #cell(archive)="{ rowIndex }">
            <va-select v-model="disks[rowIndex].archive" :options="disks[rowIndex].options" value-by="value"
              text-by="text" />
          </template>
        </va-data-table>
        <p v-else-if="repository && !loading" class="mt-3 info">{{ $t('pages.tasks.drp.noBackup') }}</p>
      </va-card-content>
    </va-card>

    <va-card class="mb-3">
      <va-card-title>
        <h2>{{ $t('pages.tasks.drp.step2') }}</h2>
      </va-card-title>
      <va-card-content>
        <div class="row">
          <va-select v-model="connectorId" :label="$t('pages.tasks.drp.connector')" :options="connectorOptions"
            value-by="value" text-by="text" @update:modelValue="loadOptions" />
        </div>

        <div v-if="options" class="grid mt-3">
          <va-select v-model="domainId" :label="$t('pages.tasks.drp.domain')" :options="domainOptions"
            value-by="value" text-by="text" clearable searchable @update:modelValue="onDomainChange" />
          <va-select v-if="domainId" v-model="account" :label="$t('pages.tasks.drp.account')" :options="accountOptions" value-by="value"
            text-by="text" @update:modelValue="onAccountChange" />
          <va-input v-model="name" :label="$t('pages.tasks.drp.newVmName')" :rules="[nameRule]" />
          <va-select v-model="zoneId" :label="$t('pages.tasks.drp.zone')" :options="zoneOptions" value-by="value" text-by="text" />
          <va-select v-model="serviceOfferingId" :label="$t('pages.tasks.drp.computeOffering')" :options="offeringOptions" value-by="value"
            text-by="text" />
          <va-select v-model="templateId" :label="$t('pages.tasks.drp.template')" :options="templateOptions"
            value-by="value" text-by="text" searchable />
          <va-select v-model="networkId"
            :label="networkOptions.length > 1 ? $t('pages.tasks.drp.networkRequired') : $t('pages.tasks.drp.network')"
            :options="networkOptions" value-by="value" text-by="text" clearable />
          <va-input v-model="ipAddress" :label="$t('pages.tasks.drp.ipAddress')" :disabled="!networkId"
            :rules="[ipRule]" />
          <va-select v-if="includedDisks.length > 1" v-model="dataDiskOfferingId" :label="$t('pages.tasks.drp.dataDiskOffering')"
            :options="diskOfferingOptions" value-by="value" text-by="text" />
          <simple-checkbox v-model="startAfter" :label="$t('pages.tasks.drp.startAfter')" />
          <simple-checkbox v-model="cleanupOnFailure" :label="$t('pages.tasks.drp.cleanupOnFailure')" />
          <va-select v-model="hookId" class="drp-hook" :label="$t('pages.tasks.drp.notifyHook')" :options="hookOptions"
            value-by="value" text-by="text" clearable :placeholder="$t('pages.tasks.drp.notifyNobody')" />
        </div>
        <va-alert v-if="options && !options.mounted_pools.length" class="mt-3" color="danger" border="top">
          {{ $t('pages.tasks.drp.noPrimaryStorage') }}
        </va-alert>
      </va-card-content>
    </va-card>

    <va-card>
      <va-card-title>
        <h2>{{ $t('pages.tasks.drp.step3') }}</h2>
      </va-card-title>
      <va-card-content>
        <va-button :disabled="!canRestore || running" @click="showConfirm = true">{{ $t('pages.tasks.drp.restoreButton') }}</va-button>

        <div v-if="running" class="flex-center ma-3 column">
          <spring-spinner :animation-duration="2000" :size="40" color="#2c82e0" />
          <p class="mt-3">{{ step }}</p>
        </div>
        <va-alert v-if="failure" class="mt-3" color="danger" border="top">{{ failure }}</va-alert>
        <va-alert v-if="done" class="mt-3" color="success" border="top">
          {{ $t('pages.tasks.drp.vmBefore') }} <b>{{ done.vm_name }}</b>
          {{ $t('pages.tasks.drp.created', { count: done.volumes.length, state: done.started ? $t('pages.tasks.drp.started') : $t('pages.tasks.drp.stopped'), id: done.vm_id }) }}
        </va-alert>
      </va-card-content>
    </va-card>

    <va-card class="mt-3">
      <va-card-title>
        <div class="history-header">
          <h2>{{ $t('pages.tasks.drp.history') }}</h2>
          <va-button icon="refresh" size="small" @click="loadHistory">{{ $t('pages.tasks.drp.refresh') }}</va-button>
        </div>
      </va-card-title>
      <va-card-content>
        <va-data-table :no-data-html="$t('pages.common.noItems')" :items="runs" :columns="historyColumns">
          <template #cell(created_at)="{ rowIndex }">
            {{ new Date(runs[rowIndex].created_at).toLocaleString() }}
          </template>
          <template #cell(target)="{ rowIndex }">{{ targetOf(runs[rowIndex]) }}</template>
          <template #cell(status)="{ rowIndex }">
            <va-chip size="small" outline square :color="statusColors[runs[rowIndex].status]">
              {{ statusText(runs[rowIndex].status) }}
            </va-chip>
          </template>
          <template #cell(duration)="{ rowIndex }">{{ durationOf(runs[rowIndex]) }}</template>
          <template #cell(actions)="{ rowIndex }">
            <va-button size="small" icon="info" @click="openRun(runs[rowIndex])" />
          </template>
        </va-data-table>
        <div class="history-footer mt-3">
          <span>{{ $t('pages.tasks.drp.restoreCount', { count: runsTotal }) }}</span>
          <va-pagination v-if="historyPages > 1" v-model="historyPage" :pages="historyPages" :visible-pages="5"
            @update:modelValue="loadHistory" />
        </div>
      </va-card-content>
    </va-card>

    <va-modal v-model="showRun" hide-default-actions size="large">
      <template #header>
        <h2>
          <va-icon name="history" color="info" />
          {{ $t('pages.tasks.drp.restoreOf', { name: selectedRun?.vm_name }) }}
        </h2>
      </template>
      <hr>
      <div v-if="selectedRun" class="run-details">
        <p>
          <va-chip size="small" outline square :color="statusColors[selectedRun.status]">{{ selectedRun.status }}</va-chip>
          {{ $t('pages.tasks.drp.startedBy') }} <b>{{ selectedRun.username || $t('pages.tasks.drp.unknown') }}</b> {{ $t('pages.tasks.drp.on') }}
          {{ new Date(selectedRun.created_at).toLocaleString() }}
          <span v-if="selectedRun.finished_at">({{ durationOf(selectedRun) }})</span>
        </p>
        <p><b>{{ $t('pages.tasks.drp.source') }}</b> {{ $t('pages.tasks.drp.diskCount', { repository: selectedRun.repository, count: selectedRun.disks.length }) }}<br>
          <small>{{ selectedRun.disks.join(", ") }}</small></p>
        <p><b>{{ $t('pages.tasks.drp.target') }}</b> {{ targetOf(selectedRun) }}</p>
        <p><b>{{ $t('pages.tasks.drp.newVm') }}</b> {{ selectedRun.vm_name }}
          <span v-if="selectedRun.vm_id">{{ $t('pages.tasks.drp.cloudstackId', { id: selectedRun.vm_id }) }}</span></p>
        <va-alert v-if="selectedRun.error" color="danger" border="top" class="mb-3">{{ selectedRun.error }}</va-alert>
        <p><b>{{ $t('pages.tasks.drp.steps') }}</b></p>
        <pre class="run-log">{{ selectedRun.log || $t('pages.tasks.drp.noStep') }}</pre>
      </div>
      <template #footer>
        <va-button @click="showRun = false">{{ $t('pages.tasks.drp.close') }}</va-button>
      </template>
    </va-modal>

    <va-modal v-model="showConfirm" :ok-text="$t('pages.tasks.drp.confirmOk')" @ok="restore">
      <template #header>
        <h2>
          <va-icon name="settings_backup_restore" color="info" />
          {{ $t('pages.tasks.drp.confirmTitle') }}
        </h2>
      </template>
      <hr>
      <div>
        <b>{{ repository }}</b> {{ $t('pages.tasks.drp.confirmMiddle', { count: includedDisks.length }) }} <b>{{ name }}</b>{{ $t('pages.tasks.drp.confirmAfter') }}
      </div>
    </va-modal>
  </div>
</template>

<script>
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import axios from "axios";

const HISTORY_PAGE_SIZE = 10;

export default defineComponent({
  name: "DrpRestore",
  components: { ...spinners, SimpleCheckbox },
  data() {
    return {
      storageId: null,
      repositories: [],
      repository: null,
      disks: [],
      rootDisk: null,
      loading: false,
      connectorId: null,
      options: null,
      domainId: null,
      account: null,
      accounts: [],
      name: "",
      zoneId: null,
      serviceOfferingId: null,
      templateId: null,
      networkId: null,
      ipAddress: "",
      dataDiskOfferingId: null,
      startAfter: true,
      cleanupOnFailure: false,
      hookId: null,
      showConfirm: false,
      runs: [],
      runsTotal: 0,
      historyPage: 1,
      historyTimer: null,
      showRun: false,
      selectedRun: null,
      statusColors: { success: "success", failed: "danger", running: "info", queued: "warning" },
      running: false,
      step: "",
      failure: null,
      done: null,
    };
  },
  computed: {
    hookOptions() {
      return this.$store.state.resources.externalHookList.map((hook) => ({ value: hook.id, text: hook.name }));
    },
    historyColumns() {
      return [
        { key: "created_at", label: this.$t("pages.tasks.drp.historyColumns.date") },
        { key: "username", label: this.$t("pages.tasks.drp.historyColumns.user") },
        { key: "repository", label: this.$t("pages.tasks.drp.historyColumns.source") },
        { key: "target", label: this.$t("pages.tasks.drp.historyColumns.target") },
        { key: "vm_name", label: this.$t("pages.tasks.drp.historyColumns.newVm") },
        { key: "status", label: this.$t("pages.tasks.drp.historyColumns.status") },
        { key: "duration", label: this.$t("pages.tasks.drp.historyColumns.duration") },
        { key: "actions", label: this.$t("pages.tasks.drp.historyColumns.actions") },
      ];
    },
    diskColumns() {
      return [
        { key: "disk", label: this.$t("pages.tasks.drp.diskColumns.disk") },
        { key: "include", label: this.$t("pages.tasks.drp.diskColumns.restore") },
        { key: "root", label: this.$t("pages.tasks.drp.diskColumns.root") },
        { key: "archive", label: this.$t("pages.tasks.drp.diskColumns.backup") },
      ];
    },
    api() {
      return `${this.$store.state.endpoint.api}/api/v1`;
    },
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    storageOptions() {
      return this.$store.state.storageList.map((s) => ({ value: s.id, text: `${s.name} (${s.path})` }));
    },
    connectorOptions() {
      return this.$store.state.resources.connectorList.map((c) => ({ value: c.id, text: `${c.name} (${c.url})` }));
    },
    includedDisks() {
      return this.disks.filter((d) => d.include);
    },
    domainOptions() {
      return (this.options?.domains ?? []).map((d) => ({ value: d.id, text: d.path }));
    },
    accountOptions() {
      return this.accounts.map((a) => ({ value: a.name, text: a.name }));
    },
    zoneOptions() {
      return (this.options?.zones ?? []).map((z) => ({ value: z.id, text: z.name }));
    },
    offeringOptions() {
      return (this.options?.service_offerings ?? []).map((o) => ({
        value: o.id,
        text: `${o.name}${o.cpus ? ` (${o.cpus} CPU, ${o.memory} MB)` : ""}`,
      }));
    },
    templateOptions() {
      return (this.options?.templates ?? [])
        .filter((t) => !this.zoneId || !t.zone_id || t.zone_id === this.zoneId)
        .map((t) => ({ value: t.id, text: t.name }));
    },
    networkOptions() {
      return (this.options?.networks ?? [])
        .filter((n) => !this.zoneId || !n.zone_id || n.zone_id === this.zoneId)
        .map((n) => ({ value: n.id, text: `${n.name}${n.cidr ? ` (${n.cidr})` : ""}` }));
    },
    diskOfferingOptions() {
      return (this.options?.disk_offerings ?? [])
        .filter((d) => d.custom)
        .map((d) => ({ value: d.id, text: d.name }));
    },
    historyPages() {
      return Math.ceil(this.runsTotal / HISTORY_PAGE_SIZE);
    },
    canRestore() {
      return (
        this.repository && this.includedDisks.length > 0 && this.rootDisk && this.connectorId && this.options &&
        this.nameRule(this.name) === true && this.ipRule(this.ipAddress) === true &&
        this.zoneId && this.serviceOfferingId && this.templateId &&
        (!this.domainId || this.account) &&
        // With several networks, CloudStack can not choose for us.
        (this.networkOptions.length < 2 || this.networkId) &&
        (this.includedDisks.length < 2 || this.dataDiskOfferingId)
      );
    },
  },
  methods: {
    // A status the page does not know is shown as received.
    statusText(status) {
      const key = `pages.tasks.drp.status.${status}`;
      return this.$te(key) ? this.$t(key) : status;
    },
    nameRule(value) {
      return /^[A-Za-z0-9][A-Za-z0-9-]{0,62}$/.test(value) || this.$t("pages.tasks.drp.nameRule");
    },
    ipRule(value) {
      return !value || /^(\d{1,3}\.){3}\d{1,3}$/.test(value) || this.$t("pages.tasks.drp.ipRule");
    },
    detail(error) {
      const detail = error?.response?.data?.detail;
      if (detail && typeof detail === "object") return detail.status ?? detail[0]?.msg ?? JSON.stringify(detail);
      return detail ?? String(error);
    },
    notify(title, error) {
      console.error(error);
      this.$vaToast.init({ title, message: this.detail(error), color: "danger" });
    },
    async loadRepositories() {
      this.repository = null;
      this.disks = [];
      this.repositories = [];
      try {
        const { data } = await axios.get(`${this.api}/drp/repositories`, {
          params: { storage_id: this.storageId }, headers: this.headers,
        });
        this.repositories = data.repositories;
      } catch (error) {
        this.notify(this.$t("pages.tasks.drp.errListVms"), error);
      }
    },
    async loadArchives() {
      this.disks = [];
      if (!this.repository) return;
      this.loading = true;
      try {
        const { data } = await axios.get(
          `${this.api}/drp/repositories/${encodeURIComponent(this.repository)}/archives`,
          { params: { storage_id: this.storageId }, headers: this.headers });
        // Archives are sorted from the newest: the first of a disk is its latest backup.
        const byDisk = {};
        for (const archive of data.archives) {
          (byDisk[archive.disk] ||= []).push(archive);
        }
        this.disks = Object.entries(byDisk).map(([disk, archives]) => ({
          disk,
          include: true,
          archive: archives[0].name,
          options: archives.map((a) => ({ value: a.name, text: new Date(a.start).toLocaleString() })),
        }));
        const root = this.disks.find((d) => /^(ROOT|vda)/i.test(d.disk)) ?? this.disks[0];
        this.rootDisk = root ? root.disk : null;
        if (root) this.name = `${this.repository.replace(/[^A-Za-z0-9-]/g, "-")}-restored`.slice(0, 63);
      } catch (error) {
        this.notify(this.$t("pages.tasks.drp.errListBackups"), error);
      } finally {
        this.loading = false;
      }
    },
    ensureRoot() {
      const current = this.disks.find((d) => d.disk === this.rootDisk);
      if (!current || !current.include) this.rootDisk = this.includedDisks[0]?.disk ?? null;
    },
    // The offerings depend on the account the VM is created for.
    async loadOptions(keepForm = false) {
      if (!keepForm) {
        this.options = null;
        this.domainId = null;
        this.account = null;
        this.accounts = [];
      }
      try {
        const params = {};
        if (this.domainId && this.account) {
          params.domain_id = this.domainId;
          params.account = this.account;
        }
        const { data } = await axios.get(`${this.api}/drp/cloudstack/${this.connectorId}/options`, {
          params, headers: this.headers,
        });
        this.options = data;
        if (!keepForm) this.zoneId = data.zones.length === 1 ? data.zones[0].id : null;
      } catch (error) {
        this.notify(this.$t("pages.tasks.drp.errReadEnv"), error);
      }
    },
    async onDomainChange() {
      this.account = null;
      this.accounts = [];
      this.templateId = null;
      this.networkId = null;
      if (!this.domainId) {
        await this.loadOptions(true);
        return;
      }
      try {
        const { data } = await axios.get(`${this.api}/drp/cloudstack/${this.connectorId}/accounts`, {
          params: { domain_id: this.domainId }, headers: this.headers,
        });
        this.accounts = data.accounts;
        if (data.accounts.length === 1) {
          this.account = data.accounts[0].name;
          await this.onAccountChange();
        }
      } catch (error) {
        this.notify(this.$t("pages.tasks.drp.errListAccounts"), error);
      }
    },
    async onAccountChange() {
      // Only the templates and networks of this account can be used.
      this.templateId = null;
      this.networkId = null;
      await this.loadOptions(true);
    },
    targetOf(run) {
      const where = run.account ? `${run.domain_name || this.$t("pages.tasks.drp.domainFallback")} / ${run.account}` : this.$t("pages.tasks.drp.connectorAccount");
      return `${run.connector_name || "?"}: ${where}`;
    },
    durationOf(run) {
      const end = run.finished_at ? new Date(run.finished_at) : new Date();
      const seconds = Math.max(0, Math.round((end - new Date(run.created_at)) / 1000));
      return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
    },
    async loadHistory() {
      try {
        const { data } = await axios.get(`${this.api}/drp/history`, {
          params: { limit: HISTORY_PAGE_SIZE, offset: (this.historyPage - 1) * HISTORY_PAGE_SIZE },
          headers: this.headers,
        });
        this.runs = data.items;
        this.runsTotal = data.total;
      } catch (error) {
        console.error(error);
      }
    },
    async openRun(run) {
      try {
        const { data } = await axios.get(`${this.api}/drp/history/${run.id}`, { headers: this.headers });
        this.selectedRun = data;
        this.showRun = true;
      } catch (error) {
        this.notify(this.$t("pages.tasks.drp.errReadRestore"), error);
      }
    },
    async restore() {
      this.failure = null;
      this.done = null;
      // The root disk first.
      const ordered = [...this.includedDisks].sort((a, b) => (b.disk === this.rootDisk) - (a.disk === this.rootDisk));
      try {
        const { data } = await axios.post(`${this.api}/drp/restore`, {
          storage_id: this.storageId,
          repository: this.repository,
          disks: ordered.map((d) => d.archive),
          connector_id: this.connectorId,
          name: this.name,
          zone_id: this.zoneId,
          service_offering_id: this.serviceOfferingId,
          template_id: this.templateId,
          network_id: this.networkId || null,
          ip_address: this.ipAddress || null,
          data_disk_offering_id: ordered.length > 1 ? this.dataDiskOfferingId : null,
          domain_id: this.domainId || null,
          domain_name: this.domainId ? this.domainOptions.find((d) => d.value === this.domainId)?.text : null,
          account: this.account || null,
          cleanup_on_failure: this.cleanupOnFailure,
          start_after: this.startAfter,
          hook_id: this.hookId || null,
        }, { headers: this.headers });
        this.running = true;
        this.step = this.$t("pages.tasks.drp.starting");
        this.historyPage = 1;
        this.loadHistory();
        await this.track(data.Location);
      } catch (error) {
        this.failure = this.detail(error);
      } finally {
        this.running = false;
        this.loadHistory();
      }
    },
    async track(location) {
      for (;;) {
        const { data } = await axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: this.headers });
        if (data.state === "SUCCESS") {
          this.done = data.info;
          return;
        }
        if (data.state === "PROGRESS" && data.info?.step) this.step = data.info.step;
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    },
  },
  watch: {
    // With a single hook, it is the one to tell: it can still be cleared.
    "$store.state.resources.externalHookList": {
      immediate: true,
      handler(list) {
        if (this.hookId === null && list.length === 1) {
          this.hookId = list[0].id;
        }
      },
    },
  },
  mounted() {
    this.$store.dispatch("requestStorage");
    this.$store.dispatch("requestConnector");
    this.$store.dispatch("requestExternalHook");
    this.loadHistory();
    // While a restore is running, its line follows it.
    this.historyTimer = setInterval(() => {
      if (this.running || this.runs.some((run) => ["queued", "running"].includes(run.status))) {
        this.loadHistory();
      }
    }, 4000);
  },
  beforeUnmount() {
    clearInterval(this.historyTimer);
  },
});
</script>

<style scoped>
.row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.row>* {
  min-width: 18rem;
  flex: 1;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
  align-items: end;
}

.column {
  flex-direction: column;
}

.info {
  color: var(--va-gray);
}

.history-header,
.history-footer {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
}

.run-log {
  max-height: 16rem;
  overflow: auto;
  background: var(--va-background);
  padding: 0.75rem;
  font-size: 0.85rem;
  white-space: pre-wrap;
}
</style>
