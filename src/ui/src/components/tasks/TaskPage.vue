<template>
  <div class="row">
    <div class="flex lg12 xl10">
      <va-card class="mb-4">
        <va-card-title>
          <h1>{{ title }}</h1>
          <div class="mr-0 text-right">
            <va-button v-if="$store.getters.canEdit" color="info"
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
          <va-chip v-show="skippedTaskNumber" color="warning" class="mr-4 mb-2 skipped-count"
            :title="$t('pages.tasks.common.state.SKIPPED')">
            <va-icon name="pause_circle" />
            <span style="font-style: bold; padding-left: 5px;">
              {{ skippedTaskNumber }}
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
          <va-input v-model="search" class="mb-3 task-search" clearable
            :placeholder="$t('pages.tasks.common.search')" :aria-label="$t('pages.tasks.common.search')">
            <template #prependInner>
              <va-icon name="search" size="small" />
            </template>
          </va-input>
          <task-table :data="visibleTaskList" :columns="columns" />
          <div v-if="!$store.state.isbackupTaskTableReady" class="flex-center ma-3">
            <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
          </div>
        </va-card-content>
      </va-card>
    </div>
    <div class="flex lg12 xl2">
      <va-card class="d-flex">
        <va-card-title>
          {{ $t('pages.tasks.common.filterByDate') }}
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
    let selectedDate = new Date();
    const date = this.$route.query.date
    try {
      // Note that the calendar view is not moving to the selected date…
      selectedDate = new Date(date ?? (() => { throw "date is null" })())
    } catch (_) { }

    return {
      selectedDate,
      search: "",
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
    columns() {
      return [
        { key: 'target', label: this.$t('pages.tasks.common.columns.target'), sortable: true },
        { key: 'started', label: this.$t('pages.tasks.common.columns.started'), sortable: true },
        { key: 'runtime', label: this.$t('pages.tasks.common.columns.runtime'), sortable: true },
        { key: 'state', label: this.$t('pages.tasks.common.columns.state'), sortable: true },
        { key: 'actions', label: this.$t('pages.tasks.common.columns.actions') },
      ]
    },
    taskList() {
      return this.getTaskList((task) => this.isOnSelectedDay(task.received))
    },
    // The search looks in the name of the machine, the state (as shown and as sent), the time and the date.
    visibleTaskList() {
      const words = (this.search || "").toLowerCase().split(/\s+/).filter(Boolean)
      if (!words.length) {
        return this.taskList
      }
      return this.taskList.filter((task) => {
        const text = [
          task.target,
          task.state,
          this.$te(`pages.tasks.common.state.${task.state}`) ? this.$t(`pages.tasks.common.state.${task.state}`) : "",
          task.started ? new Date(task.started * 1000).toLocaleString() : "",
        ].join(" ").toLowerCase()
        return words.every((word) => text.includes(word))
      })
    },
    successTaskNumber() {
      return this.taskList.filter(({ state }) => state === 'SUCCESS').length
    },
    skippedTaskNumber() {
      return this.taskList.filter(({ state }) => state === 'SKIPPED').length
    },
    failureTaskNumber() {
      return this.taskList.filter(({ state }) => state === 'FAILURE').length
    },
    pendingTaskNumber() {
      return this.taskList.filter(({ state }) => ['RECEIVED', 'STARTED'].includes(state)).length
    },
  },
  methods: {
    // TODO Move to computed method ? Or dependencies are tracked ?
    isOnSelectedDay(dateToCheck) {
      const convertedDateCheck = new Date(dateToCheck * 1000)
      return (
        this.selectedDate.getFullYear() === convertedDateCheck.getFullYear() &&
        this.selectedDate.getMonth() === convertedDateCheck.getMonth() &&
        this.selectedDate.getDate() === convertedDateCheck.getDate()
      )
    }
  },
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
