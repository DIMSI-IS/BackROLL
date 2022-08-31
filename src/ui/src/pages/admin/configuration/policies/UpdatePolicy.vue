<template>
  <va-card v-if="policy && $store.state.isstorageTableReady">
    <va-card-title>
      <h1>Updating policy {{ policy.name }}</h1>
    </va-card-title>
    <va-card-content>
      <va-form
        tag="form"
        @submit.prevent="updateBackupPolicy"
      >
        <va-input
          label="Name"
          v-model="updatedValues.name"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <va-input
          class="mt-3"
          label="Description"
          v-model="updatedValues.description"
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
        <va-slider v-model="updatedValues.retention_day" label="Daily" :max="365">
          <template #prepend>
            <va-input type="number" v-model.number="updatedValues.retention_day" readonly />
          </template>
        </va-slider>
        <va-slider v-model="updatedValues.retention_week" label="Weekly" :max="52">
          <template #prepend>
            <va-input type="number" v-model.number="updatedValues.retention_week" readonly />
          </template>
        </va-slider>
        <va-slider v-model="updatedValues.retention_month" label="Monthly" :max="12">
          <template #prepend>
            <va-input type="number" v-model.number="updatedValues.retention_month" readonly />
          </template>
        </va-slider>
        <va-slider v-model="updatedValues.retention_year" label="Yearly" :max="5">
          <template #prepend>
            <va-input type="number" v-model.number="updatedValues.retention_year" readonly />
          </template>
        </va-slider>
        <va-divider class="divider">
          <span class="px-2">
            NOTIFICATIONS
          </span>
        </va-divider>
        <va-select
          label="Select external hook"
          v-model="updatedValues.externalhook"
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
          v-model="updatedValues.externalhook"
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
          type="submit"
        >
          Validate
        </va-button>
      </va-form>
    </va-card-content>
  </va-card>
  <div v-else class="flex-center ma-3">
    <spring-spinner
      :animation-duration="2000"
      :size="30"
      color="#2c82e0"
    />
  </div>
</template>
<script>
import parser from 'cron-parser'
import * as spinners from 'epic-spinners'
export default {
  name: 'updatePolicy',
  components: { ...spinners },
  data () {
    return {
      inputValue1: '',
      inputValue2: '',
      dayList: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      daySelection: [],
      timeToBackup: new Date(new Date().setHours(0,0,0,0)),
      value: 1,
      storageSelection: null,
      updatedValues: { 
        name: '',
        schedule: null,
        storage: null,
        externalhook: null,
        retention: {
          day: 0,
          week: 0,
          month: 0,
          year: 0
        },
        id: null,
        description: '',
        enabled: null
      }
    }
  },
  computed: {
    policy () {
      const result = this.$store.state.resources.policyList.filter((item) => {
        return item.id == this.$route.params.id
      })
      return result[0]
    },
    selectStorage() {
      return this.$store.state.storageList.map(x => ({
        text: x.name.toUpperCase(),
        value: x.id
      }))
    },
    selectExternalHook() {
      return this.$store.state.resources.externalHookList.map(x => ({
        text: x.name,
        value: x.id
      }))
    }
  },
  watch: {
    policy: function () {
      this.updatedValues = {...this.policy}
    },
    updatedValues: function () {
      if (this.updatedValues.schedule) {
        this.parseCron(this.updatedValues.schedule)
      }
      if (this.updatedValues.retention) {
        this.parseRetention(this.updatedValues.retention)
      }
    },
    selectStorage: function () {
      if (this.updatedValues.storage !== null) {
        this.updateStorage(this.updatedValues.storage)
      }
    },
    selectExternalHook: function () {
      if (this.updatedValues.externalhook !== null) {
        this.updateExternalHook(this.updatedValues.externalhook)
      }
    }
  },
  mounted () {
    this.updatedValues = {...this.policy}
    this.updateStorage(this.updatedValues.storage)
    this.updateExternalHook(this.updatedValues.externalhook)
    if (this.updatedValues.schedule) {
      this.parseCron(this.updatedValues.schedule)
    }
    if (this.updatedValues.retention) {
      this.parseRetention(this.updatedValues.retention)
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
    updateStorage(id) {
      const result = this.selectStorage.filter((item) => {
        return item.value == id
      })
      this.storageSelection = result[0]
    },
    updateExternalHook(id) {
      const result = this.selectExternalHook.filter((item) => {
        return item.value == id
      })
      this.updatedValues.externalhook = result[0]
    },
    updateBackupPolicy() {
      const policy = this.updatedValues
      policy.storage = this.storageSelection
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
      policy.schedule = newSchedule
      policy.externalhook = this.updatedValues.externalhook.value
      policy.retention = {
        day: this.updatedValues.retention_day,
        week: this.updatedValues.retention_week,
        month: this.updatedValues.retention_month,
        year: this.updatedValues.retention_year,
      }

      this.$store.dispatch("updatePolicy", {
        vm: this,
        token: this.$keycloak.token,
        policyValues: policy
      })
    },
    parseCron(cron) {
      const interval = parser.parseExpression(cron)
      const fields = JSON.parse(JSON.stringify(interval.fields))
      this.timeToBackup = new Date(new Date().setHours(fields.hour,fields.minute,0))
      const newDaySchedule = []
      if (fields.dayOfWeek.includes(1)) {
        newDaySchedule.push('Monday')
      }
      if (fields.dayOfWeek.includes(2)) {
        newDaySchedule.push('Tuesday')
      }
      if (fields.dayOfWeek.includes(3)) {
        newDaySchedule.push('Wednesday')
      }
      if (fields.dayOfWeek.includes(4)) {
        newDaySchedule.push('Thursday')
      }
      if (fields.dayOfWeek.includes(5)) {
        newDaySchedule.push('Friday')
      }
      if (fields.dayOfWeek.includes(6)) {
        newDaySchedule.push('Saturday')
      }
      if (fields.dayOfWeek.includes(0) || fields.dayOfWeek.includes(7)) {
        newDaySchedule.push('Sunday')
      }
      this.daySelection = newDaySchedule
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
