<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          connectorId
            ? $t('pages.configuration.connector.updating', { name: stateConnector?.name ?? '' })
            : $t('pages.configuration.connector.adding')
        "
      />
    </va-card-title>
    <va-card-content v-if="!connectorId || stateConnector">
      <va-alert color="info" icon="info" dense>
        {{ $t('pages.configuration.connector.onlyCloudstack') }}
      </va-alert>
      <br />
      <va-form ref="form">
        <va-input
          :label="$t('pages.configuration.common.name')"
          v-model="formConnector.name"
          :rules="[
            (value) => value?.length > 0 || $t('pages.configuration.common.required'),
            (value) =>
              isConnectorNameUnique(value) ||
              $t('pages.configuration.connector.nameUsed'),
          ]"
        />
        <br />
        <!-- TODO Test for duplicates ? -->
        <va-input
          :label="$t('pages.configuration.connector.endpointUrl')"
          v-model="formConnector.url"
          :rules="[(value) => value?.length > 0 || $t('pages.configuration.common.required')]"
        />
        <br />
        <va-input
          :label="connectorId ? $t('pages.configuration.connector.loginUpdate') : $t('pages.configuration.connector.login')"
          v-model="formConnector.login"
          :rules="[(value) => connectorId || value?.length > 0 || $t('pages.configuration.common.required')]"
        />
        <br />
        <va-input
          v-model="formConnector.password"
          :type="isPasswordVisible ? 'text' : 'password'"
          :label="connectorId ? $t('pages.configuration.connector.passwordUpdate') : $t('pages.configuration.connector.password')"
          :rules="[(value) => connectorId || value?.length > 0 || $t('pages.configuration.common.required')]"
        >
          <template #appendInner>
            <va-icon
              :name="isPasswordVisible ? 'visibility_off' : 'visibility'"
              size="small"
              color="--va-primary"
              @click="isPasswordVisible = !isPasswordVisible"
            />
          </template>
        </va-input>
      </va-form>
      <br />
      <va-button
        class="mb-3"
        @click="
          $refs.form.validate() &&
            (connectorId ? updateConnector() : addConnector())
        "
      >
        {{ connectorId ? $t('pages.configuration.common.update') : $t('pages.configuration.common.add') }}
      </va-button>
    </va-card-content>
    <div v-else class="flex-center ma-3">
      <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
    </div>
  </va-card>
</template>

<script>
import axios from "axios";
import * as spinners from "epic-spinners";

import FormHeader from "@/components/forms/FormHeader.vue";
import { canonicalName } from "@/pages/admin/forms";

export default {
  components: {
    ...spinners,
    FormHeader,
  },
  data() {
    return {
      connectorId: this.$route.params.id,
      formConnector: {
        name: null,
        url: null,
        login: null,
        password: null,
      },
      isPasswordVisible: false,
    };
  },
  computed: {
    stateConnector() {
      return this.$store.state.resources.connectorList.find(
        (item) => item.id == this.connectorId
      );
    },
  },
  watch: {
    stateConnector: function () {
      this.propagateStateConnector();
    },
  },
  methods: {
    isConnectorNameUnique(value) {
      const canonical = canonicalName(value);
      return !this.$store.state.resources.connectorList.find(
        ({ id, name }) =>
          id != this.connectorId && canonicalName(name) == canonical
      );
    },
    propagateStateConnector() {
      // The secret is never sent back by the server.
      this.formConnector = { ...this.stateConnector, password: "" };
    },
    updateConnector() {
      this.$store.dispatch("updateConnector", {
        vm: this,
        connectorValues: this.formConnector,
      });
    },
    addConnector() {
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/connectors`,
          this.formConnector,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestConnector");
          this.$router.push("/admin/configuration/connectors");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.connector.added"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.connector.addFailed"),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
  mounted() {
    // TODO Wait ?
    this.$store.dispatch("requestConnector");
    if (this.stateConnector) {
      this.propagateStateConnector();
    }
  },
};
</script>
<style></style>
