<template>
  <va-card v-if="hook && $store.state.isexternalHookTableReady">
    <va-card-title>
      <h1>Updating external hook {{ hook.name }}</h1>
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
export default {
  data () {
    return {
      isPasswordVisible: false,
      validation: false,
      updatedValues: { 
        name: '',
        value: '',
        provider: 'slack'
      }
    }
  },
  watch: {
    hook: function () {
      this.updatedValues = {...this.hook}
    },
    validation: function () {
      if (this.validation) {
        this.updateHook()
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
    this.updatedValues = {...this.hook}
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
    }
  }
}
</script>
<style>

</style>