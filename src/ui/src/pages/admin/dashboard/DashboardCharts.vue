<template>
  <div class="row row-equal">
    <div class="flex xs12 xl10">
      <va-card v-if="lineChartData">
        <va-card-title>
          <h1>{{ $t("dashboard.charts.lastFailedBackup") }}</h1>
          <div class="mr-0 text-right">
            <va-button
              size="small"
              color="info"
              @click="this.$router.push('/admin/tasks/backup')"
              :disabled="lineChartData.labels.length < 2"
            >
              {{ $t("dashboard.charts.showInMoreDetail") }}
            </va-button>
          </div>
        </va-card-title>
        <va-card-content>
          <task-table
            :data="tableData"
            :columns="columns"
            :pagination="true"
            :perPage="6"
          />
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
    <div class="flex xs12 md6 xl2">
      <va-card class="d-flex">
        <va-card-title>
          <h1>{{ $t("dashboard.charts.vmRepartition") }}</h1>
          <div class="mr-0 text-right">
            <va-button icon="print" flat class="mr-0" @click="printChart" />
          </div>
        </va-card-title>
        <va-card-content v-if="!$store.state.isvmTableReady">
          <div class="text--center pb-4">
            <div class="flex-center spinner-box">
              <component
                :animation-duration="1500"
                :is="loadingDonutType"
                color="#2c82e0"
                :size="120"
              >
              </component>
            </div>
          </div>
        </va-card-content>
        <va-card-content v-else>
          <va-chart
            class="chart chart--donut"
            :data="configChart"
            type="donut"
          />
        </va-card-content>
      </va-card>
    </div>
  </div>
</template>

<script>
import TaskTable from "@/components/tasks/TaskTable.vue";
import * as spinners from "epic-spinners";
import { getDonutChartData } from "@/data/charts/DonutChartData";
import { getLineChartData } from "@/data/charts/LineChartData";
import VaChart from "@/components/va-charts/VaChart.vue";
import { useGlobalConfig } from "vuestic-ui";
import { defineComponent } from "vue";

export default defineComponent({
  name: "dashboard-charts",
  components: { ...spinners, VaChart, TaskTable },
  data() {
    return {
      lineChartData: null,
      donutChartData: null,
      lineChartFirstMonthIndex: 0,
      columns: [
        { key: "target" },
        { key: "started" },
        { key: "state" },
        { key: "actions" },
      ],
      loadingDonutType: "HalfCircleSpinner",
    };
  },
  mounted() {
    this.lineChartData = getLineChartData(this.theme);
    this.donutChartData = getDonutChartData(
      this.theme,
      this.poolListName,
      this.vmListCountperPool
    );

    this.$store.dispatch("requestBackupTask");
    this.$store.dispatch("requestPool");
    this.$store.dispatch("requestHost");
    this.$store.dispatch("requestVirtualMachine");
    this.$store.dispatch("requestStorage");
  },
  watch: {
    "$themes.success"() {
      this.lineChartData = getLineChartData(this.theme);
      this.donutChartData = getDonutChartData(
        this.theme,
        this.poolListName,
        this.vmListCountperPool
      );
    },

    "$themes.danger"() {
      this.lineChartData = getLineChartData(this.theme);
      this.donutChartData = getDonutChartData(
        this.theme,
        this.poolListName,
        this.vmListCountperPool
      );
    },

    "$themes.warning"() {
      this.donutChartData = getDonutChartData(
        this.theme,
        this.poolListName,
        this.vmListCountperPool
      );
    },
  },
  methods: {
    olderthan24hrs(timestamp) {
      let OneDay = new Date();
      OneDay.setDate(OneDay.getDate() - 1);
      OneDay = OneDay.getTime() / 1000;
      if (OneDay > timestamp) {
        // The yourDate time is less than 1 days from now
        return true;
      } else if (OneDay < timestamp) {
        // The yourDate time is more than 1 days from now
        return false;
      }
    },
    printChart() {
      const win = window.open("", "Print", "height=600,width=800");
      win.document.write(`<br><img src='${this.donutChartDataURL}'/>`);
      // TODO: find better solution how to remove timeout
      setTimeout(() => {
        win.document.close();
        win.focus();
        win.print();
        win.close();
      }, 200);
    },
  },
  computed: {
    configChart: function () {
      const generatedData = {
        labels: this.poolListName,
        datasets: [
          {
            label: "VM distribution by pool",
            backgroundColor: [
              "#2c82e0",
              "#DE1041",
              "#FFAC0A",
              "#babfc2",
              "#1B1A1F",
              "#E1E9F8",
            ],
            data: this.vmListCountperPool,
          },
        ],
      };
      return generatedData;
    },
    vmListCountperPool() {
      if (this.$store.state.resources.vmList) {
        const array = [];
        const countArray = [];
        const poolList = JSON.parse(
          JSON.stringify(this.$store.state.resources.poolList)
        );
        for (const item in poolList) {
          array.push(
            this.$store.state.resources.hostList.filter(
              (x) => x.pool_id === poolList[item].id
            )
          );
        }
        for (const subitem in array) {
          let count = 0;
          for (const item in JSON.parse(JSON.stringify(array[subitem]))) {
            count += this.$store.state.resources.vmList.filter(
              (x) => x.host === array[subitem][item].id
            ).length;
          }
          countArray.push(count);
        }
        return countArray;
      } else {
        return null;
      }
    },
    poolListName() {
      const array = [];
      const poolList = JSON.parse(
        JSON.stringify(this.$store.state.resources.poolList)
      );
      for (const item in poolList) {
        array.push(poolList[item].name);
      }
      return array;
    },
    filteredData() {
      return Object.values(this.$store.state.backupTaskList).filter(
        (x) =>
          (x.name === "Single_VM_Backup" || x.name === "backup_subtask") &&
          !this.olderthan24hrs(x.started) &&
          x.state === "FAILURE"
      );
    },
    tableData() {
      return this.filteredData.map((x) => {
        const isPool = x.name == "Pool_VM_Backup";
        const taskArg = x.args[0];
        const poolId = taskArg?.pool_id;
        return {
          uuid: x.uuid,
          name: x.name.replaceAll("_", " "),
          target: isPool
            ? this.$store.state.resources.poolList.find((e) => e.id == poolId)
                ?.name
            : taskArg?.name ?? "N/A",
          targetPage: isPool ? "pools" : "virtualmachines",
          targetUuid: taskArg?.uuid,
          started: x.started,
          ipAddress: x.ip_address,
          runtime: isPool ? null : x.runtime,
          state: x.state,
          parent: x.name == "backup_subtask" ? x.parent : null,
        };
      });
    },
    theme() {
      return useGlobalConfig().getGlobalConfig().colors;
    },
    donutChartDataURL() {
      return document
        .querySelector(".chart--donut canvas")
        .toDataURL("image/png");
    },
  },
});
</script>
<style scoped>
.chart {
  height: 350px;
}

.text-right {
  text-align: right;
}
</style>
