<template>
  <div class="row">
    <div class="flex lg12 xl10">
      <va-card class="mb-4">
        <va-card-title>
          <h1>{{ title }}</h1>
          <div class="mr-0 text-right">
            <va-button color="info"
              @click="this.$router.push({ path: '/admin/tasks/kickstart', query: { task: kickstartTask } })">
              {{ kickstartTitle }}
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
          <task-table :data="taskList" :columns="columns" />
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
</template>

<script>
import TaskTable from "@/components/tasks/TaskTable.vue"
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

export default defineComponent({
  name: 'task-page',
  components: { ...spinners, TaskTable },
  props: {
    title: String,
    kickstartTitle: String,
    kickstartTask: String,
    getTaskList: Function,
  },
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
      scrollSpeed: 50,
    }
  },
  computed: {
    taskList() {
      return this.getTaskList((task) => this.isOnSelectedDay(task.received))
    },
    successTaskNumber() {
      return this.taskList.filter(({ state }) => state === 'SUCCESS').length
    },
    failureTaskNumber() {
      return this.taskList.filter(({ state }) => state === 'FAILURE').length
    },
    pendingTaskNumber() {
      return this.taskList.filter(({ state }) => ['RECEIVED', 'STARTED'].includes(state)).length
    },
  },
  methods: {
    isOnSelectedDay(dateToCheck) {
      const convertedDateCheck = new Date(dateToCheck * 1000)
      return (
        this.selectedDate.getFullYear() === convertedDateCheck.getFullYear() &&
        this.selectedDate.getMonth() === convertedDateCheck.getMonth() &&
        this.selectedDate.getDate() === convertedDateCheck.getDate()
      )
    }
  }
})
</script>
<!-- TODO Is CSS used ? -->
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}

.center-div {
  margin: 0 auto;
  width: 100px;
}
</style>
