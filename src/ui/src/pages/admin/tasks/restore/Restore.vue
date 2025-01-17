<template>
  <div class="row">
    <div class="flex lg12 xl10">
      <va-card class="mb-4">
        <va-card-title>
          <h1>Restore</h1>
          <div class="mr-0 text-right">
            <va-button color="info"
              @click="this.$router.push({ path: '/admin/tasks/kickstart', query: { task: 'restore' } })">
              Start restore task
            </va-button>
          </div>
        </va-card-title>
        <va-card-content>
          <va-chip v-show="successTaskNumber" color="success" class="mr-4 mb-2">
            <va-icon name="task_alt" />
            <span style="font-style: bold; padding-left: 5px;">
              {{ successTaskNumber }}
            </span>
          </va-chip>
          <va-chip v-show="failureTaskNumber" color="danger" class="mr-4 mb-2">
            <va-icon name="error" />
            <span style="font-style: bold; padding-left: 5px;">
              {{ failureTaskNumber }}
            </span>
          </va-chip>
          <va-chip v-show="pendingTaskNumber" color="info" class="mr-4 mb-2">
            <va-icon name="loop" spin="counter-clockwise" />
            <span style="font-style: bold; padding-left: 5px;">
              {{ pendingTaskNumber }}
            </span>
          </va-chip>
          <backup-table :data="tableData" :columns="columns" />
          <div v-if="!$store.state.isbackupTaskTableReady" class="flex-center ma-3">
            <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
          </div>
        </va-card-content>
      </va-card>
    </div>
    <div class="flex lg12 xl2">
      <va-card class="d-flex">
        <va-card-title>
          Filter by date
        </va-card-title>
        <va-card-content class="row">
          <va-date-picker v-model="selectedDate" :highlight-today="false"
            :allowedDays="(date) => new Date(date) < new Date()" first-weekday="Monday" mode="single" />
        </va-card-content>
      </va-card>
    </div>
  </div>
  <va-modal v-model="logModal" size="large" :hide-default-actions="true">
    <template #header>
      <h2>
        <va-icon name="bug_report" color="info" />
        Task logs
      </h2>
    </template>
    <hr>
    <div class="consoleStyle">
      {{ taskInfo.traceback }}
    </div>
    <template #footer>
      <va-button @click="logModal = !logModal">
        Close
      </va-button>
    </template>
  </va-modal>
</template>

<script>
import BackupTable from "@/components/backup-table/BackupTable.vue"
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

export default defineComponent({
  name: 'BackupsTable',
  components: { ...spinners, BackupTable },
  data() {
    return {
      columns: [
        { key: 'target', sortable: true },
        { key: 'started', sortable: true },
        { key: 'runtime', sortable: true },
        { key: 'state', sortable: true },
        { key: 'actions' },
      ],
      selectedDate: new Date(),
      logModal: false,
      taskInfo: { traceback: null },

      positionVertical: 'bottom',
      positionHorizontal: 'right',

      verticalOffset: 5,
      horizontalOffset: 5,
      visibilityHeight: 1,
      scrollSpeed: 50
    }
  },
  computed: {
    filteredTaskList() {
      if (this.selectedDate) {
        return Object.values(this.$store.state.restoreTaskList).filter(x => (this.dateSelector(x.received)))
      } else {
        return Object.values(this.$store.state.restoreTaskList)
      }
    },
    successTaskNumber() {
      return this.filteredTaskList.filter(x => x.state === 'SUCCESS').length
    },
    failureTaskNumber() {
      return this.filteredTaskList.filter(x => x.state === 'FAILURE').length
    },
    pendingTaskNumber() {
      return this.filteredTaskList.filter(x => x.state === 'RECEIVED').length
    },
    tableData() {
      return this.filteredTaskList.map(x => {
        const taskArgs = this.parseArgs(x)
        return {
          uuid: x.uuid,
          name: x.name.replaceAll('_', ' '),
          target: taskArgs?.name ?? "",
          targetPage: "virtualmachines",
          targetUuid: taskArgs?.uuid,
          started: x.started,
          ipAddress: x.ip_address,
          runtime: x.runtime,
          state: x.state,
        }
      })
    }
  },
  mounted () {
    this.$store.dispatch("requestRestoreTask", { token: this.$keycloak.token })
  },
  methods: {
    dateSelector(dateToCheck) {
      const convertedDateCheck = new Date(dateToCheck * 1000)
      if (
        this.selectedDate.getFullYear() === convertedDateCheck.getFullYear() &&
        this.selectedDate.getMonth() === convertedDateCheck.getMonth() &&
        this.selectedDate.getDate() === convertedDateCheck.getDate()
      ) {
        return true
      } else {
        return false
      }
    },
    getPool(id) {
      return this.$store.state.resources.poolList.filter((item) => {
        return item.id == id
      })
    },
    parseArgs(x) {
      try {
        return JSON.parse(x.args);
      } catch (error) {
        console.error(error);
      }
    }
  }
})
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}

.center-div {
  margin: 0 auto;
  width: 100px;
}

.consoleStyle {
  padding: 1% 1% 1% 1%;
  background: black;
  color: silver;
  font-size: 1em;
  border-radius: 5px;
  max-height: 5%;
  width: auto;
}
</style>
