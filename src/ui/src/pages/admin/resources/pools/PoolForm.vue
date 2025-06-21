<template>
  <va-card>
    <va-card-title>
      <FormHeader :title="poolId ? `Updating pool ${statePool?.name ?? ''}` : 'Creating pool'" />
    </va-card-title>
    <va-card-content v-if="!poolId || statePool">
      <va-form ref="form">
        <va-input label="Name" v-model="formPool.name" :rules="[(value) => value?.length > 0 || 'Field is required']" />
        <br />
        <va-select label="Select policy" v-model="selectedPolicy" :options="policyOptions"
          :rules="[(value) => value || 'Field is required']">
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
      </va-form>
      <br />
      <va-select label="Select connector (optional)" v-model="selectedConnector" :options="connectorOptions" />
      <br />
      <va-button class="mb-3" @click="$refs.form.validate() && (poolId ? updatePool() : addPool())">
        {{ poolId ? "Update" : "Create" }}
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
      poolId: this.$route.params.id,
      formPool: {
        name: "",
      },
      selectedPolicy: null,
      selectedConnector: null,
    };
  },
  computed: {
    statePool() {
      return this.$store.state.resources.poolList.find(
        (e) => e.id == this.poolId
      );
    },
    policyOptions() {
      return this.$store.state.resources.policyList.map((e) => ({
        text: e.name,
        value: e.id,
      }));
    },
    connectorOptions() {
      return this.$store.state.resources.connectorList.map((e) => ({
        text: e.name,
        value: e.id,
      }));
    },
  },
  watch: {
    statePool: function () {
      this.propagateStatePool();
    },
    policyOptions: function () {
      if (this.selectedPolicy) {
        this.updatePolicy(this.selectedPolicy.value);
      }
    },
    connectorOptions: function () {
      if (this.selectedConnector) {
        this.updateConnector(this.selectedConnector.value);
      }
    },
  },
  mounted() {
    if (this.statePool) {
      this.propagateStatePool();
    }
  },
  methods: {
    propagateStatePool() {
      this.formPool = { ...this.statePool };
      this.updatePolicy(this.statePool.policy_id);
      this.updateConnector(this.statePool.connector_id);
    },
    updatePolicy(id) {
      this.selectedPolicy = this.policyOptions.find((e) => e.value == id);
    },
    updateConnector(id) {
      this.selectedConnector = this.connectorOptions.find((e) => e.value == id);
    },
    exportPool() {
      const pool = JSON.parse(JSON.stringify(this.formPool));

      if (this.selectedPolicy) {
        pool.policy_id = this.selectedPolicy.value;
      }
      if (this.selectedConnector) {
        pool.connector_id = this.selectedConnector.value;
      }

      return pool;
    },
    updatePool() {
      this.$store.dispatch("updatePool", {
        vm: this,
        token: this.$store.state.token,
        poolValues: this.exportPool(),
      });
    },
    addPool() {
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/pools`,
          this.exportPool(),
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestPool", { token: this.$store.state.token });
          this.$router.push("/admin/resources/pools");
          this.$vaToast.init({
            title: response.data.state,
            message: "Pool has been successfully added",
            color: "success",
          });
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unable to add pool",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
};
</script>

<style></style>
