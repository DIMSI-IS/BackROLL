<template>
  <va-card>
    <va-card-title>
      <h1>Connectors</h1>
      <div class="mr-0 text-right">
        <va-button
          color="info"
          @click="this.$router.push('/admin/configuration/connectors/new')"
        >
          Add connector
        </va-button>
      </div>
    </va-card-title>
    <va-card-content>
      <va-data-table
        :items="$store.state.resources.connectorList"
        :columns="columns"
      >
        <template #cell(name)="{ value }">
          {{ value }}
        </template>
        <template #cell(url)="{ value }">
          {{ value }}
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button icon="settings" @click="this.$router.push(`/admin/configuration/connectors/${$store.state.resources.connectorList[rowIndex].id}`)" />
            <va-button icon="delete" @click="selectedConnector = $store.state.resources.connectorList[rowIndex], showDeleteModal = !showDeleteModal" />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isexternalHookTableReady" class="flex-center ma-3">
        <spring-spinner
          :animation-duration="2000"
          :size="30"
          color="#2c82e0"
        />
      </div>
    </va-card-content>
  </va-card>
  <va-modal
    v-model="showDeleteModal"
    @ok="deleteConnector()"
  >
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

export default defineComponent({
  name: 'PoliciesTable',
  components: { ...spinners },
  data () {
    return {
      columns: [
        { key: 'name'},
        { key: 'url'},
        { key: 'actions'}
      ],
      showDeleteModal: false,
      selectedConnector: null
    }
  },
  computed: {
  },
  methods: {
    deleteConnector () {
      const self = this
      const connector = {...this.selectedConnector}
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/connectors/${connector.id}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestConnector", { token: this.$keycloak.token })
        this.$vaToast.init(({ title: response.data.state, message: 'connector has been successfully removed', color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          console.log(error)
          self.$vaToast.init(({ title: 'Unable to remove connector', message: error.response.data.detail, color: 'danger' }))
        }
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
