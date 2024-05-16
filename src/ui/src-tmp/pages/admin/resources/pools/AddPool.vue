<template>
  <va-card>
    <va-card-title>
      <h1>Adding new pool</h1>
    </va-card-title>
    <va-card-content>
      <va-form ref="form" @validation="validation = $event">
        <va-input label="Name" v-model="inputValue1"
          :rules="[value => (value && value.length > 0) || 'Field is required']" />
        <br>
        <va-select label="Select policy" v-model="policySelection" :options="selectData"
          :rules="[value => isValid(value) || 'Field is required']">
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
      </va-form>
      <br>
      <va-select
        label="Select Connector"
        v-model="connectorSelection"
        :options="selectConnectorData"
      />
      <br>
      <va-button class="mb-3" @click="$refs.form.validate()">
        Validate
      </va-button>
    </va-card-content>
  </va-card>
</template>

<script>
  import axios from 'axios'
  export default {
    data() {
      return {
        connector: null,
        validation: false,
        inputValue1: null,
        policySelection: {},
        connectorSelection: {}
      }
    },
    watch: {
      validation: function () {
        if (this.validation) {
          this.addPool()
        }
      }
    },
    computed: {
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
    methods: {
      isValid(value) {
        if (Object.keys(value).length < 1) {
          return false
        } else {
          return true
        }
      },
      addPool() {
        console.log(this.connectorSelection)
        axios.post(`${this.$store.state.endpoint.api}/api/v1/pools`, { name: this.inputValue1, policy_id: this.policySelection.value, connector_id: this.connectorSelection.value }, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
          .then(response => {
            this.$store.dispatch("requestPool", { token: this.$keycloak.token })
            this.$router.push('/admin/resources/pools')
            this.$vaToast.init(({ title: response.data.state, message: "Pool has been successfully added", color: 'success' }))
          })
          .catch(function (error) {
            if (error.response) {
              // The request was made and the server responded with a status code
              // that falls out of the range of 2xx
              self.$vaToast.init(({ title: 'Unable to add pool', message: error.response.data.detail, color: 'danger' }))
            }
          })
      }
    }
  }
</script>

<style>

</style>