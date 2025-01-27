<template>
  <va-card>
    <va-card-title>
      <h1 v-if="policyId">Updating policy {{ statePolicy?.name ?? "" }}</h1>
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
          :options="dayOptions"
          v-model="selectedDays"
          multiple
          :rules="[(value) => value?.length > 0 || 'Field is required']"
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
          v-model="selectedStorage"
          :options="storageOptions"
          :rules="[(value) => value || 'Field is required']"
        >
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
        <va-divider class="divider">
          <span class="px-2"> DATA RETENTION </span>
        </va-divider>
        <va-slider v-model="retention.day" label="Daily" :max="365">
          <template #prepend>
            <va-input type="number" v-model.number="retention.day" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.week" label="Weekly" :max="52">
          <template #prepend>
            <va-input type="number" v-model.number="retention.week" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.month" label="Monthly" :max="12">
          <template #prepend>
            <va-input type="number" v-model.number="retention.month" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.year" label="Yearly" :max="5">
          <template #prepend>
            <va-input type="number" v-model.number="retention.year" readonly />
          </template>
        </va-slider>
        <va-divider class="divider">
          <span class="px-2"> NOTIFICATIONS </span>
        </va-divider>
        <va-select
          label="Select external hook"
          v-model="selectedExternalHook"
          :options="externalHookOptions"
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
import dayOfWeek from "./dayOfWeek";

export default {
  name: "updatePolicy",
  components: { ...spinners },
  data() {
    return {
      policyId: this.$route.params.id,
      formPolicy: {
        name: "",
        description: "",
      },
      dayOptions: dayOfWeek.week(),
      selectedDays: [],
      timeToBackup: new Date(new Date().setHours(0, 0, 0, 0)),
      selectedStorage: null,
      retention: {
        // TODO Provide nice defaults ?
        day: 0,
        week: 0,
        month: 0,
        year: 0,
      },
      selectedExternalHook: null,
    };
  },
  computed: {
    statePolicy() {
      return this.$store.state.resources.policyList.find(
        (item) => item.id == this.policyId
      );
    },
    storageOptions() {
      return this.$store.state.storageList.map((x) => ({
        text: x.name.toUpperCase(),
        value: x.id,
      }));
    },
    externalHookOptions() {
      return this.$store.state.resources.externalHookList.map((x) => ({
        text: x.name,
        value: x.id,
      }));
    },
  },
  watch: {
    statePolicy: function () {
      this.propagateStatePolicy();
    },
    storageOptions: function () {
      if (this.selectedStorage != null) {
        this.updateSelectedStorage(this.selectedStorage.value);
      }
    },
    externalHookOptions: function () {
      if (this.selectedExternalHook != null) {
        this.updateSelectedExternalHook(this.selectedExternalHook.value);
      }
    },
  },
  mounted() {
    if (this.statePolicy) {
      this.propagateStatePolicy();
    }
  },
  methods: {
    propagateStatePolicy() {
      this.formPolicy = { ...this.statePolicy };

      const parsedCron = JSON.parse(
        JSON.stringify(parser.parseExpression(this.statePolicy.schedule).fields)
      );
      this.timeToBackup = new Date(
        new Date().setHours(parsedCron.hour, parsedCron.minute, 0)
      );
      this.selectedDays = dayOfWeek.toNames(parsedCron.dayOfWeek);

      this.updateSelectedStorage(this.statePolicy.storage);

      // TODO Change retention to an object EVERYWHERE in Backroll ?
      // Then retention will be included in fromPolicy.
      this.retention = Object.fromEntries(
        Object.entries(this.statePolicy)
          .filter(([key]) => key.startsWith("retention_"))
          .map(([key, value]) => [key.replace("retention_", ""), value])
      );

      this.updateSelectedExternalHook(this.statePolicy.externalhook);
    },
    updateSelectedStorage(id) {
      this.selectedStorage = this.storageOptions.find(
        (item) => item.value == id
      );
    },
    updateSelectedExternalHook(id) {
      this.selectedExternalHook = this.externalHookOptions.find(
        (item) => item.value == id
      );
    },
    exportPolicy() {
      const policy = JSON.parse(JSON.stringify(this.formPolicy));

      policy.schedule = `${this.timeToBackup.getMinutes()} ${this.timeToBackup.getHours()} * * ${dayOfWeek.toSymbols(
        this.selectedDays
      )}`;

      policy.storage = this.selectedStorage?.value;

      policy.retention = this.retention;

      policy.externalhook = this.selectedExternalHook?.value;

      return policy;
    },
    updatePolicy() {
      this.$store.dispatch("updatePolicy", {
        vm: this,
        token: this.$keycloak.token,
        policyValues: this.exportPolicy(),
      });
    },
    addPolicy() {
      const self = this;
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/backup_policies`,
          this.exportPolicy(),
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
  },
};
</script>
<style scoped>
.divider {
  padding-top: 1%;
  padding-bottom: 1%;
}
</style>
