<template>
  <div class="activity">
    <div class="row row-equal">
      <div class="flex xs12 sm6" v-for="tile in tiles" :key="tile.label">
        <va-card class="clickable" :to="tile.route">
          <va-card-content>
            <div class="tile">
              <va-icon :name="tile.icon" :size="40" :color="tile.color" />
              <div>
                <p class="display-4 mb-0" :style="{ color: tile.alert ? 'var(--va-danger)' : null }">
                  {{ tile.value }}
                </p>
                <p class="mb-0">{{ tile.label }}</p>
                <p class="caption mb-0" v-if="tile.detail">{{ tile.detail }}</p>
              </div>
            </div>
          </va-card-content>
        </va-card>
      </div>
    </div>

  </div>
</template>

<script>
const BACKUP_TASKS = ["Single_VM_Backup", "backup_subtask"];

export default {
  name: "DashboardActivity",
  computed: {
    // `started` is in seconds.
    tasks() {
      return Object.values(this.$store.state.backupTaskList)
        .filter((task) => BACKUP_TASKS.includes(task.name));
    },
    last24Hours() {
      const limit = Date.now() / 1000 - 24 * 3600;
      return this.tasks.filter((task) => task.started && task.started > limit);
    },
    running() {
      return this.tasks.filter((task) => task.state === "STARTED").length;
    },
    waiting() {
      return this.tasks.filter((task) => ["RECEIVED", "PENDING", "RETRY"].includes(task.state)).length;
    },
    succeeded() {
      return this.last24Hours.filter((task) => task.state === "SUCCESS").length;
    },
    failed() {
      return this.last24Hours.filter((task) => task.state === "FAILURE");
    },
    lastSuccess() {
      const times = this.tasks
        .filter((task) => task.state === "SUCCESS" && task.started)
        .map((task) => task.started);
      return times.length ? new Date(Math.max(...times) * 1000).toLocaleString() : this.$t('pages.dashboard.none');
    },
    policies() {
      return this.$store.state.resources.policyList;
    },
    tiles() {
      return [
        {
          label: this.$t('pages.dashboard.backupsRunning'), value: this.running, icon: "sync", color: "primary",
          detail: this.waiting ? this.$t('pages.dashboard.waitingForPlace', { count: this.waiting }) : null,
          route: "/admin/tasks/backup",
        },
        {
          label: this.$t('pages.dashboard.succeeded24'), value: this.succeeded, icon: "check_circle", color: "success",
          detail: this.$t('pages.dashboard.lastSuccess', { when: this.lastSuccess }), route: "/admin/tasks/backup",
        },
        {
          label: this.$t('pages.dashboard.failed24'), value: this.failed.length, icon: "error",
          color: this.failed.length ? "danger" : "secondary", alert: this.failed.length > 0,
          route: "/admin/tasks/backup",
        },
        {
          label: this.$t('pages.dashboard.policiesEnabled'),
          value: `${this.policies.filter((policy) => policy.enabled).length} / ${this.policies.length}`,
          icon: "schedule", color: "info", route: "/admin/configuration/policies",
        },
      ];
    },
  },
};
</script>

<style scoped>
.tile {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.clickable {
  cursor: pointer;
}

.activity .row {
  margin-bottom: 0.75rem;
}
</style>
