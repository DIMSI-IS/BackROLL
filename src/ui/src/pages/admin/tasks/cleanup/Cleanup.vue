<template>
  <div>
    <va-card class="mb-3">
      <va-card-title>
        <h1>{{ $t('pages.cleanup.title') }}</h1>
      </va-card-title>
      <va-card-content>
        <p class="info mb-3">{{ $t('pages.cleanup.intro') }}</p>
        <va-alert v-if="!isAdmin" color="info" border="top" class="mb-3">{{ $t('pages.cleanup.readOnly') }}</va-alert>
        <va-select v-model="storageId" :label="$t('pages.cleanup.storage')" :options="storageOptions" value-by="value"
          text-by="text" @update:modelValue="onStorageChange" />
        <p v-if="loaded && !storages.length" class="mt-3 info">{{ $t('pages.cleanup.noStorage') }}</p>
      </va-card-content>
    </va-card>

    <template v-if="storage">
      <va-card class="mb-3">
        <va-card-title>
          <h2>{{ $t('pages.cleanup.automatic.title') }}</h2>
        </va-card-title>
        <va-card-content>
          <va-alert color="warning" border="top" class="mb-3">{{ $t('pages.cleanup.automatic.warning') }}</va-alert>

          <div class="grid">
            <va-input v-model.number="form.keep_days" type="number" min="1" max="3650" :disabled="!isAdmin"
              :label="$t('pages.cleanup.automatic.keepDays')"
              :rules="[() => keepDaysValid || $t('pages.cleanup.automatic.range', { min: 1, max: 3650 })]">
              <template #appendInner>
                <span class="unit">{{ $t('pages.cleanup.automatic.keepDaysUnit') }}</span>
              </template>
            </va-input>
            <va-select v-model="hookId" :label="$t('pages.cleanup.automatic.hook')" :options="hookOptions"
              value-by="value" text-by="text" clearable :disabled="!isAdmin" />
          </div>

          <p class="info mt-2 keep-example">{{ $t('pages.cleanup.automatic.keepDaysExample') }}</p>
          <va-alert v-if="lowDays" color="warning" border="top" class="mt-2 low-days">
            {{ $t('pages.cleanup.automatic.lowDays', { days: form.keep_days }) }}
          </va-alert>

          <div class="mt-3">
            <simple-checkbox toggle v-model="form.after_backup" :disabled="!isAdmin"
              :label="$t('pages.cleanup.automatic.afterBackup')" />
          </div>
          <div class="mt-3">
            <simple-checkbox toggle v-model="form.scheduled" :disabled="!isAdmin"
              :label="$t('pages.cleanup.automatic.scheduled')" />
          </div>

          <div v-if="form.scheduled" class="schedule mt-3">
            <div v-if="!rawMode" class="grid">
              <va-select v-model="freqKind" :label="$t('pages.cleanup.automatic.frequency')" :options="frequencyOptions"
                value-by="value" text-by="text" :disabled="!isAdmin" />
              <va-select v-if="freqKind === 'week'" v-model="weekday" :label="$t('pages.cleanup.automatic.weekday')"
                :options="weekdayOptions" value-by="value" text-by="text" :disabled="!isAdmin" />
              <va-input v-model="time" type="time" :label="$t('pages.cleanup.automatic.time')" :disabled="!isAdmin"
                :rules="[() => timeValid || $t('pages.cleanup.automatic.cronInvalid')]" />
            </div>
            <va-input v-else v-model="rawCron" :label="$t('pages.cleanup.automatic.cron')" :disabled="!isAdmin"
              :rules="[() => cronValid || $t('pages.cleanup.automatic.cronInvalid')]" />
            <simple-checkbox class="mt-2" :model-value="rawMode" :label="$t('pages.cleanup.automatic.rawMode')"
              :disabled="!isAdmin" @update:modelValue="toggleRaw" />
            <p v-if="cronText" class="mt-2">
              {{ $t('pages.cleanup.automatic.runs') }} <b>{{ cronText }}</b>
              <span class="info">({{ cron }})</span>
            </p>
          </div>

          <va-button class="mt-4" :disabled="!isAdmin || !canSave" :loading="saving" @click="save">
            {{ $t('pages.cleanup.automatic.save') }}
          </va-button>
        </va-card-content>
      </va-card>

      <va-card class="mb-3">
        <va-card-title>
          <h2>{{ $t('pages.cleanup.run.title') }}</h2>
        </va-card-title>
        <va-card-content>
          <p class="info mb-3">{{ $t('pages.cleanup.run.help') }}</p>
          <va-alert v-if="dirty" color="info" border="top" class="mb-3 unsaved">
            {{ $t('pages.cleanup.run.unsaved') }}
          </va-alert>
          <div class="selection">
            <va-button class="simulate-button" :disabled="!isAdmin || !keepDaysValid || dirty || busy || simulating"
              :loading="simulating" @click="simulate">
              {{ $t('pages.cleanup.simulation.button') }}
            </va-button>
            <va-button class="run-button" color="danger" :disabled="!isAdmin || !keepDaysValid || dirty || busy"
              @click="showRunConfirm = true">
              {{ $t('pages.cleanup.run.button') }}
            </va-button>
          </div>
          <div v-if="following" class="flex-center ma-3 column">
            <spring-spinner :animation-duration="2000" :size="40" color="#2c82e0" />
            <p class="mt-3">{{ $t('pages.cleanup.run.following') }}</p>
          </div>

          <div v-if="simulating" class="flex-center ma-3 column">
            <spring-spinner :animation-duration="2000" :size="40" color="#2c82e0" />
            <p class="mt-3">{{ $t('pages.cleanup.simulation.calculating') }}</p>
          </div>
          <va-alert v-if="simFailure" class="mt-3" color="danger" border="top">
            {{ $t('pages.cleanup.simulation.failed') }}: {{ simFailure }}
          </va-alert>

          <div v-if="simResult && !simulating" class="simulation mt-4">
            <p><b>{{ $t('pages.cleanup.simulation.days', { days: simResult.keep_days }) }}</b></p>
            <va-alert v-if="(simResult.errors || []).length" class="mt-2" color="warning" border="top">
              <p>{{ $t('pages.cleanup.simulation.errors') }}</p>
              <ul class="warnings">
                <li v-for="(item, index) in simResult.errors" :key="index">{{ item.name }}: {{ item.error }}</li>
              </ul>
            </va-alert>
            <p v-if="!simRepositories.length" class="mt-3 info sim-none">{{ $t('pages.cleanup.simulation.none') }}</p>
            <template v-else>
              <p class="info mt-2">{{ $t('pages.cleanup.simulation.hint') }}</p>
              <div class="selection mt-3">
                <va-button size="small" preset="secondary" :disabled="!isAdmin" @click="selectAllSimulated">
                  {{ $t('pages.cleanup.simulation.selectAll') }}
                </va-button>
                <va-button size="small" preset="secondary" :disabled="!checkedCount" @click="checked = {}">
                  {{ $t('pages.cleanup.simulation.selectNone') }}
                </va-button>
                <span class="info sim-count">{{ $tc('pages.cleanup.simulation.selected', checkedCount) }}</span>
              </div>
              <div v-for="repo in simRepositories" :key="repo.name" class="sim-repo mt-3">
                <div class="sim-head">
                  <simple-checkbox class="repo-box" :disabled="!isAdmin" :model-value="repoAllChecked(repo)"
                    @update:modelValue="toggleRepo(repo, $event)" />
                  <b>{{ repo.name }}</b>
                  <span class="info">
                    {{ $t('pages.cleanup.simulation.repoSummary', { count: checkedIn(repo), total: repo.delete.length, kept: repo.kept }) }}
                  </span>
                  <va-button size="small" preset="secondary" class="expand-button" @click="toggleOpen(repo.name)">
                    {{ openRepos.includes(repo.name) ? $t('pages.cleanup.simulation.hide') : $t('pages.cleanup.simulation.show') }}
                  </va-button>
                </div>
                <ul v-if="openRepos.includes(repo.name)" class="sim-list">
                  <li v-for="item in repo.delete" :key="item.name">
                    <simple-checkbox class="archive-box" :disabled="!isAdmin"
                      :model-value="isChecked(repo.name, item.name)"
                      :label="`${item.name} - ${formatDate(item.time)}`"
                      @update:modelValue="toggleArchive(repo.name, item.name, $event)" />
                  </li>
                </ul>
              </div>
              <va-button class="mt-3 delete-selection" color="danger" :disabled="!isAdmin || !checkedCount || busy"
                @click="openSimDelete">
                {{ $t('pages.cleanup.simulation.delete') }}
              </va-button>
            </template>
          </div>
        </va-card-content>
      </va-card>

      <va-card class="mb-3">
        <va-card-title>
          <h2>{{ $t('pages.cleanup.orphans.title') }}</h2>
        </va-card-title>
        <va-card-content>
          <p class="info mb-3">{{ $t('pages.cleanup.orphans.help') }}</p>
          <va-button :disabled="!isAdmin || scanning || busy" :loading="scanning" @click="scan">
            {{ $t('pages.cleanup.orphans.scan') }}
          </va-button>
          <div v-if="scanning" class="flex-center ma-3 column">
            <spring-spinner :animation-duration="2000" :size="40" color="#2c82e0" />
            <p class="mt-3">{{ $t('pages.cleanup.orphans.scanning') }}</p>
          </div>
          <va-alert v-if="scanFailure" class="mt-3" color="danger" border="top">
            {{ $t('pages.cleanup.orphans.scanFailed') }}: {{ scanFailure }}
          </va-alert>

          <template v-if="scanResult && !scanning">
            <va-alert v-if="!scanResult.complete" class="mt-3" color="warning" border="top">
              <p>{{ $t('pages.cleanup.orphans.incomplete') }}</p>
              <ul class="warnings">
                <li v-for="(warning, index) in scanResult.warnings || []" :key="index">{{ warning }}</li>
              </ul>
            </va-alert>
            <p class="mt-3">{{ $tc('pages.cleanup.orphans.machines', scanResult.machines) }}</p>
            <p v-if="!orphans.length" class="mt-3 info">{{ $t('pages.cleanup.orphans.none') }}</p>
            <template v-else>
              <div class="selection mt-3">
                <va-button size="small" preset="secondary" :disabled="!canDeleteOrphans" @click="selectAll">
                  {{ $t('pages.cleanup.orphans.selectAll') }}
                </va-button>
                <va-button size="small" preset="secondary" :disabled="!selected.length" @click="selected = []">
                  {{ $t('pages.cleanup.orphans.selectNone') }}
                </va-button>
                <span class="info">{{ $t('pages.cleanup.orphans.selected', { count: selected.length }) }}</span>
              </div>
              <va-data-table :no-data-html="$t('pages.common.noItems')" class="mt-2" :items="orphans" :columns="orphanColumns">
                <template #cell(select)="{ rowIndex }">
                  <simple-checkbox :model-value="selected.includes(orphans[rowIndex].name)"
                    :disabled="!canDeleteOrphans" @update:modelValue="toggle(orphans[rowIndex].name)" />
                </template>
                <template #cell(last_backup)="{ rowIndex }">
                  {{ orphans[rowIndex].last_backup ? formatDate(orphans[rowIndex].last_backup) : $t('pages.cleanup.orphans.never') }}
                </template>
                <template #cell(size_bytes)="{ rowIndex }">{{ humanSize(orphans[rowIndex].size_bytes) }}</template>
              </va-data-table>
              <va-button class="mt-3" color="danger" :disabled="!canDeleteOrphans || !selected.length || busy"
                @click="openDelete">
                {{ $t('pages.cleanup.orphans.delete') }}
              </va-button>
            </template>
          </template>
        </va-card-content>
      </va-card>
    </template>

    <va-card>
      <va-card-title>
        <div class="history-header">
          <h2>{{ $t('pages.cleanup.history.title') }}</h2>
          <va-button icon="refresh" size="small" @click="loadRuns">{{ $t('pages.cleanup.refresh') }}</va-button>
        </div>
      </va-card-title>
      <va-card-content>
        <va-data-table :no-data-html="$t('pages.common.noItems')" :items="runs" :columns="historyColumns">
          <template #cell(started_at)="{ rowIndex }">{{ formatDate(runs[rowIndex].started_at) }}</template>
          <template #cell(kind)="{ rowIndex }">{{ kindText(runs[rowIndex].kind) }}</template>
          <template #cell(trigger)="{ rowIndex }">{{ triggerText(runs[rowIndex].trigger) }}</template>
          <template #cell(user)="{ rowIndex }">{{ runs[rowIndex].user || $t('pages.cleanup.history.system') }}</template>
          <template #cell(status)="{ rowIndex }">
            <va-chip size="small" outline square :color="statusColors[runs[rowIndex].status]">
              {{ statusText(runs[rowIndex].status) }}
            </va-chip>
          </template>
          <template #cell(summary)="{ rowIndex }">{{ summaryText(runs[rowIndex]) }}</template>
          <template #cell(actions)="{ rowIndex }">
            <va-button size="small" icon="info" @click="openRun(runs[rowIndex])" />
          </template>
        </va-data-table>
        <p v-if="!runs.length" class="mt-3 info">{{ $t('pages.cleanup.history.empty') }}</p>
        <div class="mt-3">{{ $tc('pages.cleanup.history.count', runs.length) }}</div>
      </va-card-content>
    </va-card>

    <va-modal v-model="showRunConfirm" :ok-text="$t('pages.cleanup.run.confirmOk')"
      :cancel-text="$t('pages.cleanup.cancel')" @ok="runNow">
      <template #header>
        <h2>
          <va-icon name="delete_sweep" color="danger" />
          {{ $t('pages.cleanup.run.confirmTitle') }}
        </h2>
      </template>
      <hr>
      <div>{{ $t('pages.cleanup.run.confirm', { days: form.keep_days, storage: storage ? storage.storage_name : '' }) }}</div>
      <va-alert v-if="lowDays" color="warning" border="top" class="mt-3">
        {{ $t('pages.cleanup.automatic.lowDays', { days: form.keep_days }) }}
      </va-alert>
    </va-modal>

    <va-modal v-model="showSimDelete" hide-default-actions>
      <template #header>
        <h2>
          <va-icon name="delete_forever" color="danger" />
          {{ $t('pages.cleanup.simulation.deleteTitle') }}
        </h2>
      </template>
      <hr>
      <div>
        <p>
          {{ $t('pages.cleanup.simulation.deleteIntro', {
            backups: $tc('pages.cleanup.simulation.backups', checkedCount),
            repositories: $tc('pages.cleanup.simulation.repositories', checkedRepositories),
          }) }}
        </p>
        <va-alert v-if="lowDays" color="warning" border="top" class="mt-3">
          {{ $t('pages.cleanup.automatic.lowDays', { days: form.keep_days }) }}
        </va-alert>
        <va-input v-model="typed" class="mt-3" :label="$t('pages.cleanup.orphans.typeToConfirm', { word: confirmWord })" />
      </div>
      <template #footer>
        <va-button preset="secondary" class="mr-2" @click="showSimDelete = false">{{ $t('pages.cleanup.cancel') }}</va-button>
        <va-button color="danger" :disabled="!simTypedOk" @click="deleteSimulated">
          {{ $t('pages.cleanup.simulation.deleteOk') }}
        </va-button>
      </template>
    </va-modal>

    <va-modal v-model="showDelete" hide-default-actions>
      <template #header>
        <h2>
          <va-icon name="delete_forever" color="danger" />
          {{ $t('pages.cleanup.orphans.deleteTitle') }}
        </h2>
      </template>
      <hr>
      <div>
        <p>{{ $t('pages.cleanup.orphans.deleteIntro') }}</p>
        <ul class="names">
          <li v-for="name in selected" :key="name"><b>{{ name }}</b></li>
        </ul>
        <va-input v-model="typed" class="mt-3" :label="$t('pages.cleanup.orphans.typeToConfirm', { word: confirmWord })" />
      </div>
      <template #footer>
        <va-button preset="secondary" class="mr-2" @click="showDelete = false">{{ $t('pages.cleanup.cancel') }}</va-button>
        <va-button color="danger" :disabled="!typedOk" @click="deleteOrphans">
          {{ $t('pages.cleanup.orphans.deleteOk') }}
        </va-button>
      </template>
    </va-modal>

    <va-modal v-model="showRun" hide-default-actions size="large">
      <template #header>
        <h2>
          <va-icon name="history" color="info" />
          {{ $t('pages.cleanup.history.detailTitle', { storage: selectedRun ? selectedRun.storage_name : '' }) }}
        </h2>
      </template>
      <hr>
      <div v-if="selectedRun" class="run-details">
        <p>
          <va-chip size="small" outline square :color="statusColors[selectedRun.status]">
            {{ statusText(selectedRun.status) }}
          </va-chip>
          {{ kindText(selectedRun.kind) }} - {{ triggerText(selectedRun.trigger) }}
        </p>
        <p>
          {{ $t('pages.cleanup.history.startedOn') }} {{ formatDate(selectedRun.started_at) }}
          {{ $t('pages.cleanup.history.by') }} <b>{{ selectedRun.user || $t('pages.cleanup.history.system') }}</b>
          <span v-if="selectedRun.finished_at"><br>{{ $t('pages.cleanup.history.finishedOn') }} {{ formatDate(selectedRun.finished_at) }}</span>
        </p>
        <p><b>{{ summaryText(selectedRun) }}</b></p>
        <p><b>{{ $t('pages.cleanup.history.log') }}</b></p>
        <pre class="run-log">{{ selectedRun.log || $t('pages.cleanup.history.noLog') }}</pre>
      </div>
      <template #footer>
        <va-button @click="showRun = false">{{ $t('pages.cleanup.close') }}</va-button>
      </template>
    </va-modal>
  </div>
</template>

<script>
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import axios from "axios";
import cronstrue from "cronstrue/i18n";

const CRON_FIELD = /^\S+(\s+\S+){4}$/;
const TIME = /^([01]?\d|2[0-3]):([0-5]\d)$/;
// Below this number of days, a warning says how little is kept.
const LOW_DAYS = 3;

export default defineComponent({
  name: "Cleanup",
  components: { ...spinners, SimpleCheckbox },
  data() {
    return {
      loaded: false,
      storages: [],
      storageId: null,
      form: { keep_days: 30, after_backup: false, scheduled: false },
      hookId: null,
      freqKind: "day",
      weekday: 0,
      time: "04:00",
      rawMode: false,
      rawCron: "0 4 * * *",
      saving: false,
      showRunConfirm: false,
      following: false,
      scanning: false,
      scanResult: null,
      scanFailure: null,
      selected: [],
      simulating: false,
      simResult: null,
      simFailure: null,
      checked: {},
      openRepos: [],
      showSimDelete: false,
      showDelete: false,
      typed: "",
      runs: [],
      runsTimer: null,
      showRun: false,
      selectedRun: null,
      unmounted: false,
      statusColors: { success: "success", failed: "danger", running: "info" },
    };
  },
  computed: {
    api() {
      return `${this.$store.state.endpoint.api}/api/v1`;
    },
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    isAdmin() {
      return !!this.$store.getters.isAdmin;
    },
    storage() {
      return this.storages.find((s) => s.storage_id === this.storageId) || null;
    },
    storageOptions() {
      return this.storages.map((s) => ({ value: s.storage_id, text: `${s.storage_name} (${s.path})` }));
    },
    hookOptions() {
      return (this.$store.state.resources.externalHookList || []).map((x) => ({ value: x.id, text: x.name }));
    },
    frequencyOptions() {
      return [
        { value: "day", text: this.$t("pages.cleanup.automatic.everyDay") },
        { value: "week", text: this.$t("pages.cleanup.automatic.everyWeek") },
      ];
    },
    weekdayOptions() {
      return [1, 2, 3, 4, 5, 6, 0].map((d) => ({ value: d, text: this.$t(`pages.cleanup.weekdays.${d}`) }));
    },
    orphanColumns() {
      return [
        { key: "select", label: "" },
        { key: "name", label: this.$t("pages.cleanup.orphans.columns.name") },
        { key: "last_backup", label: this.$t("pages.cleanup.orphans.columns.lastBackup") },
        { key: "archives", label: this.$t("pages.cleanup.orphans.columns.archives") },
        { key: "size_bytes", label: this.$t("pages.cleanup.orphans.columns.size") },
      ];
    },
    historyColumns() {
      return [
        { key: "started_at", label: this.$t("pages.cleanup.history.columns.date") },
        { key: "storage_name", label: this.$t("pages.cleanup.history.columns.storage") },
        { key: "kind", label: this.$t("pages.cleanup.history.columns.kind") },
        { key: "trigger", label: this.$t("pages.cleanup.history.columns.trigger") },
        { key: "user", label: this.$t("pages.cleanup.history.columns.user") },
        { key: "status", label: this.$t("pages.cleanup.history.columns.status") },
        { key: "summary", label: this.$t("pages.cleanup.history.columns.summary") },
        { key: "actions", label: this.$t("pages.cleanup.history.columns.actions") },
      ];
    },
    orphans() {
      return this.scanResult?.orphans ?? [];
    },
    canDeleteOrphans() {
      return this.isAdmin && !!this.scanResult && this.scanResult.complete !== false;
    },
    keepDaysValid() {
      const v = this.form.keep_days;
      return Number.isInteger(v) && v >= 1 && v <= 3650;
    },
    // The simulation and the cleaning use the saved number of days: a change that was not saved is not what they do.
    dirty() {
      return !!this.storage && this.form.keep_days !== this.storage.keep_days;
    },
    lowDays() {
      return this.keepDaysValid && this.form.keep_days < LOW_DAYS;
    },
    simRepositories() {
      return this.simResult?.repositories ?? [];
    },
    checkedCount() {
      return Object.keys(this.checked).length;
    },
    checkedRepositories() {
      return this.simRepositories.filter((repo) => this.checkedIn(repo) > 0).length;
    },
    simTypedOk() {
      return this.typed.trim().toLowerCase() === this.confirmWord.toLowerCase() && this.checkedCount > 0;
    },
    timeValid() {
      return TIME.test(this.time || "");
    },
    // The cron produced by the builder, or typed by hand.
    cron() {
      if (this.rawMode) return (this.rawCron || "").trim().replace(/\s+/g, " ");
      const match = TIME.exec(this.time || "");
      if (!match) return "";
      const day = this.freqKind === "week" ? this.weekday : "*";
      return `${Number(match[2])} ${Number(match[1])} * * ${day}`;
    },
    cronText() {
      if (!this.cronValid) return "";
      try {
        return cronstrue.toString(this.cron, { locale: this.$i18n.locale });
      } catch (error) {
        return "";
      }
    },
    cronValid() {
      if (!CRON_FIELD.test(this.cron)) return false;
      try {
        cronstrue.toString(this.cron);
        return true;
      } catch (error) {
        return false;
      }
    },
    canSave() {
      return this.keepDaysValid && (!this.form.scheduled || this.cronValid);
    },
    confirmWord() {
      return this.$t("pages.cleanup.orphans.confirmWord");
    },
    typedOk() {
      return this.typed.trim().toLowerCase() === this.confirmWord.toLowerCase() && this.selected.length > 0;
    },
    busy() {
      return this.following || this.runs.some((run) => run.status === "running" && run.storage_id === this.storageId);
    },
  },
  watch: {
    "$store.state.refresh.tick"() {
      this.loadRuns();
    },
  },
  methods: {
    detail(error) {
      const detail = error?.response?.data?.detail;
      if (detail && typeof detail === "object") return detail.status ?? detail[0]?.msg ?? JSON.stringify(detail);
      return detail ?? String(error);
    },
    notify(title, error) {
      console.error(error);
      this.$vaToast.init({ title, message: this.detail(error), color: "danger" });
    },
    sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleString() : "";
    },
    humanSize(bytes) {
      let value = Number(bytes) || 0;
      const units = ["B", "KiB", "MiB", "GiB", "TiB"];
      let i = 0;
      while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i += 1;
      }
      return `${i === 0 ? value : value.toFixed(value >= 100 ? 0 : 1)} ${units[i]}`;
    },
    // A value the page does not know is shown as received.
    translated(prefix, value) {
      const key = `pages.cleanup.history.${prefix}.${value}`;
      return this.$te(key) ? this.$t(key) : value;
    },
    statusText(status) {
      return this.translated("status", status);
    },
    kindText(kind) {
      return this.translated("kind", kind);
    },
    triggerText(trigger) {
      return this.translated("trigger", trigger);
    },
    summaryText(run) {
      const s = run.summary;
      if (!s) return this.$t("pages.cleanup.history.noSummary");
      let text = this.$t("pages.cleanup.history.summary", {
        archives: this.$tc("pages.cleanup.history.archives", s.archives_deleted ?? 0),
        repositories: this.$tc("pages.cleanup.history.repositories", s.repositories ?? 0),
        size: this.humanSize(s.freed_bytes),
      });
      if (s.errors) text += ` (${this.$tc("pages.cleanup.history.summaryErrors", s.errors)})`;
      return text;
    },
    // Reads a cron back into the builder fields when it is a simple one.
    applyCron(cron) {
      const value = (cron || "").trim();
      this.rawCron = value || "0 4 * * 0";
      const m = /^(\d{1,2}) (\d{1,2}) \* \* (\*|[0-7])$/.exec(value);
      if (m && Number(m[1]) < 60 && Number(m[2]) < 24) {
        this.time = `${m[2].padStart(2, "0")}:${m[1].padStart(2, "0")}`;
        this.freqKind = m[3] === "*" ? "day" : "week";
        this.weekday = m[3] === "*" ? 0 : Number(m[3]) % 7;
        this.rawMode = false;
      } else {
        this.rawMode = true;
      }
    },
    toggleRaw(value) {
      if (value) {
        this.rawCron = this.cron || this.rawCron;
        this.rawMode = true;
      } else {
        this.applyCron(this.rawCron);
        // A cron the builder cannot express stays in raw mode.
      }
    },
    applyStorage() {
      const s = this.storage;
      if (!s) return;
      this.form = { keep_days: s.keep_days, after_backup: !!s.after_backup, scheduled: !!s.scheduled };
      this.hookId = s.hook_id || null;
      this.applyCron(s.schedule);
    },
    onStorageChange() {
      this.applyStorage();
      this.scanResult = null;
      this.scanFailure = null;
      this.selected = [];
      this.resetSimulation();
    },
    resetSimulation() {
      this.simResult = null;
      this.simFailure = null;
      this.checked = {};
      this.openRepos = [];
    },
    async load() {
      try {
        const { data } = await axios.get(`${this.api}/cleanup/settings`, { headers: this.headers });
        this.storages = data.storages || [];
        if (!this.storage && this.storages.length) this.storageId = this.storages[0].storage_id;
        this.applyStorage();
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableLoad"), error);
      } finally {
        this.loaded = true;
      }
    },
    async save() {
      this.saving = true;
      try {
        const { data } = await axios.put(`${this.api}/cleanup/settings/${this.storageId}`, {
          keep_days: this.form.keep_days,
          after_backup: this.form.after_backup,
          scheduled: this.form.scheduled,
          schedule: this.cronValid ? this.cron : this.storage.schedule,
          hook_id: this.hookId || null,
        }, { headers: this.headers });
        const index = this.storages.findIndex((s) => s.storage_id === this.storageId);
        if (index >= 0 && data && data.storage_id) this.storages.splice(index, 1, data);
        this.applyStorage();
        this.resetSimulation();
        this.$vaToast.init({ message: this.$t("pages.cleanup.saved"), color: "success" });
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableSave"), error);
      } finally {
        this.saving = false;
      }
    },
    async loadRuns() {
      try {
        const { data } = await axios.get(`${this.api}/cleanup/runs`, {
          params: { limit: 50 }, headers: this.headers,
        });
        this.runs = data.items || [];
      } catch (error) {
        console.error(error);
      }
    },
    async openRun(run) {
      try {
        const { data } = await axios.get(`${this.api}/cleanup/runs/${run.id}`, { headers: this.headers });
        this.selectedRun = data;
        this.showRun = true;
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableLog"), error);
      }
    },
    // Follows a run until it ends, then tells how it went.
    async followRun(runId) {
      this.following = true;
      try {
        for (;;) {
          await this.sleep(3000);
          if (this.unmounted) return;
          const { data } = await axios.get(`${this.api}/cleanup/runs/${runId}`, { headers: this.headers });
          if (data.status !== "running") {
            this.$vaToast.init({
              message: this.$t(data.status === "success" ? "pages.cleanup.run.finished" : "pages.cleanup.run.failed"),
              color: data.status === "success" ? "success" : "danger",
            });
            return;
          }
        }
      } catch (error) {
        console.error(error);
      } finally {
        this.following = false;
        if (!this.unmounted) this.loadRuns();
      }
    },
    async runNow() {
      try {
        const { data } = await axios.post(`${this.api}/cleanup/run`, { storage_id: this.storageId },
          { headers: this.headers });
        this.$vaToast.init({ message: this.$t("pages.cleanup.run.started"), color: "success" });
        this.loadRuns();
        this.followRun(data.run_id);
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableRun"), error);
      }
    },
    async scan() {
      this.scanning = true;
      this.scanResult = null;
      this.scanFailure = null;
      this.selected = [];
      // The storage chosen when the search starts: the answer of another one is not shown.
      const storageId = this.storageId;
      try {
        const { data } = await axios.post(`${this.api}/cleanup/orphans/scan`, { storage_id: this.storageId },
          { headers: this.headers });
        for (;;) {
          await this.sleep(2000);
          if (this.unmounted) return;
          const { data: status } = await axios.get(`${this.$store.state.endpoint.api}${data.Location}`,
            { headers: this.headers });
          if (storageId !== this.storageId) return;
          if (status.state === "SUCCESS") {
            this.scanResult = status.info;
            return;
          }
          if (status.state === "FAILURE") {
            this.scanFailure = typeof status.status === "string" ? status.status : JSON.stringify(status.status ?? status.info ?? "");
            return;
          }
        }
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableScan"), error);
      } finally {
        this.scanning = false;
      }
    },
    async simulate() {
      this.simulating = true;
      this.resetSimulation();
      // The storage chosen when the simulation starts: the answer of another one is not shown.
      const storageId = this.storageId;
      try {
        const { data } = await axios.post(`${this.api}/cleanup/simulate`, { storage_id: this.storageId },
          { headers: this.headers });
        for (;;) {
          await this.sleep(2000);
          if (this.unmounted) return;
          const { data: status } = await axios.get(`${this.$store.state.endpoint.api}${data.Location}`,
            { headers: this.headers });
          if (storageId !== this.storageId) return;
          if (status.state === "SUCCESS") {
            this.simResult = status.info;
            this.selectAllSimulated();
            return;
          }
          if (status.state === "FAILURE") {
            this.simFailure = typeof status.status === "string" ? status.status : JSON.stringify(status.status ?? status.info ?? "");
            return;
          }
        }
      } catch (error) {
        this.notify(this.$t("pages.cleanup.simulation.unable"), error);
      } finally {
        this.simulating = false;
      }
    },
    // A backup is told by its repository and its name.
    key(repository, name) {
      return `${repository}\u0001${name}`;
    },
    isChecked(repository, name) {
      return !!this.checked[this.key(repository, name)];
    },
    checkedIn(repo) {
      return repo.delete.filter((item) => this.isChecked(repo.name, item.name)).length;
    },
    repoAllChecked(repo) {
      return repo.delete.length > 0 && this.checkedIn(repo) === repo.delete.length;
    },
    setChecked(repository, names, value) {
      const next = { ...this.checked };
      names.forEach((name) => {
        if (value) next[this.key(repository, name)] = true;
        else delete next[this.key(repository, name)];
      });
      this.checked = next;
    },
    toggleRepo(repo, value) {
      this.setChecked(repo.name, repo.delete.map((item) => item.name), value);
    },
    toggleArchive(repository, name, value) {
      this.setChecked(repository, [name], value);
    },
    selectAllSimulated() {
      const next = {};
      this.simRepositories.forEach((repo) => repo.delete.forEach((item) => { next[this.key(repo.name, item.name)] = true; }));
      this.checked = next;
    },
    toggleOpen(name) {
      this.openRepos = this.openRepos.includes(name) ? this.openRepos.filter((n) => n !== name) : [...this.openRepos, name];
    },
    openSimDelete() {
      this.typed = "";
      this.showSimDelete = true;
    },
    async deleteSimulated() {
      this.showSimDelete = false;
      const backups = {};
      this.simRepositories.forEach((repo) => {
        const names = repo.delete.filter((item) => this.isChecked(repo.name, item.name)).map((item) => item.name);
        if (names.length) backups[repo.name] = names;
      });
      try {
        const { data } = await axios.post(`${this.api}/cleanup/selection/delete`, {
          storage_id: this.storageId, backups,
        }, { headers: this.headers });
        this.$vaToast.init({ message: this.$t("pages.cleanup.simulation.started"), color: "success" });
        // What was deleted leaves the list.
        this.resetSimulation();
        this.loadRuns();
        this.followRun(data.run_id);
      } catch (error) {
        this.notify(this.$t("pages.cleanup.simulation.unableDelete"), error);
      }
    },
    toggle(name) {
      this.selected = this.selected.includes(name)
        ? this.selected.filter((n) => n !== name)
        : [...this.selected, name];
    },
    selectAll() {
      this.selected = this.orphans.map((o) => o.name);
    },
    openDelete() {
      this.typed = "";
      this.showDelete = true;
    },
    async deleteOrphans() {
      this.showDelete = false;
      const names = [...this.selected];
      try {
        const { data } = await axios.post(`${this.api}/cleanup/orphans/delete`, {
          storage_id: this.storageId, repositories: names,
        }, { headers: this.headers });
        this.$vaToast.init({ message: this.$t("pages.cleanup.orphans.started"), color: "success" });
        // The deleted repositories leave the list.
        if (this.scanResult) {
          this.scanResult = { ...this.scanResult, orphans: this.orphans.filter((o) => !names.includes(o.name)) };
        }
        this.selected = [];
        this.loadRuns();
        this.followRun(data.run_id);
      } catch (error) {
        this.notify(this.$t("pages.cleanup.unableDelete"), error);
      }
    },
  },
  mounted() {
    if (!this.$store.state.resources.externalHookList.length) this.$store.dispatch("requestExternalHook");
    this.load();
    this.loadRuns();
    // While a cleaning is running, its line follows it.
    this.runsTimer = setInterval(() => {
      if (this.runs.some((run) => run.status === "running")) this.loadRuns();
    }, 5000);
  },
  beforeUnmount() {
    this.unmounted = true;
    clearInterval(this.runsTimer);
  },
});
</script>

<style scoped>
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

.unit {
  color: var(--va-gray);
}

.selection {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sim-repo {
  border: 1px solid var(--va-background-border, #dde);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
}

.sim-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sim-list {
  margin: 0.5rem 0 0 1.5rem;
  list-style: none;
  max-height: 16rem;
  overflow: auto;
}

.warnings,
.names {
  margin: 0.5rem 0 0 1.25rem;
  list-style: disc;
}

.history-header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
}

.run-log {
  max-height: 20rem;
  overflow: auto;
  background: var(--va-background);
  padding: 0.75rem;
  font-size: 0.85rem;
  white-space: pre-wrap;
}
</style>
