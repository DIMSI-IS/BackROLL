<template>
  <div class="row">
    <div class="flex xs12 md6">
      <va-card stripe :stripe-color="atRisk.length || neverBacked.length ? 'danger' : 'success'">
        <va-card-title>
          {{ $t('pages.dashboard.protection') }}
          <va-select v-model="ageChoice" :options="ageChoices" text-by="text" value-by="value"
            :clearable="false" class="age" :title="$t('pages.dashboard.riskTitle')" />
        </va-card-title>
        <va-card-content>
          <div v-if="error" class="mb-2">
            <va-icon name="warning" color="warning" /> {{ error }}
          </div>
          <div class="counts">
            <div><p class="display-4 mb-0" style="color: var(--va-success)">{{ protectedMachines.length }}</p>
              <p class="mb-0">{{ $t('pages.dashboard.protectedCount') }}</p></div>
            <div><p class="display-4 mb-0" :style="{ color: atRisk.length ? 'var(--va-danger)' : null }">{{ atRisk.length }}</p>
              <p class="mb-0">{{ $t('pages.dashboard.atRisk') }}</p></div>
            <div><p class="display-4 mb-0" :style="{ color: neverBacked.length ? 'var(--va-danger)' : null }">{{ neverBacked.length }}</p>
              <p class="mb-0">{{ $t('pages.dashboard.neverBackedUp') }}</p></div>
            <div v-if="offMachines.length" class="stopped" role="button" tabindex="0" :aria-expanded="String(showOff)"
              :title="$t('pages.dashboard.notRunningTitle')" @click="showOff = !showOff" @keyup.enter="showOff = !showOff">
              <p class="display-4 mb-0">{{ offMachines.length }}</p>
              <p class="mb-0">{{ $t('pages.dashboard.notRunningCount') }}
                <va-icon :name="showOff ? 'expand_less' : 'expand_more'" size="small" /></p>
            </div>
          </div>
          <machine-list v-if="problems.length" class="problem-list" :machines="problems" />
          <p v-else-if="loaded" class="mt-3 mb-0">
            <va-icon name="check_circle" color="success" /> {{ $t('pages.dashboard.everyMachineRecent') }}
          </p>
          <machine-list v-if="showOff && offMachines.length" class="stopped-list" :machines="offMachines" />
        </va-card-content>
      </va-card>
    </div>

    <div class="flex xs12 md6">
      <va-card stripe stripe-color="info">
        <va-card-title>{{ $t('pages.dashboard.nextScheduled') }}</va-card-title>
        <va-card-content>
          <p v-if="nextRuns.length === 0" class="mb-0">{{ $t('pages.dashboard.noPolicyEnabled') }}</p>
          <va-list v-else>
            <va-list-item v-for="run in nextRuns" :key="run.id" :to="`/admin/configuration/policy/${run.id}`">
              <va-list-item-section>
                <va-list-item-label>{{ run.name }}</va-list-item-label>
                <va-list-item-label caption>{{ run.when }}</va-list-item-label>
              </va-list-item-section>
              <va-list-item-section icon>
                <va-chip size="small" square outline>{{ $t('pages.dashboard.inDuration', { duration: run.in }) }}</va-chip>
              </va-list-item-section>
            </va-list-item>
          </va-list>
        </va-card-content>
      </va-card>
    </div>

  </div>
</template>

<script>
import axios from "axios";
import parser from "cron-parser";

import MachineList from "./MachineList.vue";

const AGE_KEY = "backroll.protection.hours";

function duration(milliseconds, t) {
  const minutes = Math.max(1, Math.round(milliseconds / 60000));
  if (minutes < 60) return t('pages.dashboard.minutes', { count: minutes });
  const hours = Math.round(minutes / 60);
  if (hours < 48) return t('pages.dashboard.hours', { count: hours });
  return t('pages.dashboard.days', { count: Math.round(hours / 24) });
}

export default {
  name: "DashboardProtection",
  components: { MachineList },
  data() {
    let hours = 48;
    try {
      hours = Number(localStorage.getItem(AGE_KEY)) || 48;
    } catch {
      // The default is used.
    }
    return {
      hours,
      repositories: [],
      loaded: false,
      showOff: false,
      error: null,
    };
  },
  computed: {
    ageChoices() {
      return [
        { text: this.$t("pages.dashboard.age24"), value: 24 },
        { text: this.$t("pages.dashboard.age48"), value: 48 },
        { text: this.$t("pages.dashboard.age7d"), value: 168 },
        { text: this.$t("pages.dashboard.age30d"), value: 720 },
      ];
    },
    ageChoice: {
      get() {
        return this.ageChoices.find((choice) => choice.value === this.hours) || this.ageChoices[1];
      },
      set(choice) {
        this.hours = choice && typeof choice === "object" ? choice.value : choice;
        try {
          localStorage.setItem(AGE_KEY, String(this.hours));
        } catch {
          // Kept until the page is closed.
        }
        this.load();
      },
    },
    machines() {
      // A repository is named after its machine.
      const byName = Object.fromEntries(this.repositories.map((repository) => [repository.name, repository]));
      return this.$store.state.resources.vmList.map((vm) => ({ vm, repository: byName[vm.name] }));
    },
    // Only the running machines are backed up: the others are counted apart, so that a machine that is off on
    // purpose does not turn the card red, and a real problem is not lost among them.
    runningMachines() {
      return this.machines.filter(({ vm }) => vm.state === "Running");
    },
    offMachines() {
      const now = Date.now();
      return this.machines
        .filter(({ vm }) => vm.state !== "Running")
        .map(({ vm, repository }) => {
          const last = repository && repository.last_backup ? new Date(repository.last_backup).getTime() : null;
          return {
            uuid: vm.uuid, name: vm.name, state: vm.state, age: last === null ? Infinity : now - last,
            detail: last === null
              ? this.$t('pages.dashboard.noBackupYet')
              : this.$t('pages.dashboard.lastBackupAgo', { duration: duration(now - last, (...args) => this.$t(...args)) }),
          };
        })
        // The ones that were never backed up first, then the oldest backup.
        .sort((a, b) => (a.age === b.age ? 0 : b.age - a.age));
    },
    protectedMachines() {
      return this.runningMachines.filter(({ repository }) => repository && repository.protected);
    },
    atRisk() {
      return this.runningMachines.filter(({ repository }) => repository && !repository.protected && repository.last_backup);
    },
    neverBacked() {
      return this.runningMachines.filter(({ repository }) => !repository || !repository.last_backup);
    },
    problems() {
      const now = Date.now();
      const risky = this.atRisk
        .map(({ vm, repository }) => ({
          uuid: vm.uuid, name: vm.name, age: now - new Date(repository.last_backup).getTime(),
          detail: repository.state === "locked"
            ? this.$t('pages.dashboard.repositoryLocked')
            : this.$t('pages.dashboard.lastBackupAgo', { duration: duration(now - new Date(repository.last_backup).getTime(), (...args) => this.$t(...args)) }),
        }))
        .sort((a, b) => b.age - a.age);
      const never = this.neverBacked.map(({ vm, repository }) => ({
        uuid: vm.uuid, name: vm.name, age: Infinity,
        detail: repository && repository.state !== "ok" ? this.$t('pages.dashboard.repositoryState', { state: repository.state }) : this.$t('pages.dashboard.noBackupYet'),
      }));
      // All of them: the list shows the first ones and a button for the others.
      return [...never, ...risky];
    },
    nextRuns() {
      const now = new Date();
      return this.$store.state.resources.policyList
        .filter((policy) => JSON.parse(policy.enabled))
        .map((policy) => {
          try {
            const next = parser.parseExpression(policy.schedule, { currentDate: now, tz: "Europe/Paris" }).next().toDate();
            return { id: policy.id, name: policy.name, at: next, when: next.toLocaleString(), in: duration(next - now, (...args) => this.$t(...args)) };
          } catch {
            return null;
          }
        })
        .filter(Boolean)
        .sort((a, b) => a.at - b.at);
    },
  },
  watch: {
    "$store.state.refresh.tick"() {
      this.load();
    },
  },
  methods: {
    async load() {
      try {
        const { data } = await axios.get(
          `${this.$store.state.endpoint.api}/api/v1/dashboard/protection`,
          { params: { max_age_hours: this.hours },
            headers: { Authorization: `Bearer ${this.$store.state.token}` } });
        this.repositories = data.repositories;
        this.error = null;
      } catch (error) {
        this.error = this.$t('pages.dashboard.unableReadBackups');
        console.error(error);
      } finally {
        this.loaded = true;
      }
    },
  },
  mounted() {
    this.load();
  },
};
</script>

<style scoped>
.age {
  width: 6.5rem;
}

.stopped {
  cursor: pointer;
}

.stopped .display-4 {
  color: var(--va-secondary);
}

.counts {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}
</style>
