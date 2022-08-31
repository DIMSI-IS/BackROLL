<template>
  <va-card>
    <va-card-title>
      <h1>Adding new external hook</h1>
    </va-card-title>
    <va-card-content>
      <va-alert
        color="info"
        icon="info"
        dense
      >
        For now, the only external hook provider supported is Slack
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
          label="Provider"
          v-model="inputValue2"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
          readonly
        />
        <br>
        <va-input
          v-model="inputValue3"
          :type="isPasswordVisible ? 'text' : 'password'"
          label="Value"
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
      inputValue2: 'slack',
      inputValue3: null,
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
      axios.post(`${this.$store.state.endpoint.api}/api/v1/externalhooks`, { name: this.inputValue1, provider: this.inputValue2, value: this.inputValue3 }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestExternalHook", { token: this.$keycloak.token })
        this.$router.push('/admin/configuration/externalhooks')
        this.$vaToast.init(({ title: response.data.state, message: "External hook has been successfully added", color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          self.$vaToast.init(({ title: 'Unable to add external hook', message: error.response.data.detail, color: 'danger' }))
        }
      })
    }
  }
}
</script>

<style>

</style>