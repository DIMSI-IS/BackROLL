<template>
  <va-card>
    <va-card-title>
      <h1>Adding new storage</h1>
    </va-card-title>
    <va-card-content>
      <va-alert border="top" class="mb-4">
        <template #icon>
          <va-icon name="info" />
        </template>
        The storage path must be accessible by the BackROLL workers containers.<br>
        To do this, update the following portion in the docker-compose:
        <code class="consoleStyle">
  volumes:<br>
  - /mnt:/mnt
</code>
        This example gives access to the /mnt directory where NFS shares dedicated to backup storage can be mounted.
      </va-alert>
      <va-form tag="form" @submit.prevent="addStorage">
        <va-input label="Name" v-model="storageName" :rules="storageNameRules" />
        <br>
        <va-input label="Path" placeholder="eg. /mnt/myNFSbackend/" v-model="storagePath"
          :rules="storagePathRules" />
        <br>
        <va-button class="mb-3" type="submit" :disabled="!isNameValid || !isPathValid">
          Validate
        </va-button>
      </va-form>
    </va-card-content>
  </va-card>
</template>

<script>
import axios from 'axios'
export default {
  data() {
    return {
      storageName: null,
      storagePath: null,
      storageNameRules: [
        value => value?.length > 0 || 'Field is required',
        value => !this.$store.state.storageList.find(s => s.name === value) || "This name is already used"
      ],
      storagePathRules: [
        value => value?.length > 0 || 'Field is required',
        value => value != '/mnt/' || 'The path can\'t only be /mnt/',
        value => /^\/mnt/gi.test(value) || 'The path must begin by /mnt',
        value => {
          value = value?.replace(/\/$/, "")
          return !this.$store.state.storageList.find(s => s.path.replace(/\/$/, "") === value) || 'A storage already exist for this path'
        }
      ],
    }
  },
  computed: {
    isNameValid() {
      return this.storageNameRules.map(rule => rule(this.storageName)).every(value => value === true)
    },
    isPathValid() {
      return this.storagePathRules.map(rule => rule(this.storagePath)).every(value => value === true)
    }
  },
  methods: {
    addStorage() {
      const self = this
      axios.post(`${this.$store.state.endpoint.api}/api/v1/storage`, { name: this.storageName, path: this.storagePath }, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestStorage", { token: this.$keycloak.token })
          this.$router.push('/admin/configuration/storage')
          this.$vaToast.init(({ title: response.data.state, message: "Storage has been successfully added", color: 'success' }))
        })
        .catch(function (error) {
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            self.$vaToast.init(({ title: 'Unable to add storage', message: error.response.data.detail, color: 'danger' }))
          }
        })
    }
  }
}
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
