<template>
  <va-card>
    <va-card-title>
      <ListHeader title="Hooks" plus-button-title="Add external hook"
        plus-button-route="/admin/configuration/externalhooks/new" />
    </va-card-title>
    <va-card-content>
      <va-data-table :items="hookList" :columns="columns">
        <template #cell(value)="{ value }">
          {{ value ? '***MASKED***' : '' }}
        </template>
        <template #cell(id)="{ value }">
          <va-button-group gradient :rounded="false">
            <va-button icon="play_arrow" @click="testHook(value)" />
            <va-button icon="settings" :to="`/admin/configuration/externalhooks/${value}`" />
            <va-button icon="delete" @click="selectedHookId = value, showDeleteModal = true" />
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
      You are about to remove external hook <b>{{ selectedHook.name }}</b>.
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
        { key: "id", label: "actions" }
      ],
      selectedHookId: null,
      showDeleteModal: false,
    }
  },
  computed: {
    hookList() {
      return this.$store.state.resources.externalHookList
    },
    selectedHook() {
      return this.hookList.find(({ id }) => id == this.selectedHookId)
    },
  },
  methods: {
    async testHook(id) {
      try {
        const response = await axios.get(`${this.$store.state.endpoint.api}/api/v1/externalhooks/${id}/test`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        this.$vaToast.init({ title: response.data.state, message: 'External hook has been successfully tested.', color: 'success' })
      } catch (error) {
        console.error(error)
        this.$vaToast.init({
          title: 'Unable to test external hook',
          message: error?.response?.data?.detail ?? error,
          color: 'danger'
        })
      }
    },
    deleteHook() {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/externalhooks/${this.selectedHookId}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
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
