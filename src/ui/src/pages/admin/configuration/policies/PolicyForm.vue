<template>
  <va-card>
    <va-card-title>
      <h1 v-if="policyId">Updating policy {{ statePolicy.name ?? "" }}</h1>
      <h1 v-else>Adding new policy</h1>
    </va-card-title>
    <va-card-content v-if="!policyId || statePolicy">
      <va-form
        tag="form"
        @submit.prevent="policyId ? updatePolicy() : addPolicy()"
      >
        <va-input
          label="Name"
          v-model="formPolicy.name"
          :rules="[(value) => value?.length > 0 || 'Field is required']"
        />
        <va-input
          class="mt-3"
          label="Description"
          v-model="formPolicy.description"
          :rules="[(value) => value?.length > 0 || 'Field is required']"
        />
        <va-divider class="divider">
          <span class="px-2"> SCHEDULING </span>
        </va-divider>
        <va-select
          class="mb-4"
          label="Days on which the backup task must launch"
          :options="dayList"
          v-model="daySelection"
          multiple
        >
          <template #prependInner>
            <va-icon name="event" size="small" color="primary" />
          </template>
        </va-select>
        <va-time-input
          v-model="timeToBackup"
          label="At which time ?"
          ampm
          leftIcon
        />
        <va-divider class="divider">
          <span class="px-2"> STORAGE BACKEND </span>
        </va-divider>
        <va-select
          label="Select storage"
          v-model="storageSelection"
          :options="selectStorage"
          :rules="[(value) => isValid(value) || 'Field is required']"
        >
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
        <va-divider class="divider">
          <span class="px-2"> DATA RETENTION </span>
        </va-divider>
        <va-slider v-model="formPolicy.retention_day" label="Daily" :max="365">
          <template #prepend>
            <va-input
              type="number"
              v-model.number="formPolicy.retention_day"
              readonly
            />
          </template>
        </va-slider>
        <va-slider v-model="formPolicy.retention_week" label="Weekly" :max="52">
          <template #prepend>
            <va-input
              type="number"
              v-model.number="formPolicy.retention_week"
              readonly
            />
          </template>
        </va-slider>
        <va-slider
          v-model="formPolicy.retention_month"
          label="Monthly"
          :max="12"
        >
          <template #prepend>
            <va-input
              type="number"
              v-model.number="formPolicy.retention_month"
              readonly
            />
          </template>
        </va-slider>
        <va-slider v-model="formPolicy.retention_year" label="Yearly" :max="5">
          <template #prepend>
            <va-input
              type="number"
              v-model.number="formPolicy.retention_year"
              readonly
            />
          </template>
        </va-slider>
        <va-divider class="divider">
          <span class="px-2"> NOTIFICATIONS </span>
        </va-divider>
        <va-select
          label="Select external hook"
          v-model="formPolicy.externalhook"
          :options="selectExternalHook"
          clearable
        >
          <template #prependInner>
            <va-icon name="webhook" size="small" color="primary" />
          </template>
        </va-select>
        <!-- <va-input
          label="External hook"
          v-model="formPolicy.externalhook"
        >
          <template #prependInner>
            <va-icon
              name="webhook"
              size="small"
              color="primary"
            />
          </template>
        </va-input> -->
        <br />
        <va-button class="mb-3" type="submit">
          {{ policyId ? "Update" : "Validate" }}
        </va-button>
      </va-form>
    </va-card-content>
    <div v-else class="flex-center ma-3">
      <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
    </div>
  </va-card>
</template>
<script>
import axios from "axios";
import parser from "cron-parser";
import * as spinners from "epic-spinners";

export default {
  name: "updatePolicy",
  components: { ...spinners },
  data() {
    return {
      policyId: this.$route.params.id,
      formPolicy: {
        name: "",
        schedule: null,
        storage: null,
        externalhook: {},
        retention: {
          day: 0,
          week: 0,
          month: 0,
          year: 0,
        },
        id: null,
        description: "",
        enabled: null,
      },
      inputValue1: "",
      inputValue2: "",
      dayList: [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
      ],
      daySelection: [],
      timeToBackup: new Date(new Date().setHours(0, 0, 0, 0)),
      value: 1,
      storageSelection: {},
    };
  },
  computed: {
    statePolicy() {
      return this.$store.state.resources.policyList.find(
        (item) => item.id == this.policyId
      );
    },
    selectStorage() {
      return this.$store.state.storageList.map((x) => ({
        text: x.name.toUpperCase(),
        value: x.id,
      }));
    },
    selectExternalHook() {
      return this.$store.state.resources.externalHookList.map((x) => ({
        text: x.name,
        value: x.id,
      }));
    },
  },
  watch: {
    statePolicy: function () {
      this.formPolicy = { ...this.statePolicy };
    },
    formPolicy: function () {
      if (this.formPolicy.schedule) {
        this.parseCron(this.formPolicy.schedule);
      }
      if (this.formPolicy.retention) {
        this.parseRetention(this.formPolicy.retention);
      }
    },
    selectStorage: function () {
      if (this.formPolicy.storage !== null) {
        this.updateStorage(this.formPolicy.storage);
      }
    },
    selectExternalHook: function () {
      if (this.formPolicy.externalhook !== null) {
        this.updateExternalHook(this.formPolicy.externalhook);
      }
    },
  },
  mounted() {
    if (this.statePolicy) {
      this.formPolicy = { ...this.statePolicy };
      this.updateStorage(this.formPolicy.storage);
      this.updateExternalHook(this.formPolicy.externalhook);
      if (this.formPolicy.schedule) {
        this.parseCron(this.formPolicy.schedule);
      }
      if (this.formPolicy.retention) {
        this.parseRetention(this.formPolicy.retention);
      }
    }
  },
  methods: {
    isValid(value) {
      if (Object.keys(value).length < 1) {
        return false;
      } else {
        return true;
      }
    },
    updateStorage(id) {
      this.storageSelection = this.selectStorage.find(
        (item) => item.value == id
      );
    },
    updateExternalHook(id) {
      this.formPolicy.externalhook = this.selectExternalHook.find(
        (item) => item.value == id
      );
    },
    updatePolicy() {
      const policy = this.formPolicy;
      policy.storage = this.storageSelection;
      let daySchedule = [];
      // Handle every day wildcard '*'
      if (
        this.daySelection.includes("Monday") &&
        this.daySelection.includes("Tuesday") &&
        this.daySelection.includes("Wednesday") &&
        this.daySelection.includes("Thursday") &&
        this.daySelection.includes("Friday") &&
        this.daySelection.includes("Saturday") &&
        this.daySelection.includes("Sunday")
      ) {
        daySchedule.push("*");
      } else {
        if (this.daySelection.includes("Monday")) {
          daySchedule.push(1);
        }
        if (this.daySelection.includes("Tuesday")) {
          daySchedule.push(2);
        }
        if (this.daySelection.includes("Wednesday")) {
          daySchedule.push(3);
        }
        if (this.daySelection.includes("Thursday")) {
          daySchedule.push(4);
        }
        if (this.daySelection.includes("Friday")) {
          daySchedule.push(5);
        }
        if (this.daySelection.includes("Saturday")) {
          daySchedule.push(6);
        }
        if (this.daySelection.includes("Sunday")) {
          daySchedule.push(0);
          daySchedule.push(7);
        }
        daySchedule = daySchedule.sort();
      }
      const newSchedule = `${this.timeToBackup.getMinutes()} ${this.timeToBackup.getHours()} * * ${daySchedule}`;
      policy.schedule = newSchedule;

      const externalhook = this.formPolicy.externalhook?.value;
      policy.externalhook = externalhook?.length > 0 ? externalhook : null;

      policy.retention = {
        day: this.formPolicy.retention_day,
        week: this.formPolicy.retention_week,
        month: this.formPolicy.retention_month,
        year: this.formPolicy.retention_year,
      };

      this.$store.dispatch("updatePolicy", {
        vm: this,
        token: this.$keycloak.token,
        policyValues: policy,
      });
    },
    addPolicy() {
      const self = this;
      const policy = this.formPolicy;
      policy.storage = this.storageSelection;
      let daySchedule = [];
      // Handle every day wildcard '*'
      if (
        this.daySelection.includes("Monday") &&
        this.daySelection.includes("Tuesday") &&
        this.daySelection.includes("Wednesday") &&
        this.daySelection.includes("Thursday") &&
        this.daySelection.includes("Friday") &&
        this.daySelection.includes("Saturday") &&
        this.daySelection.includes("Sunday")
      ) {
        daySchedule.push("*");
      } else {
        if (this.daySelection.includes("Monday")) {
          daySchedule.push(1);
        }
        if (this.daySelection.includes("Tuesday")) {
          daySchedule.push(2);
        }
        if (this.daySelection.includes("Wednesday")) {
          daySchedule.push(3);
        }
        if (this.daySelection.includes("Thursday")) {
          daySchedule.push(4);
        }
        if (this.daySelection.includes("Friday")) {
          daySchedule.push(5);
        }
        if (this.daySelection.includes("Saturday")) {
          daySchedule.push(6);
        }
        if (this.daySelection.includes("Sunday")) {
          daySchedule.push(0);
          daySchedule.push(7);
        }
        daySchedule = daySchedule.sort();
      }
      const newSchedule = `${this.timeToBackup.getMinutes()} ${this.timeToBackup.getHours()} * * ${daySchedule}`;
      policy.schedule = newSchedule;

      const externalhook = this.formPolicy.externalhook?.value;
      policy.externalhook = externalhook?.length > 0 ? externalhook : null;
      policy.retention = {
        day: this.formPolicy.retention_day,
        week: this.formPolicy.retention_week,
        month: this.formPolicy.retention_month,
        year: this.formPolicy.retention_year,
      };
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/backup_policies`,
          policy,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$keycloak.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestPolicy", {
            token: this.$keycloak.token,
          });
          this.$router.push("/admin/configuration/policies");
          this.$vaToast.init({
            title: response.data.state,
            message: "Backup policy has been successfully added",
            color: "success",
          });
        })
        .catch(function (error) {
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            self.$vaToast.init({
              title: "Unable to add backup policy",
              message: error.response.data.detail,
              color: "danger",
            });
          }
        });
    },
    parseCron(cron) {
      const interval = parser.parseExpression(cron);
      const fields = JSON.parse(JSON.stringify(interval.fields));
      this.timeToBackup = new Date(
        new Date().setHours(fields.hour, fields.minute, 0)
      );
      const newDaySchedule = [];
      if (fields.dayOfWeek.includes(1)) {
        newDaySchedule.push("Monday");
      }
      if (fields.dayOfWeek.includes(2)) {
        newDaySchedule.push("Tuesday");
      }
      if (fields.dayOfWeek.includes(3)) {
        newDaySchedule.push("Wednesday");
      }
      if (fields.dayOfWeek.includes(4)) {
        newDaySchedule.push("Thursday");
      }
      if (fields.dayOfWeek.includes(5)) {
        newDaySchedule.push("Friday");
      }
      if (fields.dayOfWeek.includes(6)) {
        newDaySchedule.push("Saturday");
      }
      if (fields.dayOfWeek.includes(0) || fields.dayOfWeek.includes(7)) {
        newDaySchedule.push("Sunday");
      }
      this.daySelection = newDaySchedule;
    },
  },
};
</script>
<style scoped>
.divider {
  padding-top: 1%;
  padding-bottom: 1%;
}
</style>
