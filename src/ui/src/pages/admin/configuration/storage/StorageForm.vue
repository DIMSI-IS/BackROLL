<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          storageId
            ? `Updating storage ${stateStorage?.name ?? ''}`
            : 'Adding storage'
        "
      />
    </va-card-title>
    <va-card-content v-if="!storageId || stateStorage">
      <va-alert border="top" class="mb-4">
        <template #icon>
          <va-icon name="info" />
        </template>
        The storage path must be accessible by the BackROLL workers
        containers.<br />
        To do this, update the following portion in the docker-compose:
        <code class="consoleStyle">
          volumes:<br />
          - /mnt:/mnt
        </code>
        This example gives access to the /mnt directory where NFS shares
        dedicated to backup storage can be mounted.
      </va-alert>
      <va-form ref="form">
        <va-input
          label="Name"
          v-model="formStorage.name"
          :rules="[
            (value) => value?.length > 0 || 'Field is required',
            (value) =>
              isStorageNameUnique(value) || 'This name is already used',
          ]"
        />
        <br />
        <va-input
          label="Path"
          placeholder="eg. /mnt/myNFSbackend"
          v-model="formStorage.path"
          :rules="[
            (value) => value?.length > 0 || 'Field is required',
            (value) =>
              removeTrailingSlash(value) != '/mnt' ||
              'The path can’t only be /mnt or /mnt/',
            (value) => /^\/mnt/gi.test(value) || 'The path must begin by /mnt',
            (value) =>
              isStoragePathUnique(value) ||
              'A storage already exist for this path',
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
          {{ storageId ? "Update" : "Add" }}
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
            message: "Storage has been successfully added",
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: "Unable to add storage",
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
