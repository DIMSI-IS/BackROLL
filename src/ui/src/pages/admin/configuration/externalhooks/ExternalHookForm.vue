<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          hookId
            ? $t('pages.configuration.externalHook.updating', { name: stateHook?.name ?? '' })
            : $t('pages.configuration.externalHook.adding')
        "
      />
    </va-card-title>
    <va-card-content v-if="!hookId || stateHook">
      <va-alert color="info" icon="info" dense>
        {{ $t('pages.configuration.externalHook.onlySlack') }}
      </va-alert>
      <br />
      <va-form ref="form">
        <va-input
          :label="$t('pages.configuration.common.name')"
          v-model="formHook.name"
          :rules="[
            (value) => value?.length > 0 || $t('pages.configuration.common.required'),
            (value) =>
              isHookNameUnique(value) || $t('pages.configuration.externalHook.nameUsed'),
          ]"
        />
        <br />
        <va-input
          :label="$t('pages.configuration.externalHook.provider')"
          v-model="formHook.provider"
          :rules="[(value) => value?.length > 0 || $t('pages.configuration.common.required')]"
          readonly
        />
        <br />
        <va-input
          v-model="formHook.value"
          :type="isPasswordVisible ? 'text' : 'password'"
          :label="$t('pages.configuration.externalHook.value')"
          :rules="[(value) => value?.length > 0 || $t('pages.configuration.common.required')]"
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
      <br />
      <va-button
        class="mb-3"
        @click="$refs.form.validate() && (hookId ? updateHook() : addHook())"
      >
        {{ hookId ? $t('pages.configuration.common.update') : $t('pages.configuration.common.add') }}
      </va-button>
    </va-card-content>
    <div v-else class="flex-center ma-3">
      <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
    </div>
  </va-card>
</template>

<script>
import axios from "axios";
import * as spinners from "epic-spinners";

import FormHeader from "@/components/forms/FormHeader.vue";
import { canonicalName } from "@/pages/admin/forms";

export default {
  components: {
    ...spinners,
    FormHeader,
  },
  data() {
    return {
      hookId: this.$route.params.id,
      formHook: {
        name: null,
        provider: "slack",
        value: null,
      },
      isPasswordVisible: false,
    };
  },
  computed: {
    stateHook() {
      return this.$store.state.resources.externalHookList.find(
        (item) => item.id == this.hookId
      );
    },
  },
  watch: {
    stateHook: function () {
      this.propagateStateHook();
    },
  },
  methods: {
    isHookNameUnique(value) {
      const canonical = canonicalName(value);
      return !this.$store.state.resources.externalHookList.find(
        ({ id, name }) => id != this.hookId && canonicalName(name) == canonical
      );
    },
    propagateStateHook() {
      this.formHook = { ...this.stateHook };
      // Other providers are not supported yet.
      this.formHook.provider = "slack";
    },
    updateHook() {
      this.$store.dispatch("updateExternalHook", {
        vm: this,
        hookValues: this.formHook,
      });
    },
    addHook() {
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/externalhooks`,
          this.formHook,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestExternalHook");
          this.$router.push("/admin/configuration/externalhooks");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.externalHook.added"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.externalHook.addFailed"),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
  mounted() {
    // TODO Wait ?
    this.$store.dispatch("requestExternalHook");
    if (this.stateHook) {
      this.propagateStateHook();
    }
  },
};
</script>
<style></style>
