<template>
  <va-card>
    <va-card-title>
      <ListHeader title="Hooks" plus-button-title="Add external hook"
        plus-button-route="/admin/configuration/externalhooks/new" />
    </va-card-title>
    <va-card-content>
      <va-data-table :items="$store.state.resources.externalHookList" :columns="columns">
        <template #cell(value)="{ value }">
          {{ value ? '***MASKED***' : '' }}
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button icon="settings"
              @click="this.$router.push(`/admin/configuration/externalhooks/${$store.state.resources.externalHookList[rowIndex].id}`)" />
            <va-button icon="delete"
              @click="selectedHook = $store.state.resources.externalHookList[rowIndex], showDeleteModal = !showDeleteModal" />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isexternalHookTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
  <va-modal v-model="showDeleteModal" @ok="deleteHook()">
    <template #header>
      <h2>
        <va-icon name="warning" color="danger" />
        Removing External hook
      </h2>
    </template>
    <hr>
    <div>
      You are about to remove external hook <b>{{ JSON.parse(JSON.stringify(this.selectedHook)).name }}</b>.
      <br>Please confirm action.
    </div>
  </va-modal>
</template>
<script>
import axios from 'axios'
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

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
        { key: 'value' },
        { key: 'actions' }
      ],
      showDeleteModal: false,
      selectedHook: null
    }
  },
  computed: {
  },
  methods: {
    deleteHook() {
      const hook = { ...this.selectedHook }
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/externalhooks/${hook.id}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestExternalHook", { token: this.$keycloak.token })
          this.$vaToast.init({ title: response.data.state, message: 'External hook has been successfully removed', color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: 'Unable to remove external hook',
            message: error?.response?.data?.detail ?? error,
            color: 'danger'
          })
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
