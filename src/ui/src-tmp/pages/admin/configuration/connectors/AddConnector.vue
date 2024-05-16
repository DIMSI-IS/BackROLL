<template>
  <va-card>
    <va-card-title>
      <h1>Adding new connector</h1>
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
          v-model="inputValue1"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="Endpoint URL"
          v-model="inputValue2"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="API Key"
          v-model="inputValue3"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          v-model="inputValue4"
          :type="isPasswordVisible ? 'text' : 'password'"
          label="API Secret"
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
      inputValue1: null,
      inputValue2: null,
      inputValue3: null,
      inputValue4: null,
    }
  },
  watch: {
    validation: function () {
      if (this.validation) {
        this.addHook()
      }
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
    addHook() {
      axios.post(`${this.$store.state.endpoint.api}/api/v1/connectors`, { name: this.inputValue1, url: this.inputValue2, login: this.inputValue3, password: this.inputValue3 }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
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