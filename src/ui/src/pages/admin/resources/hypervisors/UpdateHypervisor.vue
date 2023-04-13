<template>
  <va-card v-if="hypervisor && $store.state.ishostTableReady">
    <va-card-title>
      <h1>Update hypervisor {{ hypervisor.hostname }}</h1>
    </va-card-title>
    <va-card-content>
      <va-form
        ref="form"
        @validation="validation = $event"
      >
        <va-input
          label="Hostname"
          v-model="updatedValues.hostname"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="IP Address"
          v-model="updatedValues.ipaddress"
          :rules="[value => (value && value.match(`^(?!0)(?!.*\\.$)((1?\\d?\\d|25[0-5]|2[0-4]\\d)(\\.|$)){4}$`)) || 'Field is required and must be a valid IP address']"
        />
        <br>
        <va-select
          label="Select Pool"
          v-model="poolSelection"
          :options="selectPoolData"
          :rules="[value => isValid(value) || 'Field is required']"
        />
        <br>
        <va-input
          label="Tag (optional)"
          v-model="updatedValues.tags"
        />

        <br>
        <va-switch v-model="useConnector" size="small">
          <template #innerLabel>
            Use connector
          </template>
        </va-switch>

        <br>
        <va-select
          v-if="useConnector"
          label="Select Connector"
          v-model="connectorSelection"
          :options="selectConnectorData"
        />

      </va-form>
      <br>
      <va-button
        class="mb-3"
        @click="$refs.form.validate()"
      >
        Validate
      </va-button>
    </va-card-content>
  </va-card>
</template>

<script>
export default {
  data () {
    return {
      useConnector: false,
      validation: false,
      updatedValues: {
        hostname: null,
        ipaddress: null,
        pool: null,
        connector_id: null,
        tags: null
      },
      poolSelection: {},
      connectorSelection: {}
    }
  },
  mounted () {
    this.updatedValues = {...this.hypervisor}
    this.updatePool(this.updatedValues.pool_id)
    this.updateConnector(this.updatedValues.connector_id)
  },
  watch: {
    hypervisor: function () {
      this.updatedValues = {...this.hypervisor}
      this.updatePool(this.updatedValues.pool_id)
      this.updateConnector(this.updatedValues.connector_id)
    },
    updatedValues: function () {
      if (this.updatedValues.connector_id) {
        this.useConnector = true
      } else {
        this.useConnector = false
      }
    },
    validation: function () {
      if (this.validation) {
        this.updateHost()
      }
    },
    selectPoolData: function () {
      if (this.updatedValues.pool !== null) {
        this.updatePool(this.updatedValues.pool)
      }
    },
    selectConnectorData: function () {
      if (this.updatedValues.connector !== null) {
        this.updateConnector(this.updatedValues.connector)
      }
    }
  },
  computed: {
    hypervisor () {
      const result = this.$store.state.resources.hostList.filter((item) => {
        return item.id == this.$route.params.id
      })
      return result[0]
    },
    selectPoolData() {
      return this.$store.state.resources.poolList.map(x => ({
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
  methods: {
    isValid(value) {
      if (Object.keys(value).length < 1) {
        return false
      } else {
        return true
      }
    },
    updatePool(id) {
      const result = this.selectPoolData.filter((item) => {
        return item.value == id
      })
      this.poolSelection = result[0]
    },
    updateConnector(id) {
      const result = this.selectConnectorData.filter((item) => {
        return item.value == id
      })
      this.connectorSelection = result[0]
    },
    updateHost() {
      const hypervisor = this.updatedValues
      hypervisor.pool_id = this.poolSelection.value
      if (this.useConnector) {
        hypervisor.connector_id = this.connectorSelection.value
      } else {
        hypervisor.connector_id = null
      }
      this.$store.dispatch("updateHost", {
        vm: this,
        token: this.$keycloak.token,
        hostValues: hypervisor
      })
    }
  }
}
</script>

<style>

</style>