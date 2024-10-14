<template>
  <va-card>
    <va-card-title>
      <h1 v-if="poolId">Updating pool {{ statePool.name ?? "" }}</h1>
      <h1 v-else>Adding new pool</h1>
    </va-card-title>
    <va-card-content v-if="!poolId || statePool">
      <va-form ref="form" @validation="poolId ? updatePool() : addPool()">
        <va-input
          label="Name"
          v-model="formPool.name"
          :rules="[(value) => value?.length > 0 || 'Field is required']"
        />
        <br />
        <va-select
          label="Select policy"
          v-model="policySelection"
          :options="selectData"
          :rules="[(value) => isValid(value) || 'Field is required']"
        >
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
      </va-form>
      <br />
      <va-select
        label="Select Connector"
        v-model="connectorSelection"
        :options="selectConnectorData"
      />
      <br />
      <va-button class="mb-3" @click="$refs.form.validate()">
        {{ poolId ? "Update" : "Validate" }}
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

export default {
  components: { ...spinners },
  data() {
    return {
      poolId: this.$route.params.id,
      formPool: {
        name: "",
        policy_id: null,
        connector_id: null,
      },
      inputValue1: null,
      policySelection: {},
      connectorSelection: {},
    };
  },
  computed: {
    statePool() {
      return this.$store.state.resources.poolList.find(
        (item) => item.id == this.poolId
      );
    },
    selectData() {
      return this.$store.state.resources.policyList.map((x) => ({
        text: x.name,
        value: x.id,
      }));
    },
    selectConnectorData() {
      return this.$store.state.resources.connectorList.map((x) => ({
        text: x.name,
        value: x.id,
      }));
    },
  },
  watch: {
    statePool: function () {
      this.formPool = { ...this.statePool };
      this.updateConnector(this.formPool.connector_id);
    },
    selectData: function () {
      if (this.statePool && this.formPool.policy_id !== null) {
        this.updatePolicy(this.formPool.policy_id);
      }
    },
    selectConnectorData: function () {
      if (this.statePool && this.formPool.connector !== null) {
        this.updateConnector(this.formPool.connector);
      }
    },
  },
  mounted() {
    if (this.statePool) {
      this.formPool = { ...this.statePool };
      this.updatePolicy(this.formPool.policy_id);
      this.updateConnector(this.formPool.connector_id);
    }
  },
  methods: {
    updateConnector(id) {
      this.connectorSelection = this.selectConnectorData.find(
        (item) => item.value == id
      );
    },
    isValid(value) {
      if (Object.keys(value).length < 1) {
        return false;
      } else {
        return true;
      }
    },
    updatePolicy(id) {
      this.policySelection = this.selectData.find((item) => {
        return item.value == id;
      });
    },
    updatePool() {
      const pool = this.formPool;
      pool.policy_id = this.policySelection.value;
      pool.connector_id = this.connectorSelection.value;
      this.$store.dispatch("updatePool", {
        vm: this,
        token: this.$keycloak.token,
        poolValues: pool,
      });
    },
    addPool() {
      self = this;
      const pool = this.formPool;
      pool.policy_id = this.policySelection.value;
      pool.connector_id = this.connectorSelection.value;
      axios
        .post(`${this.$store.state.endpoint.api}/api/v1/pools`, pool, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.$keycloak.token}`,
          },
        })
        .then((response) => {
          this.$store.dispatch("requestPool", { token: this.$keycloak.token });
          this.$router.push("/admin/resources/pools");
          this.$vaToast.init({
            title: response.data.state,
            message: "Pool has been successfully added",
            color: "success",
          });
        })
        .catch(function (error) {
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            self.$vaToast.init({
              title: "Unable to add pool",
              message: error.response.data.detail,
              color: "danger",
            });
          }
        });
    },
  },
};
</script>

<style></style>
