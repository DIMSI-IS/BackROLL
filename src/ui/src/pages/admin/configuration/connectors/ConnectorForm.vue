<template>
  <va-card>
    <va-card-title>
      <FormHeader :title="connectorId ? `Updating connector ${stateConnector?.name ?? ''}` : 'Adding connector'" />
    </va-card-title>
    <va-card-content v-if="!connectorId || stateConnector">
      <va-alert color="info" icon="info" dense>
        For now, the only supported connector is Cloudstack
      </va-alert>
      <br />
      <va-form ref="form" @validation="connectorId ? updateConnector() : addConnector()">
        <va-input label="Name" v-model="formConnector.name"
          :rules="[(value) => value?.length > 0 || 'Field is required']" />
        <br />
        <va-input label="Endpoint URL" v-model="formConnector.url"
          :rules="[(value) => value?.length > 0 || 'Field is required']" />
        <br />
        <va-input label="Login" v-model="formConnector.login"
          :rules="[(value) => value?.length > 0 || 'Field is required']" />
        <br />
        <va-input v-model="formConnector.password" :type="isPasswordVisible ? 'text' : 'password'" label="Password"
          :rules="[(value) => value?.length > 0 || 'Field is required']">
          <template #appendInner>
            <va-icon :name="isPasswordVisible ? 'visibility_off' : 'visibility'" size="small" color="--va-primary"
              @click="isPasswordVisible = !isPasswordVisible" />
          </template>
        </va-input>
      </va-form>
      <br />
      <va-button class="mb-3" @click="$refs.form.validate()">
        {{ connectorId ? "Update" : "Add" }}
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

export default {
  components: {
    ...spinners,
    FormHeader
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
  mounted() {
    if (this.stateConnector) {
      this.propagateStateConnector();
    }
  },
  methods: {
    propagateStateConnector() {
      this.formConnector = { ...this.stateConnector };
    },
    updateConnector() {
      this.$store.dispatch("updateConnector", {
        vm: this,
        token: this.$keycloak.token,
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
              Authorization: `Bearer ${this.$keycloak.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestConnector", {
            token: this.$keycloak.token,
          });
          this.$router.push("/admin/configuration/connectors");
          this.$vaToast.init({
            title: response.data.state,
            message: "Connector has been successfully added",
            color: "success",
          });
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unable to add connector",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
};
</script>
<style></style>
