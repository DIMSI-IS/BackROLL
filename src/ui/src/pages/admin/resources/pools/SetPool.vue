<template>
  <va-card>
    <va-card-title>
      <h1 v-if="pool && $store.state.ispoolTableReady">
        Updating pool {{ pool.name }}
      </h1>
      <h1 v-if="!pool || !$store.state.ispoolTableReady">Adding new pool</h1>
    </va-card-title>
    <va-card-content>
      <va-form ref="form" @validation="validation = $event">
        <va-input
          label="Name"
          v-model="poolValues.name"
          :rules="[
            (value) => (value && value.length > 0) || 'Field is required',
          ]"
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
        Validate
      </va-button>
    </va-card-content>
  </va-card>
</template>

<script>
import axios from "axios";
export default {
  data() {
    return {
      validation: false,
      inputValue1: null,
      policySelection: {},
      poolValues: {
        name: "",
        policy_id: null,
        connector_id: null,
      },
      connectorSelection: {},
    };
  },
  watch: {
    pool: function () {
      this.poolValues = { ...this.pool };
      this.updateConnector(this.poolValues.connector_id);
    },
    validation: function () {
      if (this.validation) {
        if(this.pool){
          this.updatePool();
        }else{
          this.addPool();
        }
      }
    },
    selectData: function () {
      if (this.pool && this.poolValues.policy_id !== null) {
        this.updatePolicy(this.poolValues.policy_id);
      }
    },
    selectConnectorData: function () {
      if (this.pool && this.poolValues.connector !== null) {
        this.updateConnector(this.poolValues.connector);
      }
    },
  },
  computed: {
    pool() {
      const result = this.$store.state.resources.poolList.filter((item) => {
        return item.id == this.$route.params.id;
      });
      return result[0];
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
  mounted() {
    if (this.pool) {
      this.poolValues = { ...this.pool };
      this.updatePolicy(this.poolValues.policy_id);
      this.updateConnector(this.poolValues.connector_id);
    }
  },
  methods: {
    updateConnector(id) {
      const result = this.selectConnectorData.filter((item) => {
        return item.value == id;
      });
      this.connectorSelection = result[0];
    },
    isValid(value) {
      if (Object.keys(value).length < 1) {
        return false;
      } else {
        return true;
      }
    },
    updatePolicy(id) {
      const result = this.selectData.filter((item) => {
        return item.value == id;
      });
      this.policySelection = result[0];
    },
    updatePool() {
      const pool = this.poolValues;
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
      const pool = this.poolValues;
      pool.policy_id = this.policySelection.value;
      pool.connector_id = this.connectorSelection.value;
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/pools`,
          pool,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$keycloak.token}`,
            },
          }
        )
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

<style>
</style>