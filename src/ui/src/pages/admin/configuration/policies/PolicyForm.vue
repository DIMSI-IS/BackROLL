<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          policyId
            ? $t('pages.configuration.policy.updating', { name: statePolicy?.name ?? '' })
            : $t('pages.configuration.policy.creating')
        "
      />
    </va-card-title>
    <va-card-content v-if="!policyId || statePolicy">
      <va-form ref="form">
        <va-input
          :label="$t('pages.configuration.common.name')"
          v-model="formPolicy.name"
          :rules="[
            (value) => value?.length > 0 || $t('pages.configuration.common.required'),
            (value) =>
              isPolicyNameUnique(value) || $t('pages.configuration.policy.nameUsed'),
          ]"
        />
        <va-input
          class="mt-3"
          :label="$t('pages.configuration.policy.description')"
          v-model="formPolicy.description"
          :rules="[(value) => value?.length > 0 || $t('pages.configuration.common.required')]"
        />
        <va-divider class="divider">
          <span class="px-2"> {{ $t('pages.configuration.policy.sectionScheduling') }} </span>
        </va-divider>
        <va-select
          class="mb-4"
          :label="$t('pages.configuration.policy.days')"
          :options="dayOptions"
          v-model="selectedDayOptions"
          multiple
        >
          <template #prependInner>
            <va-icon name="event" size="small" color="primary" />
          </template>
        </va-select>
        <va-time-input
          v-model="timeToBackup"
          :label="$t('pages.configuration.policy.time')"
          ampm
          leftIcon
        />
        <va-divider class="divider">
          <span class="px-2"> {{ $t('pages.configuration.policy.sectionStorage') }} </span>
        </va-divider>
        <va-select
          :label="$t('pages.configuration.policy.selectStorage')"
          v-model="selectedStorage"
          :options="storageOptions"
          :rules="[(value) => value || $t('pages.configuration.common.required')]"
        >
          <template #prependInner>
            <va-icon name="storage" size="small" color="primary" />
          </template>
        </va-select>
        <va-divider class="divider">
          <span class="px-2"> {{ $t('pages.configuration.policy.sectionRetention') }} </span>
        </va-divider>
        <va-slider v-model="retention.day" :label="$t('pages.configuration.policy.daily')" :max="365">
          <template #prepend>
            <va-input type="number" v-model.number="retention.day" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.week" :label="$t('pages.configuration.policy.weekly')" :max="52">
          <template #prepend>
            <va-input type="number" v-model.number="retention.week" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.month" :label="$t('pages.configuration.policy.monthly')" :max="12">
          <template #prepend>
            <va-input type="number" v-model.number="retention.month" readonly />
          </template>
        </va-slider>
        <va-slider v-model="retention.year" :label="$t('pages.configuration.policy.yearly')" :max="5">
          <template #prepend>
            <va-input type="number" v-model.number="retention.year" readonly />
          </template>
        </va-slider>
        <va-divider class="divider">
          <span class="px-2"> {{ $t('pages.configuration.policy.sectionFiles') }} </span>
        </va-divider>
        <va-input
          type="textarea"
          v-model="filePathsText"
          :label="$t('pages.configuration.policy.filesLabel')"
          placeholder="/etc&#10;/var/www&#10;/home/user/documents"
          :min-rows="3"
          :max-rows="8"
          class="mb-2"
        />
        <p class="va-text-secondary mb-3">
          {{ $t('pages.configuration.policy.filesHelp') }}
        </p>
        <va-divider class="divider">
          <span class="px-2"> {{ $t('pages.configuration.policy.sectionNotifications') }} </span>
        </va-divider>
        <va-select
          :label="$t('pages.configuration.policy.selectHook')"
          v-model="selectedExternalHook"
          :options="externalHookOptions"
          clearable
        >
          <template #prependInner>
            <va-icon name="webhook" size="small" color="primary" />
          </template>
        </va-select>
        <br />
        <va-button
          class="mb-3"
          @click="
            $refs.form.validate() && (policyId ? updatePolicy() : addPolicy())
          "
        >
          {{ policyId ? $t('pages.configuration.common.update') : $t('pages.configuration.policy.create') }}
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
import cronParser from "cron-parser";
import * as spinners from "epic-spinners";

import FormHeader from "@/components/forms/FormHeader.vue";
import { canonicalName } from "@/pages/admin/forms";
import dayOfWeek from "./dayOfWeek";

export default {
  name: "updatePolicy",
  components: {
    ...spinners,
    FormHeader,
  },
  data() {
    return {
      policyId: this.$route.params.id,
      formPolicy: {
        name: "",
        description: "",
      },
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
      filePathsText: "",
    };
  },
  computed: {
    dayOptions() {
      // Displayed in the current language; the value stays the English name used to build the cron.
      return dayOfWeek.week().map((name) => ({
        text: this.$t(`pages.configuration.days.${name.toLowerCase()}`),
        value: name,
      }));
    },
    selectedDayOptions: {
      get() {
        return this.selectedDays
          .map((name) => this.dayOptions.find((option) => option.value == name))
          .filter((option) => option);
      },
      set(options) {
        this.selectedDays = options.map((option) => option.value ?? option);
      },
    },
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
    storageOptions: function (options, previous) {
      if (this.selectedStorage != null) {
        this.updateSelectedStorage(this.selectedStorage.value);
      } else if (this.statePolicy && !previous?.length && options.length) {
        // The page was opened directly: the policy came before the storages. Once they are known, the storage of
        // the policy is chosen (only the first time, so that a choice of the administrator is never undone).
        this.updateSelectedStorage(this.statePolicy.storage);
      }
    },
    externalHookOptions: function (options, previous) {
      if (this.selectedExternalHook != null) {
        this.updateSelectedExternalHook(this.selectedExternalHook.value);
      } else if (this.statePolicy && !previous?.length && options.length) {
        this.updateSelectedExternalHook(this.statePolicy.externalhook);
      }
    },
  },
  mounted() {
    if (this.statePolicy) {
      this.propagateStatePolicy();
    }
  },
  methods: {
    isPolicyNameUnique(value) {
      const canonical = canonicalName(value);
      return !this.$store.state.resources.policyList.find(
        ({ id, name }) =>
          id != this.policyId && canonicalName(name) == canonical
      );
    },
    propagateStatePolicy() {
      this.formPolicy = { ...this.statePolicy };

      // If the cron expression is corrupted, let the user fix it by catching the error.
      try {
        const parsedCron = JSON.parse(
          JSON.stringify(
            cronParser.parseExpression(this.statePolicy.schedule).fields
          )
        );
        this.timeToBackup = new Date(
          new Date().setHours(parsedCron.hour, parsedCron.minute, 0)
        );
        this.selectedDays = dayOfWeek.toNames(parsedCron.dayOfWeek);
      } catch {}

      this.updateSelectedStorage(this.statePolicy.storage);

      // TODO Change retention to an object EVERYWHERE in Backroll ?
      // Then retention will be included in formPolicy.
      this.retention = Object.fromEntries(
        Object.entries(this.statePolicy)
          .filter(([key]) => key.startsWith("retention_"))
          .map(([key, value]) => [key.replace("retention_", ""), value])
      );

      this.updateSelectedExternalHook(this.statePolicy.externalhook);
      this.filePathsText = this.statePolicy.file_paths || "";
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

      policy.schedule = `${this.timeToBackup.getMinutes()} ${this.timeToBackup.getHours()} * * ${dayOfWeek
        .toSymbols(this.selectedDays)
        .join(",")}`;
      if (this.selectedStorage) {
        policy.storage = this.selectedStorage.value;
      }
      policy.retention = this.retention;
      // The list of the policies gives the paths as one text, the API takes a list.
      policy.file_paths = this.filePathsText
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line);
      if (this.selectedExternalHook) {
        policy.externalhook = this.selectedExternalHook.value;
      } else if (this.externalHookOptions.length) {
        // The hooks are known and none is chosen: the administrator cleared it, the policy has no hook.
        policy.externalhook = null;
      }
      // Otherwise the hooks are not loaded yet: the policy keeps the one it has.

      return policy;
    },
    updatePolicy() {
      this.$store.dispatch("updatePolicy", {
        vm: this,
        policyValues: this.exportPolicy(),
      });
    },
    addPolicy() {
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/backup_policies`,
          this.exportPolicy(),
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestPolicy");
          this.$router.push("/admin/configuration/policies");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.policy.added"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.policy.addFailed"),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
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
