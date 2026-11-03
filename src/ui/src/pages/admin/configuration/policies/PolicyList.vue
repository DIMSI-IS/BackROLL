<template>
  <div>
    <va-card>
      <va-card-title>
        <ListHeader :title="$t('pages.configuration.policy.title')" :plus-button-title="$t('pages.configuration.policy.createButton')"
          plus-button-route="/admin/configuration/policies/new" :dependencies-resolved="areDependenciesResolved"
          :dependencies-message="$t('pages.configuration.policy.needStorage')" :go-button-title="$t('pages.configuration.policy.goToStorage')"
          go-button-route="/admin/configuration/storage" />
      </va-card-title>
      <va-card-content>
        <va-data-table :no-data-html="$t('pages.common.noItems')" :items="$store.state.resources.policyList" :columns="columns">
          <template #cell(schedule)="{ value }">
            <va-chip size="small" outline square>
              {{ humanCron(value) }}
            </va-chip>
          </template>
          <template #cell(externalhook)="{ value }">
            <va-chip @click="this.$router.push('/admin/configuration/externalhooks')" size="small" outline square>
              {{ value }}
            </va-chip>
          </template>
          <template #cell(enabled)="{ value }"><va-chip size="small" :color="JSON.parse(value) ? 'success' : 'danger'">
              {{ JSON.parse(value) ? $t('pages.configuration.policy.enabled') : $t('pages.configuration.policy.disabled') }}
            </va-chip>
          </template>
          <template #cell(storage)="{ value }">
            <va-chip size="small" square @click="this.$router.push('/admin/configuration/storage')">
              {{ getStorage(value) }}
            </va-chip>
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button :disabled="!$store.getters.canEdit" v-if="
                JSON.parse(
                  $store.state.resources.policyList[rowIndex].enabled
                )
              " icon="block" @click="
                (selectedPolicy =
                  $store.state.resources.policyList[rowIndex]),
                  (showDisableModal = !showDisableModal)
                  " />
              <va-button :disabled="!$store.getters.canEdit" v-else icon="start" @click="
                enablePolicy($store.state.resources.policyList[rowIndex])
                " />
              <va-button :disabled="!$store.getters.canEdit" icon="settings" @click="
                this.$router.push(
                  `/admin/configuration/policy/${$store.state.resources.policyList[rowIndex].id}`
                )
                " />
              <va-button :disabled="!$store.getters.canEdit" icon="delete" @click="
              (selectedPolicy =
                $store.state.resources.policyList[rowIndex]),
                (showDeleteModal = !showDeleteModal)
                " />
            </va-button-group>
          </template>
        </va-data-table>
        <div v-if="!$store.state.isPolicyTableReady" class="flex-center ma-3">
          <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
        </div>
      </va-card-content>
    </va-card>
    <va-modal v-model="showDisableModal" @ok="disablePolicy()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          {{ $t('pages.configuration.policy.disabling') }}
        </h2>
      </template>
      <hr />
      <div>
        {{ $t('pages.configuration.policy.disableIntro') }}
        <b>{{ JSON.parse(JSON.stringify(this.selectedPolicy)).name }}</b>. <br />{{ $t('pages.configuration.common.confirm') }}
      </div>
    </va-modal>
    <va-modal v-model="showDeleteModal" @ok="deletePolicy()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          {{ $t('pages.configuration.policy.removing') }}
        </h2>
      </template>
      <hr />
      <div>
        {{ $t('pages.configuration.policy.removeIntro') }}
        <b>{{ JSON.parse(JSON.stringify(this.selectedPolicy)).name }}</b>. <br />{{ $t('pages.configuration.common.confirm') }}
      </div>
    </va-modal>
  </div>
</template>

<script>
import axios from "axios";
import { defineComponent } from "vue";
import cronstrue from "cronstrue/i18n";
import * as spinners from "epic-spinners";

import ListHeader from "@/components/lists/ListHeader.vue";

export default defineComponent({
  name: "PoliciesTable",
  components: {
    ...spinners,
    ListHeader,
  },
  data() {
    return {
      showDeleteModal: false,
      showDisableModal: false,
      selectedPolicy: null,
    };
  },
  mounted() {
    this.$store.dispatch("requestPolicy");
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.configuration.common.name") },
        { key: "schedule", label: this.$t("pages.configuration.policy.schedule") },
        { key: "storage", label: this.$t("pages.configuration.policy.storage") },
        { key: "enabled", label: this.$t("pages.configuration.policy.autoStart") },
        { key: "actions", label: this.$t("pages.configuration.common.actions") },
      ];
    },
    areDependenciesResolved() {
      // Prevent showing irrelevant alert by checking if the table is ready.
      return (
        !this.$store.state.isStorageTableReady ||
        this.$store.state.storageList.length > 0
      );
    },
  },
  methods: {
    humanCron(value) {
      // Let the other rows render by catching the error.
      try {
        return cronstrue.toString(value, { locale: this.$i18n.locale });
      } catch {
        return this.$t("pages.configuration.policy.invalidSchedule");
      }
    },
    getStorage(id) {
      if (this.$store.state.isStorageTableReady) {
        const result = this.$store.state.storageList.filter((item) => {
          return item.id == id;
        });
        return result[0].name.toUpperCase();
      } else {
        return this.$t("pages.configuration.policy.loading");
      }
    },
    deletePolicy() {
      const policy = { ...this.selectedPolicy };
      axios
        .delete(
          `${this.$store.state.endpoint.api}/api/v1/backup_policies/${policy.id}`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestPolicy");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.policy.removed"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.policy.removeFailed"),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    disablePolicy() {
      const policy = { ...this.selectedPolicy };
      policy.state = 0;
      this.$store.dispatch("updatePolicy", {
        vm: this,
        policyValues: policy,
      });
    },
    enablePolicy(object) {
      const policy = { ...object };
      policy.state = 1;
      this.$store.dispatch("updatePolicy", {
        vm: this,
        policyValues: policy,
      });
    },
  },
});
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
