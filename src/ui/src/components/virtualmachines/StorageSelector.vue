<template>
  <va-select label="Storages" v-model="storageSelection" :options="selectData" :loading="this.loadingStorages">
    <template #prependInner>
      <va-icon name="today" size="small" color="primary" />
    </template>
  </va-select>
</template>
<script>
import { defineComponent } from 'vue'
import axios from 'axios'

export default defineComponent({
  name: 'StorageList',
  props: [],
  data() {
    return {
      loadingStorages: false,
      selectedStorage: null,
      storagesInfo: []
    }
  },
  watch: {
    storage: function () {
      this.requestStorages()
    }
  },
  mounted() {
    this.requestStoragesList()
  },
  computed: {
    selectData() {
      if (this.storagesInfo) {
        const result = this.storagesInfo.map(x => ({
          text: x.name,
          value: x.path
        }))
        return result.sort().reverse()
      }
      return [];
    },
  },
  methods: {
    getStorageList(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.getStorageList(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.storagesInfo = response.data.info
            this.loadingStorages = false
          } else if (response.data.state === 'FAILURE') {
            this.loadingStorages = false
            this.$vaToast.init(({ message: response.data.status, color: 'danger' }))
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    requestStoragesList() {
      const urlToCall = `${this.$store.state.endpoint.api}/api/v1/storage`;
      axios.get(urlToCall, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.loadingStorages = true
          this.getStorageList(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
  }
})
</script>