<template>
  <va-card v-if="connector && $store.state.isconnectorTableReady">
    <va-card-title>
      <h1>Updating connector {{ connector.name }}</h1>
    </va-card-title>
    <va-card-content>
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
export default {
  data () {
    return {
      isPasswordVisible: false,
      validation: false,
      updatedValues: { 
        name: '',
        url: '',
        login: '',
        password: ''
      }
    }
  },
  watch: {
    connector: function () {
      this.updatedValues = {...this.connector}
    },
    validation: function () {
      if (this.validation) {
        this.updateConnector()
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
    this.updatedValues = {...this.connector}
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
    }
  }
}
</script>
<style>

</style>