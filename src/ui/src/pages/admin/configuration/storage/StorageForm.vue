<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          storageId
            ? $t('pages.configuration.storage.updating', { name: stateStorage?.name ?? '' })
            : $t('pages.configuration.storage.adding')
        "
      />
    </va-card-title>
    <va-card-content v-if="!storageId || stateStorage">
      <va-alert border="top" class="mb-4">
        <template #icon>
          <va-icon name="info" />
        </template>
        {{ $t('pages.configuration.storage.pathHelp1') }}<br />
        {{ $t('pages.configuration.storage.pathHelp2') }}
        <code class="consoleStyle">
          volumes:<br />
          - /mnt:/mnt
        </code>
        {{ $t('pages.configuration.storage.pathHelp3') }}
      </va-alert>
      <va-form ref="form">
        <va-input
          :label="$t('pages.configuration.common.name')"
          v-model="formStorage.name"
          :rules="[
            (value) => value?.length > 0 || $t('pages.configuration.common.required'),
            (value) =>
              isStorageNameUnique(value) || $t('pages.configuration.storage.nameUsed'),
          ]"
        />
        <br />
        <va-input
          :label="$t('pages.configuration.storage.path')"
          :placeholder="$t('pages.configuration.storage.pathPlaceholder')"
          v-model="formStorage.path"
          :rules="[
            (value) => value?.length > 0 || $t('pages.configuration.common.required'),
            (value) =>
              removeTrailingSlash(value) != '/mnt' ||
              $t('pages.configuration.storage.pathNotMnt'),
            (value) => /^\/mnt/gi.test(value) || $t('pages.configuration.storage.pathMustMnt'),
            (value) =>
              isStoragePathUnique(value) ||
              $t('pages.configuration.storage.pathUsed'),
          ]"
        />
        <br />
        <va-button
          class="mb-3"
          @click="
            $refs.form.validate() &&
              (storageId ? updateStorage() : addStorage())
          "
        >
          {{ storageId ? $t('pages.configuration.common.update') : $t('pages.configuration.common.add') }}
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
import * as spinners from "epic-spinners";

import FormHeader from "@/components/forms/FormHeader.vue";
import { canonicalName } from "@/pages/admin/forms";

export default {
  name: "updateStorage",
  components: {
    ...spinners,
    FormHeader,
  },
  data() {
    return {
      storageId: this.$route.params.id,
      formStorage: {
        name: null,
        path: null,
      },
    };
  },
  computed: {
    stateStorage() {
      return this.$store.state.storageList.find((e) => e.id == this.storageId);
    },
  },
  watch: {
    stateStorage: function () {
      this.propagateStateStorage();
    },
  },
  methods: {
    removeTrailingSlash(path) {
      return path?.replace(/\/$/, "");
    },
    isStorageNameUnique(value) {
      const canonical = canonicalName(value);
      return !this.$store.state.storageList.find(
        ({ id, name }) =>
          id != this.storageId && canonicalName(name) == canonical
      );
    },
    isStoragePathUnique(value) {
      const trimmed = this.removeTrailingSlash(value);
      return !this.$store.state.storageList.find(
        ({ id, path }) =>
          id != this.storageId && this.removeTrailingSlash(path) == trimmed
      );
    },
    propagateStateStorage() {
      this.formStorage = { ...this.stateStorage };
    },
    updateStorage() {
      const { id, name, path } = this.formStorage;
      this.$store.dispatch("updateStorage", {
        vm: this,
        storageId: id,
        name,
        path,
      });
    },
    addStorage() {
      const { name, path } = this.formStorage;
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/storage`,
          { name, path },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestStorage");
          this.$router.push("/admin/configuration/storage");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t("pages.configuration.storage.added"),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t("pages.configuration.storage.addFailed"),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
  mounted() {
    // TODO Wait for the refreshed data ?
    this.$store.dispatch("requestStorage");
    if (this.stateStorage) {
      this.propagateStateStorage();
    }
  },
};
</script>

<style>
.consoleStyle {
  margin: 15px;
  padding: 5px;
  background: black;
  color: silver;
  font-size: 1em;
  border-radius: 5px;
  max-height: 5%;
  width: auto;
}
</style>
