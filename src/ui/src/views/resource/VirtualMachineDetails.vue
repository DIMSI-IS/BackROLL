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
      <div v-if="!this.$store.state.loadingVMs" style="margin-bottom: 4%;">
        <div v-if="virtual_machine[0] !== undefined" fluid="sm">
          <b-row>
            <b-col>
              <h2> {{ virtual_machine[0].name }} </h2>
            </b-col>
            <b-col style="text-align: right;">
              <h2>
                <b-badge :variant="getBadgeType(virtual_machine[0].state)">
                  {{ virtual_machine[0].state }}
                </b-badge>
              </h2>
            </b-col>
          </b-row>
          <hr>
          <div v-if="backupInfo.length > 0">
            <b-alert v-if="backupInfo.state === 'locked'" variant="warning" show>
              <b-icon icon="arrow-clockwise" animation="spin" font-scale="1"/> A backup of this VM is currently in progress...
            </b-alert>
          </div>
          <b-row>
            <b-col md="3">
              <b-list-group style="padding: 0 0 2% 0;">
                <b-list-group-item button :active="active == 0" @click="active = 0">Information</b-list-group-item>
                <b-list-group-item button :active="active == 2" @click="active = 2">Storage</b-list-group-item>
                <div v-if="!loadingBackups">
                  <div v-if="backupInfo.length > 0">
                    <b-list-group-item v-if="backupInfo.state !== 'locked'" button :active="active == 3" @click="active = 3">Backup(s)</b-list-group-item>
                    <b-list-group-item v-else variant="warning"  button :active="active == 3" @click="active = 3" disabled><span><b-icon icon="lock" animation="fade" font-scale="1" /></span> Backup(s)</b-list-group-item>
                  </div>
                  <div v-else>
                    <b-list-group-item button :active="active == 3" @click="active = 3">Backup(s)</b-list-group-item>
                  </div>
                </div>
                <div v-else>
                  <b-list-group-item disabled><b-icon style="margin-right: 10px;" icon="three-dots" animation="cylon" font-scale="1"></b-icon><span>Backup(s)</span></b-list-group-item>
                </div>
                <b-list-group-item button :active="active == 1" @click="active = 1">Settings</b-list-group-item>
              </b-list-group>
            </b-col>
            <b-col md="9">
              <b-card>
                <div v-if="active === 0">
                  <b-card-text>
                    <b-form-group
                      label="ID"
                    >
                      <b-form-input
                        :value="virtual_machine[0].id"
                        required
                        readonly
                      ></b-form-input>
                    </b-form-group>
                    <b-form-group
                      label="UUID"
                    >
                      <b-form-input
                        :value="virtual_machine[0].uuid"
                        required
                        readonly
                      ></b-form-input>
                    </b-form-group>
                    <b-form-group
                      label="Name"
                    >
                      <b-form-input
                        :value="virtual_machine[0].name"
                        required
                        readonly
                      ></b-form-input>
                    </b-form-group>
                    <b-form-group
                      label="Hypervisor"
                    >
                      <b-form-input
                        :value="getHypervisor(virtual_machine[0].host)[0].hostname"
                        required
                        readonly
                      ></b-form-input>
                    </b-form-group>
                    <b-form-group
                      label="State"
                    >
                      <b-form-input
                        :value="virtual_machine[0].state"
                        required
                        readonly
                      ></b-form-input>
                    </b-form-group>
                  </b-card-text>
                </div>
                <div v-if="active === 1">
                  <b-card-text>
                    <div
                      style="font-weight: bold; font-size: 18px;"
                    >
                      Settings
                    </div>
                    <br>
                    <b-button
                      style="margin-right: 1%;"
                      v-b-modal.modal-breaklock
                      size="sm"
                    >
                      <b-icon icon="unlock" aria-hidden="true" /> <span> Unlock BORG repository </span>
                    </b-button>
                  </b-card-text>
                </div>
                <div v-if="active === 2">
                  <b-card-text>
                    <div
                      style="font-weight: bold; font-size: 18px;"
                    >
                      Volume(s)
                    </div>
                    <br>
                    <div v-if="virtual_machine[0].state === 'Running'">
                      <div
                        v-if="loadingdisk_list"
                        class="text-center"
                      >
                        <b-icon icon="three-dots" animation="cylon" font-scale="4" />
                        <br>
                        Discovering resources...
                      </div>
                      <b-table
                        v-else
                        striped
                        hover
                        borderless
                        :items="disk_list"
                      >
                        <template #cell(device)="row">
                          <div style="color: #4078c0;">
                            <strong>{{ row.item.device.toUpperCase() }}</strong>
                          </div>
                        </template>
                        <template #cell(source)="row" class="text-right">
                          <code style="background: black; color: silver; padding: 5px; border-radius: 5px;">
                            {{ row.item.source }}
                          </code>
                        </template>
                      </b-table>
                    </div>
                    <div v-else>
                      Virtual machine is not running
                    </div>
                  </b-card-text>
                </div>
                <div v-if="active === 3">
                  <div v-if="backupInfo.archives.length > 0">
                    <b-calendar
                      id="backup-calendar"
                      v-model="selectedDate"
                      :min="minDate"
                      :max="maxDate"
                      :date-info-fn="dateClass"
                      block
                      no-highlight-today
                    />
                  </div>
                  <div v-else>
                    There is not yet a backup associated with this virtual machine
                  </div>
                  <div v-if="selectedDate !== ''">
                    <div
                      v-if="selectedBackupDay.length === 0"
                      style="text-align: center; font-size: 18px; font-weight: bold; padding-top: 3%;"
                    >
                      No backup
                    </div>
                    <div v-else>
                      <b-table
                        responsive
                        borderless
                        striped
                        hover
                        :fields="fields"
                        :busy="loadingBackups"
                        emptyFilteredText="Aucune sauvegarde"
                        show-empty
                        :items="selectedBackupDay"
                      >
                        <template #table-busy>
                          <div class="text-center">
                            <b-icon icon="three-dots" animation="cylon" font-scale="4" />
                            <br>
                            Discovering resources...
                          </div>
                        </template>
                        <template #cell(archive)="row">
                          {{ row.item.archive.includes('_') ? (row.item.archive.split('_')[0]).toUpperCase() : (row.item.archive.split('-')[0]).toUpperCase() }}
                        </template>
                        <template #cell(actions)="row">
                          <div style="text-align: right;">
                          <b-button
                            :disabled="disk_list.includes({}) || backupInfo.state === 'locked'"
                            style="margin-right: 1%;"
                            v-b-modal.modal-restore
                            size="sm"
                            @click="selected_backup = row.item"
                          >
                            <b-icon icon="skip-forward-circle" aria-hidden="true" /> <span> Restore </span>
                          </b-button>
                          <b-button
                            :disabled="disk_list.includes({}) || backupInfo.state === 'locked'"
                            style="margin-right: 1%;"
                            v-b-modal.modal-delete
                            @click="selected_backup = row.item"
                            size="sm"
                            variant="danger"
                          >
                            <b-icon icon="trash" aria-hidden="true" /> <span> Delete </span>
                          </b-button>
                          </div>
                        </template>
                      </b-table>
                    </div>
                  </div>
                </div>
              </b-card>
            </b-col>
          </b-row>
        </div>
      </div>
      <div v-else class="text-center">
        <b-icon icon="three-dots" animation="cylon" font-scale="4" />
        <br>
        Discovering resources...
      </div>
    </div>

    <b-modal
      id="modal-restore"
      title="Restore backup"
      ok-title="Confirm"
      cancel-title="Cancel"
      ok-variant="danger"
      cancel-variant="dark"
      @ok="restoreDiskFile()"
    >
      <p class="my-4">
        You are about to restore a backup from <strong>{{ new Date (selectedDate).toLocaleDateString() }}</strong>.<br>
        All data created or modified since this date will be lost!
      </p>
    </b-modal>
    <b-modal
      v-if="virtual_machine[0]"
      id="modal-breaklock"
      title="Casser le verrouillage du repository BORG"
      ok-title="CONFIRMER"
      cancel-title="Annuler"
      ok-variant="danger"
      cancel-variant="dark"
      @ok="requestBorgBreakLock()"
    >
      <p class="my-4">
        You are about to break the lock of the VM's BORG repository <strong>{{ virtual_machine[0].name }}</strong>.<br>
        If a backup is in progress, this will interrupt it.
      </p>
    </b-modal>

    <b-modal
      id="modal-delete"
      title="Suppression d'une sauevegarde"
      ok-title="CONFIRMER"
      cancel-title="Annuler"
      ok-variant="danger"
      cancel-variant="dark"
      @ok="delete_archive()"
    >
      <p class="my-4">
        Are you sure you want to delete this backup.
      </p>
    </b-modal>

  </div>
</template>
<script>
import axios from 'axios'
export default {
  data() {
    return {
        items: [
          {text: 'Dashboard', to: '/'},
          {text: 'Virtual Machines', to: '/resource/virtual_machines'},
          {text: this.$route.params.virtual_machine, to: `/resource/virtual_machines/${this.$route.params.virtual_machine}`, active: true}
        ],
        fields: [
          {key: 'archive', label:'Volume'},
          {key: 'actions', label: ''}
        ],
        active: 0,
        disk_list: [],
        loadingdisk_list: false,
        loadingBackups: false,
        selected_backup: null,
        selectedDate: '',
        backupInfo: []
    }
  },
  sockets: {
    borg_breaklock (val) {
      this.$bvToast.toast(val.result === 'success' ? "BORG lock has been broken" : "Unable to break the BORG lock", {
        title: 'Succès !',
        variant: val.result === 'success' ? 'success' : 'danger',
        solid: true
      })
    },
    retrievedBackups (val) {
      this.backupInfo = val
      this.loadingBackups = false
    }
  },
  computed: {
    selectedBackupDay () {
      let matchingBackup = []
      for (let value of this.backupInfo.archives) {
        if (value.start.split('T')[0] === this.selectedDate) {
          matchingBackup.push(value)
        }
      }
      return matchingBackup
    },
    today () {
      const now = new Date()
      return new Date(now.getFullYear(), now.getMonth(), now.getDate())
    },
    minDate () {
      let d = new Date()
      d.setDate(d.getDate() - 30) // subtract 30 days
      return d.toISOString().split("T")[0]
    },
    maxDate () {
      return this.today
    },
    virtual_machine () {
      return this.$store.state.vmsList.filter((item) => {
        return item.name == this.$route.params.virtual_machine
      })
    },
    hypervisor () {
      return this.$store.state.hostsList.filter((item) => {
        return item.hostname == this.virtual_machine[0].host
      })      
    },
  },
  watch: {
    virtual_machine: function () {
      this.requestVmDetails()
      this.requestBackupList()
    }
  },
  mounted () {
    this.requestVmDetails()
    this.requestBackupList()
  },
  methods: {
    dateClass(ymd) {
      for (let value of this.backupInfo.archives) {
        if (ymd === value.start.split('T')[0]) {
          return 'backupedDay'
        }
      }
      return ''
    },
    delete_archive () {
      const json = {
          "target": this.virtual_machine[0],
          "selected_backup": this.selected_backup
        }
      this.$socket.client.emit('delete_archive', json)
      this.$bvToast.toast("Task ongoing...", {
        title: "Archive deletion",
        variant: 'primary' ,
        solid: true,
        autoHideDelay: 5000,
        noCloseButton: true
      })
    },
    getBadgeType(state) {
      if (state === 'Running') {
        return 'success'
      } else {
        return 'danger'
      }
    },
    getVmDetails: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getVmDetails(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
          this.disk_list = response.data.info.disk_list
          this.loadingdisk_list = false
        } else if (response.data.state === 'FAILURE') {
          this.loadingdisk_list = false
          this.$bvToast.toast(response.data.status, {
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        console.log(e)
      })
    },
    requestVmDetails: function () {
      if (this.virtual_machine[0]) { 
        axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtual_machine[0].uuid}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
        .then(response => {
          this.loadingdisk_list = true
          this.getVmDetails(response.data.Location)
        })
        .catch(e => {
          console.log(e)
        })
      }
    },
    getHypervisor (id) {
      return this.$store.state.hostsList.filter((item) => {
        return item.id == id
      })
    },
    getBackupList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getBackupList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
          this.backupInfo = response.data.info
          this.loadingBackups = false
        } else if (response.data.state === 'FAILURE') {
          this.loadingBackups = false
          this.$bvToast.toast(response.data.status, {
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        console.log(e)
      })
    },
    requestBackupList: function () {
      if (this.virtual_machine[0]) { 
        axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtual_machine[0].uuid}/backups`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
        .then(response => {
          this.loadingBackups = true
          this.getBackupList(response.data.Location)
        })
        .catch(e => {
          console.log(e)
        })
      }
    },
    restoreDiskFile: function () {
      console.log(this.virtual_machine[0].uuid, this.selected_backup)
      const json = {
          "virtual_machine_id": this.virtual_machine[0].uuid,
          "backup_id": this.selected_backup.archive
        }
      axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/restore/${this.virtual_machine[0].uuid}`, json, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.trackRestoreJob(response.data.Location)
        this.$bvToast.toast("Restore task has been sent to backend", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    trackRestoreJob: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.trackRestoreJob(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
          this.$bvToast.toast("VM successfully restored", {
            title: response.data.state,
            variant: 'success',
            solid: true
          })
        } else if (response.data.state === 'FAILURE') {
          this.$bvToast.toast(response.data.status, {
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    getBorgBreakLock: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getBorgBreakLock(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
          this.$bvToast.toast("Borg repository lock has been broken", {
            title: response.data.state,
            variant: 'success',
            solid: true
          })
        } else if (response.data.state === 'FAILURE') {
          this.$bvToast.toast(response.data.status, {
            title: response.data.state,
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        console.log(e)
      })
    },
    requestBorgBreakLock () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtual_machine[0].uuid}/breaklock`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getBorgBreakLock(response.data.Location)
      })
      .catch(e => {
        console.log(e)
      })
    }
  }
}
</script>
<style>
.backupedDay{
  background-color: #BEE5EB;
}
</style>
