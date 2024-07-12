<template>
  <va-card v-if="storage">
    <va-card-title>
      <h1>Update storage {{ storage.name }}</h1>
    </va-card-title>
    <va-card-content>
      <va-form
        tag="form"
        @submit.prevent="updateStorage"
      >
        <va-input
          label="Name"
          v-model="updatedValues.name"
          :rules="[value => (value && value.length > 0) || 'Field is required']"
        />
        <br>
        <va-input
          label="Path"
          placeholder="eg. /mnt/myNFSbackend"
          v-model="updatedValues.path"
          :rules="[
          value => (value && value.length > 0) || 'Field is required',
          value => value != '/mnt/' || 'The path can\'t only be /mnt/', 
          value => /^\/mnt\/([a-zA-Z0-9_ -]+\/)+$/i.test(value) || 'The path must begin by /mnt and end with a /',
          value => !this.$store.state.storageList.find(s => s.path === value) || 'A storage already exist for this path'
          ]" />
        <br>
        <va-button
          class="mb-3"
          type="submit"
        >
          Update
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
import * as spinners from 'epic-spinners'

export default {
  name: 'updateStorage',
  components: { ...spinners },
  data () {
    return {
      updatedValues: {name: null, path: null}
    }
  },
  watch: {
    storage: function () {
      this.updatedValues = {...this.storage}
    }
  },
  computed: {
    storage () {
      const result = this.$store.state.storageList.filter((item) => {
        return item.id == this.$route.params.id
      })
      return result[0]
    }
  },
  mounted () {
    this.updatedValues = {...this.storage}
  },
  methods: {
    updateStorage() {
      const storage = this.updatedValues
      this.$store.dispatch("updateStorage", { vm: this, token: this.$keycloak.token, storageId: storage.id, name: storage.name, path: storage.path })
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
    border-radius:5px;
    max-height: 5%; width: auto;
  }
</style>