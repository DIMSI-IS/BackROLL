<template>
  <va-card>
    <va-card-title>
      <ListHeader :title="$t('pages.configuration.connector.title')" :plus-button-title="$t('pages.configuration.connector.addButton')"
        plus-button-route="/admin/configuration/connectors/new" />
    </va-card-title>
    <va-card-content>
      <va-data-table :no-data-html="$t('pages.common.noItems')" :items="$store.state.resources.connectorList" :columns="columns">
        <template #cell(name)="{ value }">
          {{ value }}
        </template>
        <template #cell(url)="{ value }">
          {{ value }}
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button :disabled="!$store.getters.canEdit" icon="settings" @click="
              this.$router.push(
                `/admin/configuration/connectors/${$store.state.resources.connectorList[rowIndex].id}`
              )
              " />
            <va-button :disabled="!$store.getters.canEdit" icon="delete" @click="
            (selectedConnector =
              $store.state.resources.connectorList[rowIndex]),
              (showDeleteModal = !showDeleteModal)
              " />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isexternalHookTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
  <va-modal v-model="showDeleteModal" @ok="deleteConnector()">
    <template #header>
      <h2>
        <va-icon name="warning" color="danger" />
        {{ $t('pages.configuration.connector.removing') }}
      </h2>
    </template>
    <hr />
    <div>
      {{ $t('pages.configuration.connector.removeIntro') }}
      <b>{{ JSON.parse(JSON.stringify(this.selectedConnector)).name }}</b>. <br />{{ $t('pages.configuration.common.confirm') }}
    </div>
  </va-modal>
</template>
<script>
import axios from "axios";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import { errorMessage } from "@/services/errorMessage";

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
      selectedConnector: null,
    };
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.configuration.common.name") },
        { key: "url", label: this.$t("pages.configuration.connector.url") },
        { key: "actions", label: this.$t("pages.configuration.common.actions") },
      ];
    },
  },
  methods: {
    deleteConnector() {
      const connector = { ...this.selectedConnector };
      axios
        .delete(
          `${this.$store.state.endpoint.api}/api/v1/connectors/${connector.id}`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestConnector");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.connector.removed"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.connector.removeFailed"),
            message: errorMessage(error),
            color: "danger",
          });
        });
    },
  },
  mounted() {
    this.$store.dispatch("requestConnector");
  },
});
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
