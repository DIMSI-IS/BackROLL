<template>
  <va-card>
    <va-card-title>
      <h1>Adding new policy</h1>
    </va-card-title>
    <va-card-content>
      <va-form
        ref="form"
        @validation="validation = $event"
      >
        <va-input
          label="Name"
          v-model="inputValue1"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <va-input
          class="mt-3"
          label="Description"
          v-model="inputValue2"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <va-divider class="divider">
          <span class="px-2">
            SCHEDULING
          </span>
        </va-divider>
        <va-select
          class="mb-4"
          label="Days on which the backup task must launch"
          :options="dayList"
          v-model="daySelection"
          multiple
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        >
          <template #prependInner>
            <va-icon
              name="event"
              size="small"
              color="primary"
            />
          </template>
        </va-select>
        <va-time-input
          v-model="timeToBackup"
          label="At which time ?"
          ampm
          leftIcon
        />
        <va-divider class="divider">
          <span class="px-2">
            STORAGE BACKEND
          </span>
        </va-divider>
        <va-select
          label="Select storage"
          v-model="storageSelection"
          :options="selectStorage"
          :rules="[value => isValid(value) || 'Field is required']"
        >
          <template #prependInner>
            <va-icon
              name="storage"
              size="small"
              color="primary"
            />
          </template>
        </va-select>
        <va-divider class="divider">
          <span class="px-2">
            DATA RETENTION
          </span>
        </va-divider>
        <va-slider v-model="dailyRetention" label="Daily" :max="365">
          <template #prepend>
            <va-input type="number" v-model.number="dailyRetention" readonly />
          </template>
        </va-slider>
        <va-slider v-model="weeklyRetention" label="Weekly" :max="52">
          <template #prepend>
            <va-input type="number" v-model.number="weeklyRetention" readonly />
          </template>
        </va-slider>
        <va-slider v-model="monthlyRetention" label="Monthly" :max="12">
          <template #prepend>
            <va-input type="number" v-model.number="monthlyRetention" readonly />
          </template>
        </va-slider>
        <va-slider v-model="yearlyRetention" label="Yearly" :max="5">
          <template #prepend>
            <va-input type="number" v-model.number="yearlyRetention" readonly />
          </template>
        </va-slider>
        <va-divider class="divider">
          <span class="px-2">
            NOTIFICATIONS
          </span>
        </va-divider>
        <va-select
          label="Select external hook"
          v-model="externalhook"
          :options="selectExternalHook"
          clearable
        >
          <template #prependInner>
            <va-icon
              name="webhook"
              size="small"
              color="primary"
            />
          </template>
        </va-select>
        <!-- <va-input
          label="External hook"
          v-model="externalhook"
        >
          <template #prependInner>
            <va-icon
              name="webhook"
              size="small"
              color="primary"
            />
          </template>
        </va-input> -->
        <br>
        <va-button
          class="mb-3"
          @click="$refs.form.validate()"
        >
          Validate
        </va-button>
      </va-form>
    </va-card-content>
  </va-card>
</template>
<script>
import axios from 'axios'
export default {
  data () {
    return {
      inputValue1: null,
      inputValue2: null,
      dayList: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      daySelection: [],
      timeToBackup: new Date(new Date().setHours(0,0,0,0)),
      value: 1,
      validation: false,

      storageSelection: {},

      dailyRetention: 1,
      weeklyRetention: 1,
      monthlyRetention: 1,
      yearlyRetention: 1,

      externalhook: ''
    }
  },
  computed: {
    selectStorage() {
      return this.$store.state.storageList.map(x => ({
        text: x.name,
        value: x.id
      }))
    },
    selectExternalHook() {
      return this.$store.state.resources.externalHookList.map(x => ({
        text: x.name,
        value: x.id
      }))
    },
    newRetention() {
      return {
        day: this.dailyRetention,
        week: this.weeklyRetention,
        month: this.monthlyRetention,
        year: this.yearlyRetention
      }
    }
  },
  watch: {
    validation: function () {
      if (this.validation) {
        this.addBackupPolicy()
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
    addBackupPolicy() {
      const self = this

      let daySchedule = []
      // Handle every day wildcard '*'
      if (
        this.daySelection.includes('Monday') &&
        this.daySelection.includes('Tuesday') &&
        this.daySelection.includes('Wednesday') &&
        this.daySelection.includes('Thursday') &&
        this.daySelection.includes('Friday') &&
        this.daySelection.includes('Saturday') &&
        this.daySelection.includes('Sunday')
      ) {
        daySchedule.push('*')
      } else {
        if (this.daySelection.includes('Monday')) {
          daySchedule.push(1)
        }
        if (this.daySelection.includes('Tuesday')) {
          daySchedule.push(2)
        }
        if (this.daySelection.includes('Wednesday')) {
          daySchedule.push(3)
        }
        if (this.daySelection.includes('Thursday')) {
          daySchedule.push(4)
        }
        if (this.daySelection.includes('Friday')) {
          daySchedule.push(5)
        }
        if (this.daySelection.includes('Saturday')) {
          daySchedule.push(6)
        }
        if (this.daySelection.includes('Sunday')) {
          daySchedule.push(0)
          daySchedule.push(7)
        }
        daySchedule = daySchedule.sort()
      }
      const newSchedule = `${this.timeToBackup.getMinutes()} ${this.timeToBackup.getHours()} * * ${daySchedule}`

      axios.post(`${this.$store.state.endpoint.api}/api/v1/backup_policies`, { name: this.inputValue1, description: this.inputValue2, retention: this.newRetention, schedule: newSchedule, storage: this.storageSelection.value, externalhook: this.externalhook.id }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestPolicy", { token: this.$keycloak.token })
        this.$router.push('/admin/configuration/policies')
        this.$vaToast.init(({ title: response.data.state, message: "Backup policy has been successfully added", color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          self.$vaToast.init(({ title: 'Unable to add backup policy', message: error.response.data.detail, color: 'danger' }))
        }
      })
    }
  }
}
</script>
<style scoped>
 .divider {
  padding-top: 1%;
  padding-bottom: 1%;
 }
</style>
