<template>
  <div>
    <va-card v-if="$store.state.isvmTableReady && virtualMachine">
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
        <va-button icon="clear" color="info" @click="$router.go(-1)">{{ $t('pages.resources.vm.close') }}</va-button>
      </va-card-title>
      <va-card-content>
        <va-tabs v-model="selectedTab" grow>
          <template #tabs>
            <va-tab icon="info" :label="$t('pages.resources.vm.tabInfo')" name="info" />
            <va-tab icon="save" :label="$t('pages.resources.vm.tabBackups')" name="save" />
          </template>
        </va-tabs>
        <div v-if="selectedTab === 'info'" style="padding-top: 1%;">
          <div class="row">
            <div class="flex xs6">
              <div class="item">
                <va-input class="mb-4" v-model="virtualMachine.id" :label="$t('pages.resources.vm.kvmDomainId')" readonly />
                <va-input class="mb-4" v-model="virtualMachine.uuid" label="UUID" readonly />
              </div>
            </div>
            <div class="flex xs6">
              <div class="item">
                <va-input class="mb-4" v-model="virtualMachine.cpus" :label="$t('pages.resources.vm.cpuCores')" readonly />
                <va-input class="mb-4" v-model="memory2GiB" :label="$t('pages.resources.vm.memoryGiB')" readonly />
              </div>
            </div>
          </div>
          <va-divider class="divider">
            <span class="px-2">
              {{ $t('pages.resources.vm.sectionHypervisor') }}
            </span>
          </va-divider>
          <div class="row">
            <div class="flex xs6">
              <div class="item">
                <va-input v-if="hypervisor" class="mb-4" v-model="hypervisor.hostname" :label="$t('pages.resources.vm.host')" readonly />
                <va-input class="mb-4" v-model="virtualMachine.host_tag" :label="$t('pages.resources.vm.tag')" readonly />
              </div>
            </div>
            <div class="flex xs6">
              <div class="item">
                <va-input v-if="hypervisor" class="mb-4" v-model="pool.name" :label="$t('pages.resources.vm.pool')" readonly />
                <va-input v-if="pool" class="mb-4" v-model="policy.name" :label="$t('pages.resources.vm.backupPolicy')" readonly />
              </div>
            </div>
          </div>
          <va-divider class="divider">
            <span class="px-2">
              {{ $t('pages.resources.vm.sectionStorage') }}
            </span>
          </va-divider>
          <!-- <div v-if="loadingStorage" class="flex-center ma-3">
            <looping-rhombuses-spinner :animation-duration="1500" :size="50" color="#2c82e0" />
          </div>
          <va-data-table :no-data-html="$t('pages.common.noItems')" v-else class="mb-4" :items="storageList" :columns="[ -->
          <va-data-table :no-data-html="$t('pages.common.noItems')" class="mb-4" :items="storageList" :columns="[
            { key: 'device', label: $t('pages.resources.vm.colDevice'), sortable: true },
            { key: 'source', label: $t('pages.resources.vm.colSource'), sortable: true },
            { key: 'formattedStatus', label: $t('pages.resources.vm.colStatus'), sortable: true }]">
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
                {{ $t(cell.source.label) }}
              </va-chip>
            </template>
          </va-data-table>
          <va-divider class="divider">
            <span class="px-2">
              {{ $t('pages.resources.vm.sectionMisc') }}
            </span>
          </va-divider>
          <va-button :disabled="!$store.getters.canEdit" icon="lock_open" @click="requestBorgBreakLock()">
            {{ $t('pages.resources.vm.unlockRepo') }}
          </va-button>
          <div class="space" />
          <va-button icon="cleaning_services" disabled>
            {{ $t('pages.resources.vm.cleanRepo') }}
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
                  <va-input class="mb-4" v-model="mostRecentBackup" :label="$t('pages.resources.vm.mostRecent')" readonly />
                  <va-input class="mb-4" v-model="oldestBackup" :label="$t('pages.resources.vm.oldest')" readonly />
                </div>
              </div>
              <div class="flex xs6">
                <div class="item">
                  <va-input class="mb-4" v-model="nextRun" :label="$t('pages.resources.vm.nextBackup')" readonly />
                  <va-button class="mb-4" @click="startBackup" :disabled="(backingUp) || !$store.getters.canEdit">
                    {{ backingUp ? $t('pages.resources.vm.backingUp') : $t('pages.resources.vm.backupNow') }}
                  </va-button>
                </div>
              </div>
            </div>
            <va-divider class="divider">
              <span class="px-2">
                {{ $t('pages.resources.vm.sectionBackupList') }}
              </span>
            </va-divider>
            <va-data-table :no-data-html="$t('pages.common.noItems')" :items="backupInfo.archives" :columns="columns" :current-page="currentPage"
              :per-page="perPage" v-model:sort-by="sortBy" v-model:sorting-order="sortingOrder" @sorted="
                sortedRowsEmitted = $event.items.map(row => row.id),
                sortingOrderEmitted = $event.sortingOrder,
                sortByEmitted = $event.sortBy
                ">
              <template #header(name)>{{ $t('pages.resources.vm.colDisk') }}</template>
              <template #header(start)>{{ $t('pages.resources.vm.colDate') }}</template>
              <template #cell(name)="{ value }">
                <va-chip size="small" color="info" square>
                  {{ value.startsWith('files_') ? $t('pages.resources.vm.files') : value.split('_')[0].toUpperCase() }}
                </va-chip>
                <span v-if="value.startsWith('files_')" class="ml-2">{{ value.replace(/^files_/, '').replace(/_\d+$/, '') }}</span>
              </template>
              <template #cell(start)="{ value }">
                <va-chip size="small" color="info" square outline>
                  {{ new Date(value).toLocaleDateString() }} - {{ new Date(value).toLocaleTimeString() }}
                </va-chip>
              </template>
              <template #cell(actions)="{ rowIndex }">
                <va-button-group gradient :rounded="false">
                  <va-button :disabled="!$store.getters.canEdit || backupInfo.archives[rowIndex].name.startsWith('files_')"
                    icon="settings_backup_restore"
                    @click="selectedBackup = backupInfo.archives[rowIndex], showDiskRestoreModal = !showDiskRestoreModal" />
                  <va-button :disabled="!$store.getters.canEdit" icon="folder_open" :title="$t('pages.resources.vm.browseFiles')"
                    @click="$router.push(`/resources/virtualmachines/${virtualMachine.uuid}/backups/${backupInfo.archives[rowIndex].name}/files`)" />
                  <va-button :disabled="!$store.getters.canEdit" icon="delete"
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
    <va-card v-else-if="$store.state.isvmTableReady" class="vm-not-found">
      <va-card-content>
        <p class="mb-3">{{ $t('pages.resources.vm.notFound') }}</p>
        <va-button icon="clear" color="info" @click="$router.go(-1)">{{ $t('pages.resources.vm.close') }}</va-button>
      </va-card-content>
    </va-card>
    <div v-else class="flex-center ma-3">
      <scaling-squares-spinner :animation-duration="1500" :size="85" color="#2c82e0" />
    </div>
    <va-modal v-model="showDiskRestoreModal" :ok-text="$t('pages.resources.common.ok')" :cancel-text="$t('pages.resources.common.cancel')" @ok="restoreDiskFile()">
      <template #header>
        <h2>
          <va-icon name="settings_backup_restore" color="info" />
          {{ $t('pages.resources.vm.restoreTitle') }}
        </h2>
      </template>
      <hr>
      <div>
        {{ $t('pages.resources.vm.restoreIntro') }} <b>{{
          JSON.parse(JSON.stringify(this.selectedBackup)).name.split('_')[0].toUpperCase() }}</b>
        <va-alert color="danger" border-color="danger" class="mb-4">
          {{ $t('pages.resources.vm.restoreLoss', { date: new Date(JSON.parse(JSON.stringify(this.selectedBackup)).start).toLocaleDateString() }) }}
        </va-alert>
        {{ $t('pages.resources.common.confirmAction') }}
      </div>
    </va-modal>
    <va-modal v-model="showDeleteModal" :ok-text="$t('pages.resources.common.ok')" :cancel-text="$t('pages.resources.common.cancel')" @ok="deleteBackup()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          {{ $t('pages.resources.vm.removeBackupTitle') }}
        </h2>
      </template>
      <hr>
      <div>
        {{ $t('pages.resources.vm.removeBackupIntro') }} <b>{{ JSON.parse(JSON.stringify(this.selectedBackup)).name }}</b><br>
        {{ $t('pages.resources.vm.backupFrom', { date: new Date(JSON.parse(JSON.stringify(this.selectedBackup)).start).toLocaleDateString() }) }}<br>
        {{ $t('pages.resources.common.confirmAction') }}
      </div>
    </va-modal>
  </div>
</template>
<script>
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'
import axios from 'axios'
import parser from 'cron-parser'
import { errorMessage } from '@/services/errorMessage'

export default defineComponent({
  name: 'VirtualMachineDetails',
  components: { ...spinners },
  data() {
    return {
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
    // The uuid, not the object: the lists are replaced by new objects at each refresh.
    'virtualMachine.uuid': function () {
      this.requestVmDetails()
      this.requestBackupList()
    },
    // The automatic refresh, or the button of the top bar: the backups may have changed.
    '$store.state.refresh.tick': function () {
      this.requestBackupList()
    }
  },
  computed: {
    columns() {
      return [
        { key: 'name', label: this.$t('pages.resources.vm.colDisk'), sortable: true },
        { key: 'start', label: this.$t('pages.resources.vm.colDate'), sortable: true },
        { key: 'actions', label: this.$t('pages.resources.vm.colActions') },
      ]
    },
    columns() {
      return [
        { key: 'name', label: this.$t('pages.resources.vm.colDisk'), sortable: true },
        { key: 'start', label: this.$t('pages.resources.vm.colDate'), sortable: true },
        { key: 'actions', label: this.$t('pages.resources.vm.colActions') },
      ]
    },
    virtualMachine() {
      const result = this.$store.state.resources.vmList.filter((item) => {
        return item.uuid == this.$route.params.id
      })
      return result[0]
    },
    hypervisor() {
      if (!this.virtualMachine) {
        return undefined
      }
      const result = this.$store.state.resources.hostList.filter((item) => {
        return item.id == this.virtualMachine.host
      })
      return result[0]
    },
    pool() {
      if (!this.virtualMachine) {
        return null
      }
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
      if (this.pool && this.pool.id) {
        return this.getPolicy(this.pool.policy_id)
      } else {
        return null
      }
    },
    memory2GiB() {
      if (!this.virtualMachine) {
        return ''
      }
      return ((this.virtualMachine.mem / 1024) / 1024).toFixed(0)
    },
    mostRecentBackup() {
      if (this.backupInfo.archives.length > 0) {
        return new Date(Math.max(...this.backupInfo.archives.map(e => new Date(e.start)))).toLocaleDateString()
      } else {
        return this.$t('pages.resources.common.na')
      }
    },
  oldestBackup() {
    if (this.backupInfo.archives.length > 0) {
      const value = new Date(Math.min(...this.backupInfo.archives.map(e => new Date(e.start)))).toLocaleDateString()
      this.lastOldestBackup = value
      return value
    }
    return this.lastOldestBackup || this.$t('pages.resources.common.na')
  },
    pages() {
      return (this.perPage && this.perPage !== 0)
        ? Math.ceil(this.backupInfo.archives.length / this.perPage)
        : this.filtered.length
    },
    nextRun() {
      if (this.policy && this.policy.schedule) {
        const options = {
          currentDate: new Date(),
          tz: 'Europe/Paris'
        }
        const interval = parser.parseExpression(this.policy.schedule, options)
        const result = `${new Date(interval.next()).toLocaleDateString()} - ${new Date(interval.next()).toLocaleTimeString()}`
        return result
      } else {
        return this.$t('pages.resources.common.na')
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
          this.$vaToast.init({ message: this.$t('pages.resources.vm.restoreSent'), color: 'light' })
          this.trackRestoreJob(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({ message: this.$t('pages.resources.vm.restoreStartFailed'), color: 'danger' })
        })
    },
    startBackup() {
      this.backingUp = true;
      axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/singlebackup/${this.virtualMachine.uuid}`, {}, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ message: this.$t('pages.resources.vm.backupRequested'), color: 'light' })
          this.trackBackupJob(response.data.Location)
        })
        .catch(error => {
          this.backingUp = false;
          console.error(error)
          this.$vaToast.init({ message: this.$t('pages.resources.vm.backupFailed'), color: 'danger' })
        })
    },
    trackBackupJob(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          // RETRY: the backup waits for a free place.
          if (['PENDING', 'STARTED', 'RECEIVED', 'RETRY'].includes(response.data.state)) {
            setTimeout(() => {
              this.trackBackupJob(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.backingUp = false;
            // A machine that does not run is not backed up: the task ends well, nothing was copied.
            if (response.data.info?.status === 'skipped') {
              this.$vaToast.init({ message: this.$t('pages.resources.vm.backupSkipped'), color: 'warning' })
            } else {
              this.$vaToast.init({ message: this.$t('pages.resources.vm.backupDone'), color: 'success' })
            }
            this.requestBackupList()
          } else if (response.data.state === 'FAILURE') {
            this.backingUp = false;
            this.$vaToast.init({ message: this.$t('pages.resources.vm.backupFailed'), color: 'danger' })
          }
        })
        .catch(error => {
          this.backingUp = false;
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
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
          this.$vaToast.init({ message: this.$t('pages.resources.vm.deleteRequested'), color: 'light' })
          this.trackDeleteBackupJob(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({ message: this.$t('pages.resources.vm.deleteFailed'), color: 'danger' })
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
            this.$vaToast.init({ message: this.$t('pages.resources.vm.deleteDone'), color: 'success' })
            this.requestBackupList()
          } else if (response.data.state === 'FAILURE') {
            this.$vaToast.init({ message: this.$t('pages.resources.vm.deleteFailed'), color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
            color: "danger"
          })
        })
    },
    trackRestoreJob(location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: { 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          if (['PENDING', 'STARTED', 'RECEIVED', 'RETRY'].includes(response.data.state)) {
            setTimeout(() => {
              this.trackRestoreJob(location)
            }, 2000)
          } else if (response.data.state === 'SUCCESS') {
            this.$vaToast.init({ message: this.$t('pages.resources.vm.restored'), color: 'success' })
          } else if (response.data.state === 'FAILURE') {
            this.$vaToast.init({ message: this.$t('pages.resources.vm.restoreFailed'), color: 'danger' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
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
            this.$vaToast.init({ title: response.data.state, message: this.$t('pages.resources.vm.unlocked'), color: 'success' })
          }
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.vm.unlockFailed'),
            message: errorMessage(error),
            color: 'danger'
          })
        })
    },
    requestBorgBreakLock() {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine.uuid}/breaklock`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$vaToast.init({ title: response.data.state, message: this.$t('pages.resources.vm.unlocking'), color: 'light' })
          this.getBorgBreakLock(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
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
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
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
              title: this.$t('pages.resources.common.unexpectedError'),
              message: errorMessage(error),
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
                label: !status.exists ? 'pages.resources.vm.storageNotFound' : !status.readable ? 'pages.resources.vm.storageNoRead' : 'pages.resources.vm.storageAvailable',
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
            title: this.$t('pages.resources.common.unexpectedError'),
            message: errorMessage(error),
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
              title: this.$t('pages.resources.common.unexpectedError'),
              message: errorMessage(error),
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