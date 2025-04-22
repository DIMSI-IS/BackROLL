<template>
  <va-card>
    <va-card-title>
      <ListHeader title="Connectors" plus-button-title="Add connector"
        plus-button-route="/admin/configuration/connectors/new" />
    </va-card-title>
    <va-card-content>
      <va-data-table :items="$store.state.resources.connectorList" :columns="columns">
        <template #cell(name)="{ value }">
          {{ value }}
        </template>
        <template #cell(url)="{ value }">
          {{ value }}
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button icon="settings"
              @click="this.$router.push(`/admin/configuration/connectors/${$store.state.resources.connectorList[rowIndex].id}`)" />
            <va-button icon="delete"
              @click="selectedConnector = $store.state.resources.connectorList[rowIndex], showDeleteModal = !showDeleteModal" />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isexternalHookTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
  <va-modal v-model="showDeleteModal" @ok="deleteConnector()">
    <template #header>
      <h2>
        <va-icon name="warning" color="danger" />
        Removing connector
      </h2>
    </template>
    <hr>
    <div>
      You are about to remove connector <b>{{ JSON.parse(JSON.stringify(this.selectedConnector)).name }}</b>.
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
        { key: 'url' },
        { key: 'actions' }
      ],
      showDeleteModal: false,
      selectedConnector: null
    }
  },
  computed: {
  },
  methods: {
    deleteConnector() {
      const connector = { ...this.selectedConnector }
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/connectors/${connector.id}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestConnector", { token: this.$keycloak.token })
          this.$vaToast.init({ title: response.data.state, message: 'connector has been successfully removed', color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: 'Unable to remove connector',
            message: error?.message ?? error,
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
