<template>
  <div class="row row-equal">
    <div class="flex xl8 xs12">
      <div class="row" v-if="$store.state.isvmTableReady">
        <div class="flex xs12 sm4" v-for="(info, idx) in infoTiles" :key="idx">
          <va-card
            class="mb-4 clickable"
            :color="info.light"
            @click="navigateTo(info.route)"
          >
            <va-card-content>
              <div class="icon-text-row">
                <va-icon
                  v-if="info.icon"
                  :name="info.icon"
                  :size="50"
                  class="card-hover"
                />
                <div>
                  <p class="display-2 mb-0 card-hover">{{ info.value }}</p>
                  <p class="card-hover">
                    {{ $t("dashboard.info." + info.text) }}
                  </p>
                </div>
              </div>
            </va-card-content>
          </va-card>
        </div>
      </div>
      <div v-else class="row row-equal">
        <div class="flex xs12 xl12">
          <va-card class="mb-12" color="light" style="width: 100%">
            <va-card-content class="table-example--pagination">
              <component
                :animation-duration="1500"
                :is="loadingDataType"
                color="#2c82e0"
                :size="120"
              >
              </component>
            </va-card-content>
          </va-card>
        </div>
      </div>
      <div class="row">
        <div class="flex xs12 md6">
          <va-card stripe stripe-color="info">
            <va-card-title>
              {{
                `${$t(
                  "dashboard.info.componentReleaseVersion"
                )} ${backrollVersion}`
              }}
            </va-card-title>
            <va-card-content>
              <p class="rich-theme-card-text">
                {{ $t("dashboard.info.gitprojectinfo") }}
              </p>
              <div class="mt-3">
                <va-button
                  color="primary"
                  target="_blank"
                  href="https://github.com/DIMSI-IS/backroll"
                >
                  {{ $t("dashboard.info.viewProject") }}
                </va-button>
              </div>
            </va-card-content>
          </va-card>
        </div>
        <div class="flex xs12 md6">
          <va-card>
            <va-card-title>{{ $t("dashboard.info.lastTask") }}</va-card-title>
            <va-card-content>
              <div class="row row-separated">
                <div class="flex xs6">
                  <p
                    class="display-2 mb-1 text--center"
                    :style="{ color: theme.success }"
                  >
                    {{ successTaskNumber }}
                  </p>
                  <p class="text--center mb-1">
                    {{ $t("dashboard.info.success") }}
                  </p>
                </div>
                <div class="flex xs6">
                  <p
                    class="display-2 mb-1 text--center"
                    :style="{ color: theme.danger }"
                  >
                    {{ failureTaskNumber }}
                  </p>
                  <p class="text--center no-wrap mb-1">
                    {{ $t("dashboard.info.failure") }}
                  </p>
                </div>
              </div>
            </va-card-content>
          </va-card>
        </div>
      </div>
    </div>
    <div class="flex xs12 md12 xl4">
      <va-card stripe stripe-color="dark">
        <va-card-title> Storage </va-card-title>
        <va-card-content
          v-if="!$store.state.isStorageTableReady"
          class="table-example--pagination"
        >
          <component
            :animation-duration="1500"
            :is="loadingStorageType"
            color="#2c82e0"
            :size="120"
          />
        </va-card-content>
        <va-card-content v-else>
          <va-list>
            <va-list-item
              v-for="(storage, index) in $store.state.storageList"
              :key="index"
              to="/admin/configuration/storage"
            >
              <va-list-item-section>
                <div
                  v-if="storage.info"
                  style="
                    display: flex;
                    justify-content: space-between;
                    width: 100%;
                  "
                >
                  <div style="display: flex; flex-direction: column">
                    <va-list-item-label>
                      <b>{{ storage.name.toUpperCase() }}</b>
                    </va-list-item-label>

                    <va-list-item-label caption>
                      {{ humanStorageSize(storage.info.used) }} /
                      {{ humanStorageSize(storage.info.total) }}
                    </va-list-item-label>

                    <va-chip
                      size="small"
                      outline
                      square
                      :color="
                        (
                          100 -
                          (storage.info.free / storage.info.total) * 100
                        ).toFixed(1) < 75
                          ? 'success'
                          : 'danger'
                      "
                    >
                      <va-icon
                        v-if="
                          (
                            100 -
                            (storage.info.free / storage.info.total) * 100
                          ).toFixed(1) >= 75
                        "
                        name="warning"
                        color="danger"
                      />
                      <span style="margin-right: 2px"
                        ><b
                          >{{
                            (
                              100 -
                              (storage.info.free / storage.info.total) * 100
                            ).toFixed(1)
                          }}% Used</b
                        ></span
                      >
                      ({{ humanStorageSize(storage.info.free) }} free)
                    </va-chip>
                  </div>
                  <div
                    style="
                      aspect-ratio: 1 / 1;
                      max-width: 100px;
                      width: 100%;
                      margin-left: auto;
                      margin-right: auto;
                    "
                  >
                    <va-chart
                      class="chart chart--donut"
                      type="donut"
                      :data="getStorageDonutChart(storage)"
                    />
                  </div>
                </div>
                <div v-else>
                  <va-chip size="small" outline square color="danger">
                    <va-icon class="material-icons" color="danger"
                      >warning</va-icon
                    >
                    Unable to retrieve information
                  </va-chip>
                </div>
              </va-list-item-section>
            </va-list-item>
          </va-list>
        </va-card-content>
      </va-card>
    </div>
    <va-modal v-model="modal">
      <div style="position: relative">
        <va-button
          @click="showPrevImage"
          color="#fff"
          icon="chevron-left"
          flat
          style="position: absolute; top: 50%"
        />
        <va-button
          @click="showNextImage"
          color="#fff"
          icon="chevron-right"
          flat
          style="position: absolute; top: 50%; right: 0"
        />
        <transition>
          <img
            :src="images[currentImageIndex]"
            style="height: 50vh; max-width: 100%"
          />
        </transition>
      </div>
    </va-modal>
  </div>
</template>

<script>
import { useGlobalConfig } from "vuestic-ui";
import * as spinners from "epic-spinners";
import VaChart from "@/components/va-charts/VaChart.vue";

export default {
  name: "DashboardInfoBlock",
  components: { ...spinners, VaChart },
  data() {
    return {
      backrollVersion: process.env.VUE_APP_BACKROLL_VERSION,
      infoTiles: [
        {
          color: "info",
          value: this.$store.state.resources.hostList.length,
          text: "hypervisors",
          icon: "dns",
          route: "/admin/resources/hypervisors",
        },
        {
          color: "info",
          value: this.$store.state.resources.poolList.length,
          text: "pools",
          icon: "hub",
          route: "/admin/resources/pools",
        },
        {
          color: "info",
          value: this.$store.state.resources.vmList.length,
          text: "virtualmachines",
          icon: "computer",
          route: "/admin/resources/virtualmachines",
        },
      ],
      modal: false,
      currentImageIndex: 0,
      loadingDataType: "LoopingRhombusesSpinner",
      loadingStorageType: "SelfBuildingSquareSpinner",
    };
  },
  watch: {
    poolCount(newCount) {
      this.infoTiles.filter(function (elem) {
        if (elem.text == "pools") {
          elem.value = newCount;
        }
      });
    },
    hostCount(newCount) {
      this.infoTiles.filter(function (elem) {
        if (elem.text == "hypervisors") {
          elem.value = newCount;
        }
      });
    },
    vmCount(newCount) {
      this.infoTiles.filter(function (elem) {
        if (elem.text == "virtualmachines") {
          elem.value = newCount;
        }
      });
    },
  },
  methods: {
    getStorageDonutChart(storage) {
      const used = storage.info.used || 0;
      const total = storage.info.total || 1;
      const free = total - used;
      const percentUsed = ((used / total) * 100).toFixed(1);
      const usedColor =
        percentUsed < 75 ? this.theme.success : this.theme.danger;
      return {
        //labels: ["Used", "Free"],
        datasets: [
          {
            backgroundColor: [usedColor, "#e0e0e0"],
            data: [used, free],
          },
        ],

        options: {
          plugins: {
            legend: {
              display: false,
            },
            title: {
              display: false,
            },
          },
        },
      };
    },

    humanStorageSize(bytes, si = false, dp = 1) {
      const thresh = si ? 1000 : 1024;
      if (Math.abs(bytes) < thresh) {
        return bytes + " B";
      }
      const units = si
        ? ["kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        : ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"];
      let u = -1;
      const r = 10 ** dp;
      do {
        bytes /= thresh;
        ++u;
      } while (
        Math.round(Math.abs(bytes) * r) / r >= thresh &&
        u < units.length - 1
      );
      return bytes.toFixed(dp) + " " + units[u];
    },
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
    showModal() {
      this.modal = true;
    },
    showPrevImage() {
      this.currentImageIndex = !this.currentImageIndex
        ? this.images.length - 1
        : this.currentImageIndex - 1;
    },
    showNextImage() {
      this.currentImageIndex =
        this.currentImageIndex === this.images.length - 1
          ? 0
          : this.currentImageIndex + 1;
    },
    navigateTo(route) {
      if (route) {
        this.$router.push(route);
      }
    },
  },
  computed: {
    theme() {
      return useGlobalConfig().getGlobalConfig().colors || {};
    },
    poolCount() {
      return this.$store.state.resources.poolList.length;
    },
    hostCount() {
      return this.$store.state.resources.hostList.length;
    },
    vmCount() {
      return this.$store.state.resources.vmList.length;
    },
    backupTaskList() {
      return Object.values(this.$store.state.backupTaskList).filter(
        (x) =>
          (x.name === "Single_VM_Backup" || x.name === "backup_subtask") &&
          !this.olderthan24hrs(x.started)
      );
    },
    successTaskNumber() {
      return this.backupTaskList.filter((x) => x.state === "SUCCESS").length;
    },
    failureTaskNumber() {
      return this.backupTaskList.filter((x) => x.state === "FAILURE").length;
    },
    pendingTaskNumber() {
      return this.backupTaskList.filter((x) => x.state === "RECEIVED").length;
    },
  },
};
</script>

<style lang="scss" scoped>
.row-separated {
  .flex + .flex {
    border-left: 1px solid var(--va-background);
  }

  // @include media-breakpoint-down(xs) {
  //   p:not(.display-2) {
  //     font-size: 0.875rem;
  //   }
  // }
}

.rich-theme-card-text {
  line-height: 24px;
}

.table-example--pagination {
  text-align: center;
  text-align: -webkit-center;
}

.clickable {
  cursor: pointer;
  transition: box-shadow 0.2s ease;
}
.clickable:hover {
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
}

.clickable:hover .card-hover {
  color: var(--va-primary);
}

.card-hover {
  transition: color 0.2s ease;
}
.icon-text-row {
  display: flex;
  align-items: center;
  gap: 30px;
}
.chart.chart--donut {
  width: auto;
  height: 100%;
}
// .dashboard {
//   .va-card__header--over {
//     @include media-breakpoint-up(md) {
//       padding-top: 0 !important;
//     }
//   }

//   .va-card__image {
//     @include media-breakpoint-up(md) {
//       padding-bottom: 0 !important;
//     }
//   }
//   .image-card {
//     position: relative;
//     .va-button {
//       position: absolute;
//     }
//   }
// }
</style>
