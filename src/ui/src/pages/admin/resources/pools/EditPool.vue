<template>
  <va-card v-if="pool && $store.state.ispoolTableReady">
    <va-card-title>
      <h1>Updating pool {{ pool.name }}</h1>
    </va-card-title>
    <va-card-content>
      <va-form ref="form" @validation="validation = $event">
        <va-input label="Name" v-model="updatedValues.name"
          :rules="[value => (value && value.length > 0) || 'Field is required']" />
        <br>
        <va-select label="Select policy" v-model="policySelection" :options="selectData" multiple
          :rules="[value => isValid(value) || 'Field is required']">
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
        <br>
        <va-select
          label="Select Connector"
          v-model="connectorSelection"
          :options="selectConnectorData"
          :rules="[value => isValid(value) || 'Field is required']"
        />
      </va-form>
      <br>
      <br>
      <va-button class="mb-3" @click="$refs.form.validate()">
        Validate
      </va-button>
    </va-card-content>
  </va-card>
</template>

<script>
  export default {
    data() {
      return {
        validation: false,
        inputValue1: null,
        policySelection: [],
        updatedValues: {},
        connectorSelection: {}
      }
    },
    watch: {
      pool: function () {
        this.updatedValues = { ...this.pool }
        this.updateConnector(this.updatedValues.connector_id)
      },
      validation: function () {
        if (this.validation) {
          this.updatePool()
        }
      },
      selectDatas: function () {
        if (this.updatedValues.policy_id !== null) {
          this.updatePolicy(this.updatedValues.policy_id)
        }
      },
      selectConnectorData: function () {
        if (this.updatedValues.connector !== null) {
          this.updateConnector(this.updatedValues.connector)
        }
      }
    },
    computed: {
      pool() {
        const result = this.$store.state.resources.poolList.filter((item) => {
          return item.id == this.$route.params.id
        })
        return result[0]
      },
      selectData() {
        return this.$store.state.resources.policyList.map(x => ({
          text: x.name,
          value: x.id
        }))
      },
      selectConnectorData() {
        return this.$store.state.resources.connectorList.map(x => ({
          text: x.name,
          value: x.id
        }))
      }
    },
    mounted() {
      this.updatedValues = { ...this.pool }
      this.updatePolicy(this.updatedValues.policy_id)
      this.updateConnector(this.updatedValues.connector_id)
    },
    methods: {
      updateConnector(id) {
        const result = this.selectConnectorData.filter((item) => {
          return item.value == id
        })
        this.connectorSelection = result[0]
      },
      isValid(value) {
        if (Object.keys(value).length < 1) {
          return false
        } else {
          return true
        }
      },
      updatePolicy(id) {
        const result = this.selectData.filter((item) => {
          return item.value == id
        })
        this.policySelection = result[0]
      },
      updatePool() {
        const pool = this.updatedValues
        pool.policy_id = this.policySelection.value
        this.$store.dispatch("updatePool", {
          vm: this,
          token: this.$keycloak.token,
          poolValues: pool
        })
      }
    }
  }
</script>

<style>

</style>