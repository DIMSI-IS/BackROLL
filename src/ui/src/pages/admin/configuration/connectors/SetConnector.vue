<template>
  <va-card >
    <va-card-title>
      <h1 v-if="connector && $store.state.isconnectorTableReady">Updating connector {{ connector.name }}</h1>
      <h1 v-if="!connector || !$store.state.isconnectorTableReady">Adding new connector</h1>
    </va-card-title>
    <va-card-content>
      <va-alert
        color="info"
        icon="info"
        dense
      >
        For now, the only supported connector is Cloudstack
      </va-alert>
      <br>
      <va-form
        ref="form"
        @validation="validation = $event"
      >
        <va-input
          label="Name"
          v-model="updatedValues.name"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="Endpoint URL"
          v-model="updatedValues.url"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="Login"
          v-model="updatedValues.login"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          v-model="updatedValues.password"
          :type="isPasswordVisible ? 'text' : 'password'"
          label="Password"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
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
      isPasswordVisible: false,
      validation: false,
      updatedValues: { 
        name: null,
        url: null,
        login: null,
        password: null
      }
    }
  },
  watch: {
    connector: function () {
      this.updatedValues = {...this.connector}
    },
    validation: function () {
      if (this.validation) {
        if(this.connector){
          this.updateConnector();
        }else{
          this.addHook();
        }
      }
    },
  },
  computed: {
    connector () {
      const result = this.$store.state.resources.connectorList.filter((item) => {
        return item.id == this.$route.params.id
      })
      console.log(result)
      return result[0]
    },
  },
  mounted () {
    if(this.connector){
      this.updatedValues = {...this.connector}
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
    updateConnector() {
      const connector = this.updatedValues
      this.$store.dispatch("updateConnector", {
        vm: this,
        token: this.$keycloak.token,
        connectorValues: connector
      })
    },
    addHook() {
      self = this;
      const connector = this.updatedValues;
      axios.post(`${this.$store.state.endpoint.api}/api/v1/connectors`,connector, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestConnector", { token: this.$keycloak.token })
        this.$router.push('/admin/configuration/connectors')
        this.$vaToast.init(({ title: response.data.state, message: "Connector has been successfully added", color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          self.$vaToast.init(({ title: 'Unable to add connector', message: error.response.data.detail, color: 'danger' }))
        }
      })
    }
  }
}
</script>
<style>

</style>