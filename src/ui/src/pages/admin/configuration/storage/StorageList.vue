<template>
  <div>
    <va-card>
      <va-card-title>
        <ListHeader title="Storage" plus-button-title="Add storage"
          plus-button-route="/admin/configuration/storage/new" />
      </va-card-title>
      <va-card-content>
        <va-data-table :items="$store.state.storageList" :columns="columns">
          <template #header(info)>disk usage (%)</template>
          <template #cell(name)="{ value }">{{ value.toUpperCase() }}</template>
          <template #cell(info)="{ rowIndex }">
            <div v-if="$store.state.storageList[rowIndex].info">
              <va-chip size="small" outline square
                :color="(100 - (($store.state.storageList[rowIndex].info.free / $store.state.storageList[rowIndex].info.total) * 100)).toFixed(1) < 75 ? 'success' : 'danger'">
                <va-icon
                  v-if="(100 - (($store.state.storageList[rowIndex].info.free / $store.state.storageList[rowIndex].info.total) * 100)).toFixed(1) >= 75"
                  name="warning" color="danger" />
                <span style="margin-right: 2px;"><b>{{ (100 - (($store.state.storageList[rowIndex].info.free /
                  $store.state.storageList[rowIndex].info.total) * 100)).toFixed(1) }}%</b></span> ({{
                      humanStorageSize($store.state.storageList[rowIndex].info.free) }} free)
              </va-chip>
            </div>
            <div v-else>
              <va-chip size="small" outline square color="danger">
                <va-icon class="material-icons" color="danger">warning</va-icon>
                Unable to retrieve information
              </va-chip>
            </div>
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button icon="settings"
                @click="this.$router.push(`/admin/configuration/storage/${$store.state.storageList[rowIndex].id}`)" />
              <va-button icon="delete"
                @click="selectedStorage = $store.state.storageList[rowIndex], showDeleteModal = !showDeleteModal" />
            </va-button-group>
          </template>
          <template #cell(path)="{ value }"><va-chip size="small" outline square>{{ value }}</va-chip></template>
        </va-data-table>
        <div v-if="!$store.state.isstorageTableReady" class="flex-center ma-3">
          <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
        </div>
      </va-card-content>
    </va-card>
    <va-modal v-model="showDeleteModal" @ok="deleteStorage()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          Removing Storage
        </h2>
      </template>
      <hr>
      <div>
        You are about to remove storage <b>{{ JSON.parse(JSON.stringify(this.selectedStorage)).name }}</b>.
        <br>Please confirm action.
      </div>
    </va-modal>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'
import axios from 'axios'

import ListHeader from '@/components/lists/ListHeader.vue'

export default defineComponent({
  name: 'PoliciesTable',
  components: {
    ...spinners,
    ListHeader
  },
  data() {
    return {
      columns: [
        { key: 'name' },
        { key: 'path' },
        { key: 'info' },
        { key: 'actions' }
      ],
      showDeleteModal: false,
      selectedStorage: null
    }
  },
  computed: {
  },
  methods: {
    deleteStorage() {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/storage/${JSON.parse(JSON.stringify(this.selectedStorage)).id}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestStorage", { token: this.$keycloak.token })
          this.$vaToast.init({ title: response.data.state, message: 'Storage has been successfully removed', color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: 'Unable to remove storage',
            message: error?.response?.data?.detail ?? error,
            color: 'danger'
          })
        })
    },
    humanStorageSize(bytes, si = false, dp = 1) {
      const thresh = si ? 1000 : 1024;
      if (Math.abs(bytes) < thresh) {
        return bytes + ' B';
      }
      const units = si
        ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
      let u = -1;
      const r = 10 ** dp;
      do {
        bytes /= thresh;
        ++u;
      } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);
      return bytes.toFixed(dp) + ' ' + units[u];
    }
  }
})
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
