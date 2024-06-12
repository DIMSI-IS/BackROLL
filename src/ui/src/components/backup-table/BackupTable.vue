<template>
  <div>
    <va-data-table
      :items="data"
      :columns="columns"
      :per-page="perPage"
      :current-page="currentPage"
    >
      <template #cell(started)="{ value }">
        <va-chip v-if="value" size="small" square outline color="primary">
          {{ (new Date(value * 1000)).toLocaleTimeString() }}
        </va-chip>
        <div v-else>
          <b>N/A</b>
        </div>
      </template>
      <template #cell(target)="{ value }">
        <div>
          <va-chip size="small" square color="primary">
            {{ value }}
          </va-chip>
        </div>
      </template>
      <template #cell(runtime)="{ rowIndex }">
        <div v-if="data[rowIndex].state == 'STARTED'">
          <va-chip size="small" color="info">
            <va-icon name="loop" spin="counter-clockwise" />
          </va-chip>
        </div>
        <div v-else-if="data[rowIndex].runtime !== null">
          <va-chip size="small" square outline color="primary">
            {{ new Date(data[rowIndex].runtime * 1000).toISOString().substr(11, 8) }}
          </va-chip>
        </div>
        <div v-else>
          <b>N/A</b>
        </div>
      </template>
      <template #cell(state)="{ value }">
        <va-chip v-if="value === 'STARTED'" size="small" color="info">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'SUCCESS'" size="small" color="success">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'FAILURE'" size="small" color="danger">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'RECEIVED'" size="small" color="purple">
          QUEUED
        </va-chip>
      </template>
      <template #cell(args)="{value} ">
        {{ value.name }}
      </template>
      
      <template #cell(actions)="{ rowIndex }">
        <va-button-group gradient :rounded="false">
          <va-button icon="settings" @click="this.$router.push(`/resources/virtualmachines/${VMNameToUUID(data[rowIndex].target)}`)" />
        </va-button-group>
      </template>

      <template v-if="pagination" #bodyAppend>
        <tr><td colspan="8" class="table--pagination">
          <va-pagination
            v-model="currentPage"
            input
            :pages="pages"
            size="small"
          />
        </td></tr>
      </template>

    </va-data-table>
    <va-modal
      v-model="logModal"
      size="large"
      :hide-default-actions="true"
    >
      <template #header>
        <h2>
          <va-icon name="bug_report" color="info" />
          Task logs ({{ selectedTask.target }})
        </h2>
      </template>
      <hr>
      <div class="consoleStyle">
        {{ taskInfo.traceback }}
      </div>
      <template #footer>
        <va-button @click="logModal = !logModal">
          Close
        </va-button>
      </template>
    </va-modal>
  </div>
</template>
<script>
import axios from 'axios'

export default {
  name: "backup-table",
  props: {
    pagination: { type: Boolean, default: false },
    perPage: { type: Number, default: 500 },
    data: { type: Array },
    columns: { type: Array }
  },
  data () {
    return {
      currentPage: 1,
      logModal: false,
      selectedTask: null,
      taskInfo: { traceback: null }
    }
  },
  computed: {
    pages () {
      if (this.pagination) {
        return (this.perPage && this.perPage !== 0)
          ? Math.ceil(this.data.length / this.perPage)
          : this.filtered.length
      } else {
        return null
      }
    }
  },
  methods: {
    toVirtualMachines() {
      if (this.$store.state.isvmTableReady) {
        this.$router.push(`/admin/resources/virtualmachines`)
      }
    },
    VMNameToUUID(name){
      for (let i = 0; i < this.$store.state.resources.vmList.length; i++){
        if(this.$store.state.resources.vmList[i].name === name){
          return this.$store.state.resources.vmList[i].uuid
        }
      }
      return 'no_uuid'
    },
    retrieveTasksLogs (taskId) {
      this.logModal = !this.logModal
      axios.get(`${this.$store.state.endpoint.api}/api/v1/logs/${taskId}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data) {
          this.taskInfo.traceback = JSON.parse(response.data).traceback
        } else {
          this.taskInfo = {
            traceback: "Unable to retrieve logs for this task."
          }
        }
      })
      .catch(e => {
        console.log(e)
      })
    }
  },
}
</script>
<style scoped>
  .table--pagination {
    text-align: center;
    text-align: -webkit-center;
  }
  .consoleStyle {
    padding: 1% 1% 1% 1%;
    background: black;
    color: silver;
    font-size: 1em;
    border-radius:5px;
    max-height: 5%; width: auto;
  }
</style>
