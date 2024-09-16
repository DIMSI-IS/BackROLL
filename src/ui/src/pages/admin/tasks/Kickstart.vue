<template>
  <va-card>
    <va-card-title>
      Task kickstart
    </va-card-title>
    <va-card-content>
      <va-timeline vertical style="min-width: 200px;">
        <va-timeline-item color="success" :active="isValid(jobSelection) ? true : false">
          <template #before>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <va-select label="Available task(s)" v-model="jobSelection" :options="selectJob"
                  :loading="!this.$store.state.isjobTableReady">
                  <template #prependInner>
                    <va-icon name="work" size="small" color="primary" />
                  </template>
                </va-select>
              </va-card-content>
            </va-card>
          </template>
          <template #after>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Select type of task you want to kickstart
            </span>
          </template>
        </va-timeline-item>
        <va-timeline-item v-if="isValid(jobSelection) && jobSelection.mode != 'mounted'" color="success"
          :active="isValid(targetSelection) ? true : false">
          <template #before>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Define your task target
            </span>
          </template>
          <template #after>
            <va-card stripe stripe-color="info" class="mb-0">
              <va-card-content>
                <va-select v-if="jobSelection.mode === 'single'" label="Target" v-model="targetSelection"
                  :options="selectData" :loading="!this.$store.state.isvmTableReady" searchable highlight-matched-text>
                  <template #prependInner>
                    <va-icon name="adjust" size="small" color="primary" />
                  </template>
                </va-select>
                <va-select v-else label="Target" v-model="targetSelection" :options="selectData2"
                  :loading="!this.$store.state.ispoolTableReady">
                  <template #prependInner>
                    <va-icon name="work" size="small" color="primary" />
                  </template>
                </va-select>
              </va-card-content>
            </va-card>
          </template>
        </va-timeline-item>
        <va-timeline-item v-else-if="isValid(jobSelection) && jobSelection.mode == 'mounted'" color="success"
          :active="isValid(jobSelection) ? true : false">
          <template #before>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Select virtual machine
            </span>
          </template>
          <template #after>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <virtual-machine-selector v-model="virtualMachineSelection" />
              </va-card-content>
            </va-card>
          </template>
        </va-timeline-item>
        <va-timeline-item color="success" v-if="isValid(targetSelection) && jobSelection.type === 'restore'"
          :active="isValid(backupSelection) ? true : false">
          <template #before>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <backup-selector v-if="isValid(targetSelection) && jobSelection.type === 'restore'"
                  v-model="backupSelection" :virtualMachine="targetSelection.value" :job="jobSelection.mode" />
              </va-card-content>
            </va-card>
          </template>
          <template #after>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Select backup you want to restore
            </span>
          </template>
        </va-timeline-item>
        <va-timeline-item color="success" v-if="isValid(virtualMachineSelection) && jobSelection.type === 'restore'"
          :active="isValid(backupSelection) ? true : false">
          <template #before>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <backup-selector v-if="isValid(virtualMachineSelection) && jobSelection.type === 'restore'"
                  v-model="backupSelection" :virtualMachine="virtualMachineSelection.value" :job="jobSelection.mode" />
              </va-card-content>
            </va-card>
          </template>
          <template #after>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Select backup you want to restore
            </span>
          </template>
        </va-timeline-item>

        <va-timeline-item color="success" v-if="isValid(backupSelection) && jobSelection.mode === 'mounted'"
          :active="isValid(backupSelection) ? true : false">
          <template #before>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              Select the storage where you want to restore
            </span>
          </template>
          <template #after>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <storage-selector v-if="isValid(virtualMachineSelection) && jobSelection.type === 'restore'"
                  v-model="storageSelection" />
              </va-card-content>
            </va-card>
          </template>

        </va-timeline-item>

        <va-timeline-item>
          <template #after>
            <div class="flex-center ma-3">
              <va-button
                v-if="(isValid(targetSelection) && jobSelection.type === 'backup') || (isValid(backupSelection) && jobSelection.type === 'restore')"
                icon="rocket_launch" @click="startJob()">
                Start task
              </va-button>
            </div>
          </template>
        </va-timeline-item>
      </va-timeline>

    </va-card-content>
  </va-card>
</template>
<script>
import BackupSelector from '@/components/virtualmachines/BackupSelector.vue'
import VirtualMachineSelector from '@/components/virtualmachines/VirtualMachineSelector.vue'
import StorageSelector from '@/components/virtualmachines/StorageSelector.vue'
import axios from 'axios'
import * as spinners from 'epic-spinners'

const taskFromQuery = {
  backup: 'Backup (VM)',
  restore: 'Disk Restore & Replace (VM)'
};

export default {
  name: 'KickstartJob',
  components: { ...spinners, BackupSelector, VirtualMachineSelector, StorageSelector },
  data() {
    return {
      jobList: [],
      jobSelection: {},
      targetSelection: {},
      backupSelection: {},
      virtualMachineSelection: {},
      storageSelection: {},
      taskValue: null,
    }
  },
  watch: {
    jobSelection: function () {
      this.targetSelection = {}
      this.virtualMachineSelection = {}
    },
    targetSelection: function () {
      this.backupSelection = {}
    }
  },
  mounted() {
    // Does not work on direct URL access maybe because this.$store.state.jobList is not ready yet.
    const taskValue = taskFromQuery[this.$route.query.task];
    this.jobSelection = this.selectJob.find(x => x.value == taskValue);
  },
  computed: {
    selectJob() {
      return this.$store.state.jobList.map(x => ({
        text: x.name,
        value: x.name,
        mode: x.mode,
        type: x.type
      }))
    },
    selectData() {
      return this.$store.state.resources.vmList.map(x => ({
        text: x.name,
        value: x.uuid
      }))
    },
    selectData2() {
      return this.$store.state.resources.poolList.map(x => ({
        text: x.name,
        value: x.id
      }))
    }
  },
  methods: {
    isValid(value) {
      if (Object.keys(value).length < 1) {
        return false
      } else {
        return true
      }
    },
    startJob() {
      //const self  = this
      let route = null
      let args = {}
      let url = null
      if (this.jobSelection.type === 'backup') {
        if (this.jobSelection.mode === 'single') {
          route = "/api/v1/tasks/singlebackup/"
          url = `${this.$store.state.endpoint.api}${route}${this.targetSelection.value}`
        } else {
          route = "/api/v1/tasks/poolbackup/"
          url = `${this.$store.state.endpoint.api}${route}${this.targetSelection.value}`
        }
      } else if (this.jobSelection.type === 'restore') {
        if (this.jobSelection.mode === 'mounted') {
          route = "/api/v1/tasks/restorespecificpath"
          url = `${this.$store.state.endpoint.api}${route}`
          args = {
            virtual_machine_id: this.virtualMachineSelection.value,
            backup_name: this.backupSelection.value,
            storage: this.storageSelection.value,
            mode: this.jobSelection.mode
          }
        } else {
          route = "/api/v1/tasks/restore/"
          url = `${this.$store.state.endpoint.api}${route}${this.targetSelection.value}`
          args = {
            virtual_machine_id: this.targetSelection.value,
            backup_name: this.backupSelection.value,
            storage: "",
            mode: this.jobSelection.mode
          }
        }

      }
      axios.post(url, args, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}` } })
        .then(response => {
          this.$store.dispatch("requestBackupTask", { token: this.$keycloak.token })
          this.$store.dispatch("requestRestoreTask", { token: this.$keycloak.token })
          if (this.jobSelection.type === 'restore') {
            this.$router.push('/admin/tasks/restore');
          } else {
            this.$router.push('/admin/tasks/backup');
          }
          this.$vaToast.init(({ title: response.data.state, message: `Task has been successfully triggered`, color: 'success' }))
        })
        .catch(function (error) {
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            this.$vaToast.init({ message: 'Task triggering has failed', title: 'Error', color: 'danger' })
          }
        })

    }
  }
}
</script>
<style scoped></style>