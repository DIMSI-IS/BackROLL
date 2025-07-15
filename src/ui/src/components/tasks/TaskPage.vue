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

          <va-input
            v-model="search"
            placeholder="Search a VM's task..."
            class="mb-3"
            prepend-inner-icon="search"
          />

          <va-select
            v-model="tasksPerVm"
            :options="tasksPerVmOptions"
            value-by="value"
            class="mb-3"
            style="max-width: 220px;"
            placeholder="Number of tasks by VM"
          />


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
    let selectedDate = new Date();
    const date = this.$route.query.date
    try {
      // Note that the calendar view is not moving to the selected date…
      selectedDate = new Date(date ?? (() => { throw "date is null" })())
    } catch (_) { }

    return {
      columns: [
        { key: 'target', sortable: true },
        { key: 'started', sortable: true },
        { key: 'runtime', sortable: true },
        { key: 'state', sortable: true },
        { key: 'actions' },
      ],
      selectedDate,
      logModal: false,
      taskInfo: { traceback: null },

      positionVertical: 'bottom',
      positionHorizontal: 'right',

      verticalOffset: 5,
      horizontalOffset: 5,
      visibilityHeight: 1,
      scrollSpeed: 50,
      search : '',
      tasksPerVm: 0,
      tasksPerVmOptions: [
        { text: '1 (dernière tâche)', value: 1 },
        { text: '2 dernières', value: 2 },
        { text: '3 dernières', value: 3 },
        { text: 'Toutes', value: 0 },
      ],
    }
    
  },
  computed: {
    taskList() {
      let list = this.getTaskList((task) => this.isOnSelectedDay(task.received));
      console.log("Filtered task list:", list); // <= ajoute ceci
      console.log("this.tasksPerVm:", this.tasksPerVm); // <= ajoute ceci*
      
      if (this.search){
        const searchLower = this.search.toLowerCase();
        list = list.filter(task =>
        (task.target && task.target.toLowerCase().includes(searchLower)) ||
        (task.args && task.args.name && task.args.name.toLowerCase().includes(searchLower))
      );
    }
      
      // Group by VM (by target or args.name)
      if (this.tasksPerVm === 0) {
        // 0 = all tasks
        return list;
      }
      const grouped = {};
      for (const task of list) {
        const vmKey = task.target || (task.args && task.args.name);
        if (!vmKey) continue;
        if (!grouped[vmKey]) grouped[vmKey] = [];
        grouped[vmKey].push(task);
      }
      // Sort each group by descending date
      Object.values(grouped).forEach(tasks =>
        tasks.sort((a, b) => new Date(b.started) - new Date(a.started))
      );
      // Take N tasks per VM
      return Object.values(grouped).flatMap(tasks => tasks.slice(0, this.tasksPerVm));
    },

    // taskList() {
    //   return this.getTaskList((task) => this.isOnSelectedDay(task.received))
    // },
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
