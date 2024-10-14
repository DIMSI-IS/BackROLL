<template>
  <va-card>
    <va-card-title>
      <h1 v-if="storageId">Updating storage {{ stateStorage.name ?? "" }}</h1>
      <h1 v-else>Adding new storage</h1>
    </va-card-title>
    <va-card-content v-if="!storageId || stateStorage">
      <va-form
        tag="form"
        @submit.prevent="storageId ? updateStorage() : addStorage()"
      >
        <va-input
          label="Name"
          v-model="formStorage.name"
          :rules="[(value) => value?.length > 0 || 'Field is required']"
        />
        <br />
        <va-input
          label="Path"
          placeholder="eg. /mnt/myNFSbackend"
          v-model="formStorage.path"
          :rules="[(value) => value?.length > 0 || 'Field is required']"
        />
        <br />
        <va-button class="mb-3" type="submit">
          {{ storageId ? "Update" : "Validate" }}
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

export default {
  name: "updateStorage",
  components: { ...spinners },
  data() {
    return {
      storageId: this.$route.params.id,
      formStorage: { name: null, path: null },
    };
  },
  computed: {
    stateStorage() {
      return this.$store.state.storageList.find(
        (item) => item.id == this.storageId
      );
    },
  },
  watch: {
    stateStorage: function () {
      propagateStorage();
    },
  },
  mounted() {
    if (this.stateStorage) {
      propagateStorage();
    }
  },
  methods: {
    propagateStateStorage() {
      this.formStorage = { ...this.stateStorage };
    },
    updateStorage() {
      const { id, name, path } = this.formStorage;
      this.$store.dispatch("updateStorage", {
        vm: this,
        token: this.$keycloak.token,
        storageId: id,
        name,
        path,
      });
    },
    addStorage() {
      const self = this;
      const { name, path } = this.formStorage;
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/storage`,
          { name, path },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$keycloak.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestStorage", {
            token: this.$keycloak.token,
          });
          this.$router.push("/admin/configuration/storage");
          this.$vaToast.init({
            title: response.data.state,
            message: "Storage has been successfully added",
            color: "success",
          });
        })
        .catch(function (error) {
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            // TODO error.message ?
            self.$vaToast.init({
              title: "Unable to add storage",
              message: error.response.data.detail,
              color: "danger",
            });
          }
        });
    },
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
