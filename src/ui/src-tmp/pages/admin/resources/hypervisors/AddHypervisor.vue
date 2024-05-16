<template>
  <va-card>
    <va-card-title>
      <h1>Adding new hypervisor</h1>
    </va-card-title>
    <va-card-content>
      <va-form
        ref="form"
        @validation="validation = $event"
      >
        <va-input
          label="Hostname"
          v-model="host.hostname"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="IP Address"
          v-model="host.ipaddress"
          :rules="[value => (value && value.match(`^(?!0)(?!.*\\.$)((1?\\d?\\d|25[0-5]|2[0-4]\\d)(\\.|$)){4}$`)) || 'Field is required and must be a valid IP address']"
        />
        <br>
        <va-select
          label="Select Pool"
          v-model="poolSelection"
          :options="selectData"
          :rules="[value => isValid(value) || 'Field is required']"
        />
        <br>
        <va-input
          label="Tag (optional)"
          v-model="host.tags"
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
import axios from 'axios'
export default {
  data () {
    return {
      validation: false,
      host: {
        hostname: null,
        ipaddress: null,
        pool: null,
        tags: null,
      },
      poolSelection: {},
    }
  },
  watch: {
    validation: function () {
      if (this.validation) {
        this.addHypervisor()
      }
    }
  },
  computed: {
    selectData() {
      return this.$store.state.resources.poolList.map(x => ({
        text: x.name,
        value: x.id,
        is_managed: x.is_managed
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
    addHypervisor() {
      const host = this.host
      host.pool = this.poolSelection
      axios.post(`${this.$store.state.endpoint.api}/api/v1/hosts`, { hostname: host.hostname, ip_address: this.host.ipaddress, pool_id: host.pool.value, tags: host.tags }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestHost", { token: this.$keycloak.token })
        this.$router.push('/admin/resources/hypervisors')
        this.$vaToast.init(({ title: response.data.state, message: "Hypervisor has been successfully added", color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          self.$vaToast.init(({ title: 'Unable to add hypervisor', message: error.response.data.detail, color: 'danger' }))
        }
      })
    }
  }
}
</script>

<style>

</style>