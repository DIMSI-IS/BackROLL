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
      <b-card title="Backup task">
        <div style="text-align: right; margin-bottom: 1%;">
          <b-button variant="info" @click="$router.push('/backups/tasks/new').catch(()=>{})">
            <b-icon icon="plus-circle" aria-hidden="true"></b-icon> Start task
          </b-button>
        </div>
        <b-table
          :items="tableData"
          :fields="fields"
          :per-page="perPage"
          :current-page="currentPage"
          :sort-desc="true"
          :busy="this.$store.state.loadingBackupTasks"
          sort-by="started"
          stacked="md"
          striped
          hover
          borderless
          ref="backupTaskTable"
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
            <div v-if="row.item.state === 'SUCCESS' || row.item.state === 'FAILURE'">
              {{ row.item.runtime === null ? null : new Date(row.item.runtime * 1000).toISOString().substr(11, 8) }}
            </div>
          </template>
          <template #cell(started)="row">
            {{ row.item.started ? (new Date(row.item.started * 1000)).toLocaleString('en-GB', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone }) : null }}
          </template>
          <template #empty="scope">
            <h5 style="text-align: center;">{{ scope.emptyText }}</h5>
          </template>
          <template #cell(state)="row">
            <h5>
              <b-badge v-if="row.item.name !== 'Pool VM Backup'" :variant="getBadgeType(row.item.state)">
                <b-icon :icon="getIcon(row.item.state)" :animation="getIconAnimation(row.item.state)" font-scale="1"></b-icon>
                {{ row.item.state }}
              </b-badge>
              <div v-else>
                <!-- {{ getPoolProgress(row.item.uuid) }} -->

              <b-progress class="mt-2" :max="getPoolTotalTask(row.item.uuid)" show-value>
                <b-progress-bar
                  :value="getPoolTotalSuccess(row.item.uuid)"
                  variant="success"
                  striped
                  :animated="(getPoolTotalFailed(row.item.uuid) + getPoolTotalSuccess(row.item.uuid)) < getPoolTotalTask(row.item.uuid) ? true : false"
                />
                <b-progress-bar
                  :value="getPoolTotalFailed(row.item.uuid)"
                  variant="danger"
                  striped
                  :animated="(getPoolTotalFailed(row.item.uuid) + getPoolTotalSuccess(row.item.uuid)) < getPoolTotalTask(row.item.uuid) ? true : false"
                />
              </b-progress>

              </div>
            </h5>
          </template>
          <template #cell(args)="row">
            {{ row.item.args.name }}
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
          <template #row-details="row">
            <b-table
              :items="retrieveChildTasks(row.item.uuid)"
              :fields="childFields"
            >
              <template #cell(started)="row">
                {{ row.item.started ? (new Date(row.item.started * 1000)).toLocaleString('en-GB', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone }) : null }}
              </template>
              <template #cell(runtime)="row">
                <div v-if="row.item.state === 'SUCCESS' || row.item.state === 'FAILURE'">
                  {{ row.item.runtime !== null ? new Date(row.item.runtime * 1000).toISOString().substr(11, 8) : '' }}
                </div>
              </template>

              <template #cell(state)="row">
                <h5>
                  <b-badge :variant="getBadgeType(row.item.state)">
                    <b-icon :icon="getIcon(row.item.state)" :animation="getIconAnimation(row.item.state)" font-scale="1"></b-icon>
                    {{ row.item.state }}
                  </b-badge>
                </h5>
              </template>


              <template #cell(actions)="row">
                <div style="text-align: right;">
                  <b-button
                    v-if="row.item.state == 'FAILURE'"
                    size="sm"
                    variant="warning"
                    @click="retrieve_tasks_logs(row.item.uuid)"
                  >
                    <b-icon icon="info-circle-fill" variant="white" aria-hidden="true"></b-icon>
                    Task logs
                  </b-button>
                </div>
              </template>

            </b-table>

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
      <div v-if="loadingTaskLogs">
        <pre class="consoleStyle">
          <code>
            {{ taskInfo.traceback }}
          </code>
        </pre>
      </div>
      <div v-else style="text-align: center;">
        <b-spinner label="Spinning" />
      </div>
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
            {text: 'Backups', active: true},
            {text: 'Tasks', to: '/backup/tasks', active: true},
          ],
          fields: [
            // {key: 'uuid', label:'ID'},
            {key: 'name', label:'Type', sortable: true},
            {key: 'target', label:'Target', sortable: true},
            {key: 'started', label:'Created', sortable: true},
            {key: 'runtime', label:'Runtime', sortable: true},
            {key: 'state', label:'State', sortable: true},
            'actions'
          ],
          childFields: [
            'name',
            {key: 'args.name', label:'Target', sortable: true},
            {key: 'started', label:'Created', sortable: true},
            {key: 'runtime', label:'Runtime', sortable: true},
            {key: 'state', label:'State', sortable: true},
            'actions'
          ],
          backupTaskList: [],
          modalLog: false,
          selectedTaskID: null,
          taskInfo: { traceback: null },
          perPage: 30,
          currentPage: 1,
          loadingTaskLogs: false
      }
  },
  beforeDestroy () {
    clearInterval(this.intervalId)
  },
  computed: {
    rows() {
      return this.filteredData.length
    },
    connectionStatus () {
      return this.$socket.connected
    },
    filteredData() {
      return Object.values(this.backupTaskList).filter(x => x.name !== 'backup_subtask')
    },
    tableData() {
      return this.filteredData.map(x => ({
        uuid: x.uuid,
        name: x.name.replaceAll('_', ' '),
        target: x.name == "Pool_VM_Backup" ? this.retrievePoolTarget(x.args) : this.retrieveArgs(x).name,
        started: x.started,
        ip_address: x.ip_address,
        runtime: x.name != "Pool_VM_Backup" ? x.runtime : null,
        state: x.state,
        // args: this.retrieveArgs(x),
        _showDetails: x.name == 'Pool_VM_Backup' ? true : false,
        parent: x.name == 'backup_subtask' ? x.parent : null
      }))
    }
  },
  mounted () {
    this.$store.state.loadingBackupTasks = true
    this.requestBackupTaskList()
  },
  methods: {
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
    getPoolTotalTask(uuid) {
      const childTaskArray =  Object.values(this.backupTaskList).filter(x => x.parent === uuid && x.name === "backup_subtask")
      return childTaskArray.length
    },
    getPoolTotalSuccess(uuid) {
      const childTaskArray =  Object.values(this.backupTaskList).filter(x => x.parent === uuid && x.name === "backup_subtask")
      let current = 0
      for (const item of childTaskArray) {
        if (item.state === 'SUCCESS') {
          current += 1
        }
      }
      return current
    },
    getPoolTotalFailed(uuid) {
      const childTaskArray =  Object.values(this.backupTaskList).filter(x => x.parent === uuid && x.name === "backup_subtask")
      let current = 0
      for (const item of childTaskArray) {
        if (item.state === 'FAILURE') {
          current += 1
        }
      }
      return current
    },
    retrieveChildTasks(uuid) {
      const childTaskList =  Object.values(this.backupTaskList).filter(x => x.parent === uuid && x.name === "backup_subtask")
      return childTaskList.map(x => ({
        uuid: x.uuid,
        name: x.name.replaceAll('_', ' '),
        started: x.started,
        runtime: x.runtime,
        state: x.state,
        args: this.retrieveArgs(x)
      }))      
    },
    handleRuntime(runtime) {
      if (runtime < 60) {
        return `${runtime} second(s)`
      } else if (runtime > 60 && runtime < 3600) {
        return `${(runtime / 60).toFixed(2)} minute(s)`
      } else if (runtime > 3600) {
        return `${(runtime / 3600).toFixed(2)} hour(s)`
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
          this.taskInfo.traceback = JSON.parse(response.data).traceback
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
    requestBackupTaskList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/tasks/backup`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.state.loadingBackupTasks = false
        this.backupTaskList = response.data.info
        setTimeout(()=>{
          this.requestBackupTaskList()
        },10000)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    retrieveArgs (x) {
      let result = ''
      if (x.name == 'Single_VM_Backup') {
        const mySubString = x.args.substring(
            x.args.lastIndexOf("{") + 1, 
            x.args.lastIndexOf("}")
        )
        result = "{" + mySubString.replaceAll("'", '"') + "}"
        return JSON.parse(result)
      } else if (x.name == 'Pool_VM_Backup') {
        const mySubString1 = x.args.substring(
            x.args.lastIndexOf("{") + 1, 
            x.args.lastIndexOf("}")
        )
        result = "{" + mySubString1 + "}"
        result = result.replaceAll("'", '"')
        result = JSON.parse(result)
        return result
      } else if (x.name == 'backup_subtask') {
        const mySubString = x.args.substring(
            x.args.lastIndexOf("{") + 1, 
            x.args.lastIndexOf("}")
        )
        result = mySubString.replaceAll("'", '"')
        result = `{${result}}`
        result = JSON.parse(result)
        return result
      }
    },
    getPool (id) {
      return this.$store.state.poolsList.filter((item) => {
        return item.id == id
      })
    },
    getIcon(state) {
      if (state === 'STARTED' || state =='RETRY') {
        return 'arrow-clockwise'
      }  else if (state === 'RECEIVED') {
        return 'hourglass'
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