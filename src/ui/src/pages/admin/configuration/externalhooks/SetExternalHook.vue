<template>
  <va-card >
    <va-card-title>
      <h1 v-if="hook && $store.state.isexternalHookTableReady">Updating external hook - {{ hook.name }}</h1>   
      <h1 v-if="!hook || !$store.state.isexternalHookTableReady">Adding new external hook</h1>
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
          v-model="updatedValues.name"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="Provider"
          v-model="updatedValues.provider"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
          readonly
        />
        <br>
        <va-input
          v-model="updatedValues.value"
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
      updatedValues: { 
        name: null,
        provider: "slack",
        value: null,
      }
    }
  },
  watch: {
    hook: function () {
      this.updatedValues = {...this.hook}
    },
    validation: function () {
      if (this.validation) {
        if(this.hook){
          this.updateHook()
        }else{
          this.addHook()
        }
      }
    },
  },
  computed: {
    hook () {
      const result = this.$store.state.resources.externalHookList.filter((item) => {
        return item.id == this.$route.params.id
      })
      console.log(result)
      return result[0]
    },
  },
  mounted () {
    if(this.hook){
      this.updatedValues = {...this.hook}
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
    updateHook() {
      const hook = this.updatedValues
      this.$store.dispatch("updateExternalHook", {
        vm: this,
        token: this.$keycloak.token,
        hookValues: hook
      })
    },
    addHook() {
      self = this;
      const hook = this.updatedValues;
      axios.post(`${this.$store.state.endpoint.api}/api/v1/externalhooks`, hook, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
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