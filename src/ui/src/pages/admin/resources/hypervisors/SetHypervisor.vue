<template>
  <va-card >
    <va-card-title>
      <h1 v-if="hypervisor && $store.state.ishostTableReady">Update hypervisor {{ hypervisor.hostname }}</h1>
      <h1 v-if="!hypervisor || !$store.state.ishostTableReady">Adding new hypervisor</h1>
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
          :options="selectPoolData"
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
        tags: null
      },
      poolSelection: {}
    }
  },
  mounted () {
    if(this.hypervisor){
      this.host = {...this.hypervisor}
      this.updatePool(this.host.pool_id)
    }
    
  },
  watch: {
    hypervisor: function () {
      this.host = {...this.hypervisor}
      this.updatePool(this.host.pool_id)
    },
    validation: function () {
      if (this.validation) {
        if(this.hypervisor){
          this.updateHost();
        }else{
          this.addHypervisor();
        }
        
      }
    },
    selectPoolData: function () {
      if (this.host.pool !== null) {
        this.updatePool(this.host.pool)
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
        value: x.id,
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
    updateHost() {
      const hypervisor = this.host
      hypervisor.pool_id = this.poolSelection.value
      this.$store.dispatch("updateHost", {
        vm: this,
        token: this.$keycloak.token,
        hostValues: hypervisor
      })
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