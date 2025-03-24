<template>
  <div>
    <va-card>
      <va-card-title>
        <h1>Policies</h1>
        <div class="mr-0 text-right">
          <va-button color="info" @click="this.$router.push('/admin/configuration/policies/new')"
            :disabled="!areDependenciesResolved">
            Create new policy
          </va-button>
        </div>
      </va-card-title>
      <va-card-content>
        <va-data-table :items="$store.state.resources.policyList" :columns="columns">
          <template #cell(schedule)="{ value }">
            <va-chip size="small" outline square>
              {{ humanCron(value) }}
            </va-chip>
          </template>
          <template #cell(externalhook)="{ value }">
            <va-chip @click="this.$router.push('/admin/configuration/externalhooks')" size="small" outline square>
              {{ value }}
            </va-chip>
          </template>
          <template #cell(enabled)="{ value }"><va-chip size="small" :color="JSON.parse(value) ? 'success' : 'danger'">
              {{ JSON.parse(value) ? 'Enabled' : 'Disabled' }}
            </va-chip>
          </template>
          <template #cell(storage)="{ value }">
            <va-chip size="small" square @click="this.$router.push('/admin/configuration/storage')">
              {{ getStorage(value) }}
            </va-chip>
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button v-if="JSON.parse($store.state.resources.policyList[rowIndex].enabled)" icon="block"
                @click="selectedPolicy = $store.state.resources.policyList[rowIndex], showDisableModal = !showDisableModal" />
              <va-button v-else icon="start" @click="enablePolicy($store.state.resources.policyList[rowIndex])" />
              <va-button icon="settings"
                @click="this.$router.push(`/admin/configuration/policy/${$store.state.resources.policyList[rowIndex].id}`)" />
              <va-button icon="delete"
                @click="selectedPolicy = $store.state.resources.policyList[rowIndex], showDeleteModal = !showDeleteModal" />
            </va-button-group>
          </template>
        </va-data-table>
        <div v-if="!$store.state.ispolicyTableReady" class="flex-center ma-3">
          <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
        </div>
      </va-card-content>
    </va-card>
    <va-modal v-model="showDisableModal" @ok="disablePolicy()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          Disabling Backup Policy
        </h2>
      </template>
      <hr>
      <div>
        You are about to disable policy <b>{{ JSON.parse(JSON.stringify(this.selectedPolicy)).name }}</b>.
        <br>Please confirm action.
      </div>
    </va-modal>
    <va-modal v-model="showDeleteModal" @ok="deletePolicy()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          Removing Backup Policy
        </h2>
      </template>
      <hr>
      <div>
        You are about to remove policy <b>{{ JSON.parse(JSON.stringify(this.selectedPolicy)).name }}</b>.
        <br>Please confirm action.
      </div>
    </va-modal>
  </div>
</template>

<script>
import axios from 'axios'
import { defineComponent } from 'vue'
import cronstrue from 'cronstrue'
import * as spinners from 'epic-spinners'

export default defineComponent({
  name: 'PoliciesTable',
  components: { ...spinners },
  data() {
    return {
      columns: [
        { key: 'name' },
        { key: 'schedule' },
        { key: 'storage' },
        { key: 'enabled', label: "auto-start" },
        { key: 'actions' }
      ],
      showDeleteModal: false,
      showDisableModal: false,
      selectedPolicy: null
    }
  },
  computed: {
    areDependenciesResolved() {
      return this.$store.state.storageList.length > 0;
    }
  },
  methods: {
    humanCron(value) {
      return cronstrue.toString(value)
    },
    getStorage(id) {
      if (this.$store.state.isstorageTableReady) {
        const result = this.$store.state.storageList.filter((item) => {
          return item.id == id
        })
        return result[0].name.toUpperCase()
      } else {
        return "loading..."
      }
    },
    deletePolicy() {
      const policy = { ...this.selectedPolicy }
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/backup_policies/${policy.id}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestPolicy", { token: this.$keycloak.token })
          this.$vaToast.init({ title: response.data.state, message: 'Policy has been successfully removed', color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: 'Unable to remove policy',
            message: error?.response?.data?.detail ?? error,
            color: 'danger'
          })
        })
    },
    disablePolicy() {
      const policy = { ...this.selectedPolicy }
      policy.state = 0
      this.$store.dispatch("updatePolicy", {
        vm: this,
        token: this.$keycloak.token,
        policyValues: policy,
      })
    },
    enablePolicy(object) {
      const policy = { ...object }
      policy.state = 1
      this.$store.dispatch("updatePolicy", {
        vm: this,
        token: this.$keycloak.token,
        policyValues: policy,
      })
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
