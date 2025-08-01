<template>
  <div>
    <va-card v-if="$store.state.isvmTableReady">
      <va-card-title style="width: 100%;">
        <div class="row">
          <div class="flex">
            <h6 class="display-6">{{ virtualMachine.name }}</h6>
          </div>
          <div class="flex">
            <va-badge class="mb-2 mr-2" :color="virtualMachine.state === 'Running' ? 'success' : 'dark'"
              :text="virtualMachine.state" />
          </div>
        </div>
        <va-button icon="clear" color="info" @click="$router.go(-1)">Close</va-button>
      </va-card-title>
      <va-card-content>
        <va-tabs v-model="selectedTab" grow>
          <template #tabs>
            <va-tab icon="info" label="Information" name="info" />
            <va-tab icon="save" label="Backup(s)" name="save" />
          </template>
        </va-tabs>
        <div v-if="selectedTab === 'info'" style="padding-top: 1%;">
          <div class="row">
            <div class="flex xs6">
              <div class="item">
                <va-input class="mb-4" v-model="virtualMachine.id" label="KVM Domain ID" readonly />
                <va-input class="mb-4" v-model="virtualMachine.uuid" label="UUID" readonly />
              </div>
            </div>
            <div class="flex xs6">
              <div class="item">
                <va-input class="mb-4" v-model="virtualMachine.cpus" label="CPU Cores" readonly />
                <va-input class="mb-4" v-model="memory2GiB" label="Memory (GiB)" readonly />
              </div>
            </div>
          </div>
          <va-divider class="divider">
            <span class="px-2">
              HYPERVISOR
            </span>
          </va-divider>
          <div class="row">
            <div class="flex xs6">
              <div class="item">
                <va-input v-if="hypervisor" class="mb-4" v-model="hypervisor.hostname" label="Host" readonly />
                <va-input class="mb-4" v-model="virtualMachine.host_tag" label="Tag" readonly />
              </div>
            </div>
            <div class="flex xs6">
              <div class="item">
                <va-input v-if="hypervisor" class="mb-4" v-model="pool.name" label="Pool" readonly />
                <va-input v-if="pool" class="mb-4" v-model="policy.name" label="Backup Policy" readonly />
              </div>
            </div>
          </div>
          <va-divider class="divider">
            <span class="px-2">
              STORAGE
            </span>
          </va-divider>
          <!-- <div v-if="loadingStorage" class="flex-center ma-3">
            <looping-rhombuses-spinner :animation-duration="1500" :size="50" color="#2c82e0" />
          </div>
          <va-data-table v-else class="mb-4" :items="storageList" :columns="[ -->
          <va-data-table class="mb-4" :items="storageList" :columns="[
            { key: 'device', sortable: true },
            { key: 'source', sortable: true },
            { key: 'formattedStatus', label: 'status', sortable: true }]">
            <template #cell(device)="cell">
              <va-chip size="small" square color="info">
                {{ cell.source.toUpperCase() }}
              </va-chip>
            </template>
            <template #cell(source)="cell">
              {{ cell.source }}
            </template>
            <template #cell(formattedStatus)="cell">
              <va-chip size="small" :color="cell.source.ok ? 'success' : 'danger'">
                {{ cell.source.label }}
              </va-chip>
            </template>
          </va-data-table>
          <va-divider class="divider">
            <span class="px-2">
              MISCELLANEOUS
            </span>
          </va-divider>
          <va-button icon="lock_open" @click="requestBorgBreakLock()">
            Unlock backup repository
          </va-button>
          <div class="space" />
          <va-button icon="cleaning_services" disabled>
            Clean and delete backup repository
          </va-button>
        </div>
        <div v-else-if="selectedTab === 'save'" style="padding-top: 1%;">
          <!-- <div v-if="loadingBackups" class="flex-center ma-3">
            <scaling-squares-spinner :animation-duration="1500" :size="85" color="#2c82e0" />
          </div>
          <div v-else> -->
          <div>
            <div class="row">
              <div class="flex xs6">
                <div class="item">
                  <va-input class="mb-4" v-model="mostRecentBackup" label="Most recent backup" readonly />
                  <va-input class="mb-4" v-model="oldestBackup" label="Oldest backup" readonly />
                </div>
              </div>
              <div class="flex xs6">
                <div class="item">
                  <va-input class="mb-4" v-model="nextRun" label="Next scheduled backup" readonly />
                  <va-button class="mb-4" @click="startBackup" :disabled="backingUp">
                    {{ backingUp ? "Backing up…" : "Backup now" }}
                  </va-button>
                </div>
              </div>
            </div>
            <va-divider class="divider">
              <span class="px-2">
                BACKUP LIST
              </span>
            </va-divider>
            <va-data-table :items="backupInfo.archives" :columns="columns" :current-page="currentPage"
              :per-page="perPage" v-model:sort-by="sortBy" v-model:sorting-order="sortingOrder" @sorted="
                sortedRowsEmitted = $event.items.map(row => row.id),
                sortingOrderEmitted = $event.sortingOrder,
                sortByEmitted = $event.sortBy
                ">
              <template #header(name)>disk</template>
              <template #header(start)>date</template>
              <template #cell(name)="{ value }">
                <va-chip size="small" color="info" square>
                  {{ value.split('_')[0].toUpperCase() }}
                </va-chip>
              </template>
              <template #cell(start)="{ value }">
                <va-chip size="small" color="info" square outline>
                  {{ new Date(value).toLocaleDateString() }} - {{ new Date(value).toLocaleTimeString() }}
                </va-chip>
              </template>
              <template #cell(actions)="{ rowIndex }">
                <va-button-group gradient :rounded="false">
                  <va-button icon="settings_backup_restore"
                    @click="selectedBackup = backupInfo.archives[rowIndex], showDiskRestoreModal = !showDiskRestoreModal" />
                  <va-button icon="repartition" disabled />
                  <va-button icon="delete"
                    @click="selectedBackup = backupInfo.archives[rowIndex], showDeleteModal = !showDeleteModal" />
                </va-button-group>
              </template>
              <template #bodyAppend>
                <tr>
                  <td colspan="8" class="table-example--pagination">
                    <va-pagination v-model="currentPage" input :pages="pages" size="small" flat />
                  </td>
                </tr>
              </template>
            </va-data-table>
          </div>
        </div>
      </va-card-content>
    </va-card>
    <div v-else class="flex-center ma-3">
      <scaling-squares-spinner :animation-duration="1500" :size="85" color="#2c82e0" />
    </div>
    <va-modal v-model="showDiskRestoreModal" @ok="restoreDiskFile()">
      <template #header>
        <h2>
          <va-icon name="settings_backup_restore" color="info" />
          Full disk restore
        </h2>
      </template>
      <hr>
      <div>
        You are about to entirely restore disk <b>{{
          JSON.parse(JSON.stringify(this.selectedBackup)).name.split('_')[0].toUpperCase() }}</b>
        <va-alert color="danger" border-color="danger" class="mb-4">
          Every data from {{ new Date(JSON.parse(JSON.stringify(this.selectedBackup)).start).toLocaleDateString() }} to
          now
          will be lost !
        </va-alert>
        Please confirm action.
      </div>
    </va-modal>
    <va-modal v-model="showDeleteModal" @ok="deleteBackup()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          Removing backup
        </h2>
      </template>
      <hr>
      <div>
        You are about to remove backup <b>{{ JSON.parse(JSON.stringify(this.selectedBackup)).name }}</b><br>
        This backup is from {{ new Date(JSON.parse(JSON.stringify(this.selectedBackup)).start).toLocaleDateString()
        }}<br>
        Please confirm action.
      </div>
    </va-modal>
  </div>
</template>
<script>
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'
import axios from 'axios'
import parser from 'cron-parser'

export default defineComponent({
  name: 'VirtualMachineDetails',
  components: { ...spinners },
  data() {
    return {
      columns: [
        { key: 'name', sortable: true },
        { key: 'start', sortable: true },
        { key: 'actions' },
      ],
      perPage: 14,
      currentPage: 1,
      sortBy: 'start',
      sortingOrder: 'desc',
      selectedTab: 'info',
      loadingBackups: false,
      selectedBackup: null,
      showDeleteModal: false,
      showDiskRestoreModal: false,
      backupInfo: { archives: [] },

      backingUp: false,

      storageList: [],
      loadingStorage: false,
      storageErrorToShow: null,
      lastMostRecentBackup: null, // Used to track changes in most recent backup during the loading
      lastOldestBackup: null, // Used to track changes in oldest backup during the loading
    }
  },
  watch: {
    virtualMachine: function () {
      this.requestVmDetails()
      this.requestBackupList()
    }
  },
  computed: {
    virtualMachine() {
      const result = this.$store.state.resources.vmList.filter((item) => {
        return item.uuid == this.$route.params.id
      })
      return result[0]
    },
    hypervisor() {
      const result = this.$store.state.resources.hostList.filter((item) => {
        return item.id == this.virtualMachine.host
      })
      return result[0]
    },
    pool() {
      if (this.hypervisor) {
        if (this.hypervisor.pool_id) {
          return this.getPool(this.hypervisor.pool_id)
        } else {
          return null
        }
      } else {
        return this.getPool(this.virtualMachine.pool_id)
      }
    },
    policy() {
      if (this.pool.id) {
        return this.getPolicy(this.pool.policy_id)
      } else {
        return null
      }
    },
    memory2GiB() {
      return ((this.virtualMachine.mem / 1024) / 1024).toFixed(0)
    },
    mostRecentBackup() {
      if (this.backupInfo.archives.length > 0) {
        return new Date(Math.max(...this.backupInfo.archives.map(e => new Date(e.start)))).toLocaleDateString()
      } else {
        return "N/A"
      }
    },
  oldestBackup() {
    if (this.backupInfo.archives.length > 0) {
      const value = new Date(Math.min(...this.backupInfo.archives.map(e => new Date(e.start)))).toLocaleDateString()
      this.lastOldestBackup = value
      return value
    }
    return this.lastOldestBackup || "N/A"
  },
    pages() {
      return (this.perPage && this.perPage !== 0)
        ? Math.ceil(this.backupInfo.archives.length / this.perPage)
        : this.filtered.length
    },
    nextRun() {
      if (this.policy.schedule) {
        const options = {
          currentDate: new Date(),
          tz: 'Europe/Paris'
        }
        const interval = parser.parseExpression(this.policy.schedule, options)
        const result = `${new Date(interval.next()).toLocaleDateString()} - ${new Date(interval.next()).toLocaleTimeString()}`
        return result
      } else {
        return 'N/A'
      }
    }
  },
  mounted() {
    this.requestVmDetails()
    this.requestBackupList()
  },
  methods: {
    restoreDiskFile: function () {
      const json = {
        "virtual_machine_id": this.virtualMachine.uuid,
        "backup_name": this.selectedBackup.archive
      }
      axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/restore/${this.virtualMachine.uuid}`, json, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ message: 'Restore task has been sent to backend', color: 'light' })
          this.trackRestoreJob(response.data.Location)
        })
        .catch(error => {
          this.errors.push(error)
          console.error(error)
          this.$vaToast.init({ message: 'Unable to start the disk recovery task', color: 'danger' })
        })
    },
    startBackup() {
      this.backingUp = true;
      axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/singlebackup/${this.virtualMachine.uuid}`, {}, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ message: 'Backup requested to backend', color: 'light' })
          this.trackBackupJob(response.data.Location)
        })
        .catch(error => {
          this.backingUp = false;
          this.errors.push(error)
          console.error(error)
          this.$vaToast.init({ message: 'Unable to backup VM', color: 'danger' })
        })
    },
    trackBackupJob(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.trackBackupJob(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.backingUp = false;
            this.$vaToast.init({ message: 'Backup has been successfully done', color: 'success' })
            this.requestBackupList()
          } else if (response.data.state === 'FAILURE') {
            this.backingUp = false;
            this.$vaToast.init({ message: 'Unable to backup VM', color: 'danger' })
          }
        })
        .catch(error => {
          this.backingUp = false;
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    deleteBackup: function () {
      const json = {
        "virtual_machine_id": this.virtualMachine.uuid,
        "backup_id": this.selectedBackup.archive
      }
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine.uuid}/backups/${JSON.parse(JSON.stringify(this.selectedBackup)).name}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ message: 'Delete backup requested to backend', color: 'light' })
          this.trackDeleteBackupJob(response.data.Location)
        })
        .catch(error => {
          this.errors.push(error)
          console.error(error)
          this.$vaToast.init({ message: 'Unable to delete backup', color: 'danger' })
        })
    },
    trackDeleteBackupJob(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.trackDeleteBackupJob(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.$vaToast.init({ message: 'Backup has been successfully deleted', color: 'success' })
            this.requestBackupList()
          } else if (response.data.state === 'FAILURE') {
            this.$vaToast.init({ message: 'Unable to delete backup', color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    trackRestoreJob(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.getBackupList(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.$vaToast.init({ message: 'VM successfully restored', color: 'success' })
          } else if (response.data.state === 'FAILURE') {
            this.$vaToast.init({ message: 'Unable to restore VM', color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    getBorgBreakLock: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.getBorgBreakLock(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.$vaToast.init({ title: response.data.state, message: 'Backup repository has been successfully unlocked', color: 'success' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: 'Unable to unlock backup repository',
            message: error?.data?.status ?? error,
            color: 'danger'
          })
        })
    },
    requestBorgBreakLock() {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine.uuid}/breaklock`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ title: response.data.state, message: 'Asking to break backup repository lock...', color: 'light' })
          this.getBorgBreakLock(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    getBackupList(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.getBackupList(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.backupInfo = response.data.info
            this.loadingBackups = false
          } else if (response.data.state === 'FAILURE') {
            this.loadingBackups = false
            this.$vaToast.init({ message: response.data.status, color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    requestBackupList() {
      if (this.virtualMachine) {
        axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine.uuid}/backups`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
          .then(response => {
            this.loadingBackups = true
            this.getBackupList(response.data.Location)
          })
          .catch(error => {
            console.error(error)
            this.$vaToast.init({
              title: "Unexpected error",
              message: error,
              color: "danger"
            })
          })
      }
    },
    getVmDetails(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
            setTimeout(() => {
              this.getVmDetails(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            const storageList = response.data.info.storage;
            for (const disk of storageList) {
              const { status } = disk;
              disk.formattedStatus = {
                label: !status.exists ? "Not found" : !status.readable ? "No read access" : "Available",
                ok: Object.values(status).every(e => e)
              }
            }
            this.storageList = storageList;

            this.loadingStorage = false
          } else if (response.data.state === 'FAILURE') {
            this.loadingStorage = false
            this.$vaToast.init({ message: response.data.status, color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
    requestVmDetails() {
      if (this.virtualMachine) {
        axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine.uuid}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
          .then(response => {
            this.loadingStorage = true
            this.getVmDetails(response.data.Location)
          })
          .catch(error => {
            console.error(error)
            this.$vaToast.init({
              title: "Unexpected error",
              message: error,
              color: "danger"
            })
          })
      }
    },
    getPool(id) {
      const result = this.$store.state.resources.poolList.filter((item) => {
        return item.id == id
      })
      return result[0]
    },
    getPolicy(id) {
      const result = this.$store.state.resources.policyList.filter((item) => {
        return item.id == id
      })
      return result[0]
    }
  }
})
</script>
<style lang="scss" scoped>
.spacer {
  text-align: center;
  border: 2px dashed var(--va-secondary);
}

.divider {
  padding-top: 1%;
  padding-bottom: 1%;
}

.table-example--pagination {
  text-align: center;
  text-align: -webkit-center;
}

.space {
  width: 5px;
  height: auto;
  display: inline-block;
}
</style>