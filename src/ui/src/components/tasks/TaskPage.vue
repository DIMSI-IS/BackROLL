<template>
  <div class="row">
    <!--list of backup part-->
    <div class="flex lg12 xl10">
      <va-card class="mb-4">
        <va-card-title>
          <h1>{{ title }}</h1>
          <div class="mr-0 text-right">
            <va-button
              color="info"
              @click="
                this.$router.push({
                  path: '/admin/tasks/kickstart',
                  query: { task: kickstartTask },
                })
              "
            >
              {{ kickstartTitle }}
            </va-button>
          </div>
        </va-card-title>
        <va-card-content>
          <va-chip v-show="successTaskNumber" color="success" class="mr-4 mb-2">
            <va-icon name="task_alt" />
            <span style="font-style: bold; padding-left: 5px">
              {{ successTaskNumber }}
            </span>
          </va-chip>
          <va-chip v-show="failureTaskNumber" color="danger" class="mr-4 mb-2">
            <va-icon name="error" />
            <span style="font-style: bold; padding-left: 5px">
              {{ failureTaskNumber }}
            </span>
          </va-chip>
          <va-chip v-show="pendingTaskNumber" color="info" class="mr-4 mb-2">
            <va-icon name="loop" spin="counter-clockwise" />
            <span style="font-style: bold; padding-left: 5px">
              {{ pendingTaskNumber }}
            </span>
          </va-chip>
          <task-table :data="taskList" :columns="columns" />
          <div
            v-if="!$store.state.isbackupTaskTableReady"
            class="flex-center ma-3"
          >
            <spring-spinner
              :animation-duration="2000"
              :size="30"
              color="#2c82e0"
            />
          </div>
        </va-card-content>
      </va-card>
    </div>
    <!--end of list of backup part-->

    <!--calendar part-->
    <div class="flex lg12 xl2">
      <va-card class="d-flex">
        <va-card-title
          class="header"
          style="
            justify-content: space-between;
            align-items: center;
            max-width: 260px;
          "
        >
          <span>Filter by date</span>
          <!--implementation of today button in the calendar-->
          <va-button color="primary" @click="setToday" class="today-button">
            <div
              style="
                display: flex;
                flex-direction: column;
                align-items: center;
                line-height: 1;
                margin-top: -4px;
              "
            >
              <small style="font-size: 0.6em; margin-bottom: -1px">TODAY</small>
              <span style="font-size: 0.85em">{{ todayDayNumber }}</span>
            </div>
          </va-button>
          <!--end of today button-->
        </va-card-title>
        <va-card-content class="row">
          <va-date-picker
            v-model="selectedDate"
            :highlight-today="false"
            mode="single"
            :allowedDays="(date) => new Date(date) < new Date()"
            first-weekday="Monday"
            :key="pickerKey"
          >
            <template #day="{ date }">
              <div class="cell" :class="getBackupClass(date)">
                {{ date.getDate() }}
              </div>
            </template>
          </va-date-picker>
        </va-card-content>
      </va-card>
    </div>
  </div>
</template>

<script>
import TaskTable from "@/components/tasks/TaskTable.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";

export default defineComponent({
  name: "task-page",
  components: { ...spinners, TaskTable },
  props: {
    title: String,
    kickstartTitle: String,
    kickstartTask: String,
    getTaskList: Function,
  },
  data() {
    let selectedDate = new Date();
    const date = this.$route.query.date;
    try {
      // Note that the calendar view is not moving to the selected date…
      selectedDate = new Date(
        date ??
          (() => {
            throw "date is null";
          })()
      );
    } catch (_) {}

    return {
      slectedDate: new Date(),
      pickerKey: 0,
      columns: [
        { key: "target", sortable: true },
        { key: "started", sortable: true },
        { key: "runtime", sortable: true },
        { key: "state", sortable: true },
        { key: "actions" },
      ],
      selectedDate,
      logModal: false,
      taskInfo: { traceback: null },

      positionVertical: "bottom",
      positionHorizontal: "right",

      verticalOffset: 5,
      horizontalOffset: 5,
      visibilityHeight: 1,
      scrollSpeed: 50,

      backupData: {
        "2025-07-01": 0,
        "2025-07-02": 1,
        "2025-07-03": 2,
        "2025-07-04": 3,
        "2025-07-05": 0,
        "2025-07-06": 4,
        "2025-07-07": 5,
        // Ajoutez d'autres dates
      },
    };
  },
  computed: {
    taskList() {
      return this.getTaskList((task) => this.isOnSelectedDay(task.received));
    },
    successTaskNumber() {
      return this.taskList.filter(({ state }) => state === "SUCCESS").length;
    },
    failureTaskNumber() {
      return this.taskList.filter(({ state }) => state === "FAILURE").length;
    },
    pendingTaskNumber() {
      return this.taskList.filter(({ state }) =>
        ["RECEIVED", "STARTED"].includes(state)
      ).length;
    },
    todayDayNumber() {
      return new Date().getDate();
    },
  },
  methods: {
    // getBackupClass(date) {
    //   const backupCount =
    //     this.backupData[
    //       `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
    //         2,
    //         "0"
    //       )}-${String(date.getDate()).padStart(2, "0")}`
    //     ] || 0;
    //   if (backupCount > 4) return "red-backup";
    //   if (backupCount > 2) return "orange-backup";
    //   if (backupCount >= 1) return "green-backup";
    //   return;
    // },
    getBackupClass(date) {
      const tasks = this.getTaskList((task) =>
        this.isOnSelectedDayFrom(task.received, date)
      );

      if (tasks.length === 0) return "";
      const allSuccess = tasks.every((task) => task.state === "SUCCESS");
      const allFailure = tasks.every((task) => task.state === "FAILURE");

      if (allSuccess) return "green-backup";
      if (allFailure) return "red-backup";
      return "orange-backup";
    },
    isOnSelectedDayFrom(timestamp, dateRef) {
      const taskDate = new Date(timestamp * 1000);
      return (
        taskDate.getFullYear() === dateRef.getFullYear() &&
        taskDate.getMonth() === dateRef.getMonth() &&
        taskDate.getDate() === dateRef.getDate()
      );
    },
    // TODO Move to computed method ? Or dependencies are tracked ?
    isOnSelectedDay(dateToCheck) {
      const convertedDateCheck = new Date(dateToCheck * 1000);
      return (
        this.selectedDate.getFullYear() === convertedDateCheck.getFullYear() &&
        this.selectedDate.getMonth() === convertedDateCheck.getMonth() &&
        this.selectedDate.getDate() === convertedDateCheck.getDate()
      );
    },
    setToday() {
      this.selectedDate = new Date();
      this.pickerKey++;
    },
  },
});
</script>

<!-- TODO Is CSS used ? -->
<style scoped>
.cell {
  width: var(--va-date-picker-cell-size);
  height: var(--va-date-picker-cell-size);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--va-date-picker-cell-radius);
}
.highlight {
  background-color: rgba(0, 123, 255, 0.4);
}
.green-backup {
  background-color: rgb(19, 216, 19, 0.5);
}
.orange-backup {
  background-color: rgba(245, 140, 3, 0.5);
}
.red-backup {
  background-color: rgba(255, 0, 0, 0.7);
}

.text-right {
  text-align: right;
  width: 100%;
}

.center-div {
  margin: 0 auto;
  width: 100px;
}
.today-button {
  position: relative;
  width: 36px; /* var(--va-date-picker-cell-size); */
  height: 36px; /* var(--va-date-picker-cell-size); */
  box-sizing: border-box;
  background: transparent !important;
  border-radius: var(--va-date-picker-cell-radius, 4px);
  border: 2px solid var(--va-date-picker-focused-border-color, #2c82e0) !important;
  color: black !important;
  padding: 0;
  min-width: 0;
  line-height: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: border 0.2s ease;

  clip-path: polygon(
    0 0,
    100% 0,
    100% calc(100% - 10px),
    calc(100% - 10px) 100%,
    0 100%
  );
}

.today-button::after {
  content: "";
  position: absolute;
  bottom: 10px;
  right: -2px;
  width: 10px;
  height: 10px;
  background: white;
  border-left: 12px solid transparent;
  border-top: 12px solid #2c82e0;
  border-top-right-radius: 3px;
  transform: rotate(-90deg);
  transform-origin: bottom right;
  box-sizing: border-box;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
