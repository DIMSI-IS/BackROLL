<template>
  <va-card>
    <va-card-title>
      <ListHeader
        :title="$t('pages.resources.pool.title')"
        :plus-button-title="$t('pages.resources.pool.createButton')"
        plus-button-route="/admin/resources/pools/new"
        :dependencies-resolved="areDependenciesResolved"
        :dependencies-message="$t('pages.resources.pool.needPolicy')"
        :go-button-title="$t('pages.resources.pool.goToPolicies')"
        go-button-route="/admin/configuration/policies"
      />
    </va-card-title>
    <va-card-content>
      <va-data-table :no-data-html="$t('pages.common.noItems')"
        :items="$store.state.resources.poolList"
        :columns="columns"
      >
        <template #cell(name)="{ value }">{{ value.toUpperCase() }}</template>
        <template #cell(policy_id)="{ value }">
          <va-chip
            size="small"
            square
            @click="this.$router.push('/admin/configuration/policies')"
          >
            {{ getBackupPolicy(value)?.name?.toUpperCase() }}
          </va-chip>
        </template>
        <template #cell(connector_id)="{ value }">
          <va-chip
            v-if="getConnector(value)"
            size="small"
            color="#7f1f90"
            square
            @click="this.$router.push('/admin/configuration/connectors')"
          >
            {{ getConnector(value) }}
          </va-chip>
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button :disabled="!$store.getters.canEdit"
              icon="settings"
              @click="
                this.$router.push(
                  `/admin/resources/pools/${$store.state.resources.poolList[rowIndex].id}`
                )
              "
            />
            <va-button :disabled="!$store.getters.canEdit"
              icon="delete"
              @click="
                (selectedPool = $store.state.resources.poolList[rowIndex]),
                  (showDeleteModal = !showDeleteModal)
              "
            />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isPoolTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
  <va-modal v-model="showDeleteModal" :ok-text="$t('pages.resources.common.ok')" :cancel-text="$t('pages.resources.common.cancel')" @ok="deletePool()">
    <template #header>
      <h2>
        <va-icon name="warning" color="danger" />
        {{ $t('pages.resources.pool.removing') }}
      </h2>
    </template>
    <hr />
    <div>
      {{ $t('pages.resources.pool.removeIntro') }}
      <b>{{ JSON.parse(JSON.stringify(this.selectedPool)).name }}</b
      >. <br />{{ $t('pages.resources.common.confirmAction') }}
    </div>
  </va-modal>
</template>

<script>
import axios from "axios";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";

import ListHeader from "@/components/lists/ListHeader.vue";

export default defineComponent({
  name: "PoolsTable",
  components: {
    ...spinners,
    ListHeader,
  },
  data() {
    return {
      showDeleteModal: false,
      selectedPool: null,
    };
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.pool.colName") },
        { key: "policy_id", label: this.$t("pages.resources.pool.colPolicy") },
        { key: "connector_id", label: this.$t("pages.resources.pool.colConnector") },
        { key: "actions", label: this.$t("pages.resources.pool.colActions") },
      ];
    },
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.pool.colName") },
        { key: "policy_id", label: this.$t("pages.resources.pool.colPolicy") },
        { key: "connector_id", label: this.$t("pages.resources.pool.colConnector") },
        { key: "actions", label: this.$t("pages.resources.pool.colActions") },
      ];
    },
    areDependenciesResolved() {
      // Prevent showing irrelevant alert by checking if the table is ready.
      return (
        !this.$store.state.isPolicyTableReady ||
        this.$store.state.resources.policyList.length > 0
      );
    },
  },
  methods: {
    getConnector(id) {
      const result = this.$store.state.resources.connectorList.find(
        (item) => item.id === id
      );
      if (result) {
        return result.name.toUpperCase();
      } else {
        return null;
      }
    },
    deletePool() {
      axios
        .delete(
          `${this.$store.state.endpoint.api}/api/v1/pools/${this.selectedPool.id}`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestPool");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t('pages.resources.pool.deleted'),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t('pages.resources.pool.deleteFailed'),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    humanPoolsSize(bytes, si = false, dp = 1) {
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
    getBackupPolicy(policyId) {
      return this.$store.state.resources.policyList.find(
        ({ id }) => id == policyId
      );
    },
  },
  mounted() {
    this.$store.dispatch("requestPolicy");
    this.$store.dispatch("requestPool");
  },
});
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
