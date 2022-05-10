<!--
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
-->

<template>
  <div>
    <div class="bc-content">
      <b-breadcrumb :items="items"></b-breadcrumb>
    </div>
    <div class="main-content">
      <b-card title="Restore task">
        <div style="text-align: right; margin-bottom: 1%;">
          <!-- <b-button variant="info" @click="$router.push('/restore/tasks/new').catch(()=>{})" disabled>
            <b-icon icon="plus-circle" aria-hidden="true"></b-icon> Nouvelle
          </b-button> -->
        </div>
        <b-table
          :items="tableData"
          :fields="fields"
          :per-page="perPage"
          :current-page="currentPage"
          :sort-desc="true"
          :busy="this.$store.state.loadingRestoreJobs"
          sort-by="received"
          stacked="md"
          striped
          hover
          borderless
          ref="selectableTable"
          show-empty
          emptyText="No task"
          small
        >
          <template #table-busy>
            <div class="text-center">
              <b-icon icon="three-dots" animation="cylon" font-scale="4" />
              <br>
              Discovering resources...
            </div>
          </template>
          <template #cell(runtime)="row">
            <div v-if="row.item.state === 'STARTED' && row.item.runtime === null">
              ...
            </div>
            <div v-else-if="row.item.state !== 'STARTED' && row.item.runtime !== null">
              {{ new Date(row.item.runtime * 1000).toISOString().substr(11, 8) }}
            </div>
          </template>
          <template #cell(received)="row">
            {{ (new Date(row.item.received * 1000)).toLocaleString('en-GB', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone }) }}
          </template>
          <template #empty="scope">
            <h5 style="text-align: center;">{{ scope.emptyText }}</h5>
          </template>
          <template #cell(state)="row">
            <h5>
              <b-badge :variant="getBadgeType(row.item.state)">
                <b-icon :icon="getIcon(row.item.state)" :animation="getIconAnimation(row.item.state)" font-scale="1"></b-icon>
                {{ row.item.state }}
              </b-badge>
            </h5>
          </template>
          <template #cell(args)="row">
            {{ row.item.args }}
          </template>
          <template #cell(actions)="row">
            <div style="text-align: right;">
              <b-button
                v-if="row.item.state == 'FAILURE'"
                size="sm"
                variant="warning"
                v-b-tooltip.hover title="See logs"
                @click="retrieve_tasks_logs(row.item.uuid)"
              >
                <b-icon icon="info-circle-fill" variant="white" aria-hidden="true"></b-icon>
              </b-button>
            </div>
          </template>
        </b-table>
        <b-pagination
          v-model="currentPage"
          :total-rows="rows"
          :per-page="perPage"
          aria-controls="taskTable"
          align="center"
        />
      </b-card>
    </div>
    <b-modal
      v-model="modalLog"
      id="modal-log"
      title="Task logs"
      size="xl"
      :ok-only="true"
    >
      <pre class="consoleStyle">
        <code>
          {{ taskInfo.traceback }}
        </code>
      </pre>
    </b-modal>
  </div>
</template>
<script>
import axios from 'axios'
export default {
  components: {},
  name: 'Dashboard',
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Restore', active: true},
            {text: 'Tasks', to: '/restore/tasks', active: true},
          ],
          fields: [
            // {key: 'uuid', label:'ID'},
            {key: 'name', label:'Type', sortable: true},
            {key: 'target', label:'Target', sortable: true},
            {key: 'received', label:'Created', sortable: true},
            {key: 'runtime', label:'Runtime', sortable: true},
            {key: 'state', label:'State', sortable: true},
            'actions'
          ],
          restoreTaskList: [],
          modalLog: false,
          selectedTaskID: null,
          taskInfo: { traceback: null },
          perPage: 8,
          currentPage: 1,
      }
  },
  beforeDestroy () {
    clearInterval(this.intervalId)
  },
  computed: {
    rows() {
      return this.$store.state.backup_jobs.length
    },
    connectionStatus () {
      return this.$socket.connected
    },
    filteredData() {
      return Object.values(this.restoreTaskList)
    },
    tableData() {
      return this.filteredData.map(x => ({
        uuid: x.uuid,
        name: x.name.replaceAll('_', ' '),
        received: x.received,
        ip_address: x.ip_address,
        runtime: x.runtime,
        state: x.state,
        // args: this.retrieveArgs(x),
        target: this.retrieveArgs(x).name,
      }))
    }
  },
  mounted () {
    this.requestRestoreTaskList()
  },
  methods: {
    requestRestoreTaskList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/tasks/restore`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.restoreTaskList = response.data.info
        setTimeout(()=>{
          this.requestRestoreTaskList()
        },10000)
      })
      .catch(e => {
        console.log(e)
      })
    },
    retrievePoolTarget (args) {
      if (args)  {
        const ArgsArray = args.split("'")
        for (const [i, v] of ArgsArray.entries()) {
          if (v === 'pool_id' && this.getPool(ArgsArray[i+2])[0]) {
            return this.getPool(ArgsArray[i+2])[0].name
          }     
        }
        return null
      } else {
        return null
      }
    },
    retrieve_tasks_logs (task_id) {
      this.modalLog = !this.modalLog
      this.loadingTaskLogs = true
      axios.get(`${this.$store.state.endpoint.api}/api/v1/logs/${task_id}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.loadingTaskLog = false
        if (response.data) {
          this.taskInfo.traceback = response.data.traceback
        } else {
          this.taskInfo = {
            traceback: "Unable to retrieve logs for this task."
          }
        }
      })
      .catch(e => {
        this.$bvToast.toast(e.data.status, {
          title: e.data.state,
          variant: 'danger',
          solid: true
        })
      })
    },
    handleRuntime(runtime) {
      if (runtime < 60) {
        return `${runtime} seconde(s)`
      } else if (runtime > 60 && runtime < 3600) {
        return `${(runtime / 60).toFixed(2)} minute(s)`
      } else if (runtime > 3600) {
        return `${(runtime / 3600).toFixed(2)} heure(s)`
      } else {
        return null
      }
    },
    retrieveArgs (x) {
      const mySubString = x.args.substring(
        x.args.lastIndexOf("(") + 1, 
        x.args.lastIndexOf(",") - 1
      )
      let  result = mySubString.replaceAll("'", '"')
      result = result.split(',')[1]
      result = "{" + result + "}"
      return JSON.parse(result)
    },
    retrieveTarget (x) {
      const mySubString = x.args.substring(
        x.args.lastIndexOf("(") + 1, 
        x.args.lastIndexOf(",") - 1
      )
      let  result = mySubString.replaceAll("'", '"')
      result = result.replaceAll("{...}", '')
      result = result.split('},')[0]
      result = result + "}"
      return JSON.parse(result)
    },
    getIcon(state) {
      if (state === 'STARTED' || state =='RETRY') {
        return 'arrow-clockwise'
      } else if (state === 'FAILURE') {
        return 'exclamation-circle-fill'
      } else if (state === 'SUCCESS') {
        return 'check-circle-fill'
      } else if (state === 'REVOKED') {
        return 'dash-circle'
      } 
    },
    getIconAnimation(state) {
      if (state === 'STARTED') {
        return 'spin'
      } else {
        return null
      }
    },
    getBadgeType(state) {
      if (state === 'STARTED' || state === 'RETRY') {
        return 'info'
      } else if (state === 'FAILURE') {
        return 'danger'
      } else if (state === 'SUCCESS') {
        return 'success'
      } else if (state === 'REVOKED') {
        return 'warning'
      }
    }
  }
}
</script>
<style>
.consoleStyle {
  padding: 1% 1% 1% 1%;
  background: black;
  color: white;
  font-size: 12px;
  border-radius:5px;
  max-height: 5%; width: auto;
}
</style>