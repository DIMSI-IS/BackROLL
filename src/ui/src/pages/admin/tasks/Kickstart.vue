<template>
  <va-card>
    <va-card-title>
      {{ $t('pages.tasks.kickstart.title') }}
    </va-card-title>
    <va-card-content>
      <va-timeline vertical style="min-width: 200px;">
        <va-timeline-item color="success" :active="isValid(jobSelection) ? true : false">
          <template #before>
            <va-card stripe stripe-color="info">
              <va-card-content>
                <va-select :label="$t('pages.tasks.kickstart.availableTasks')" v-model="jobSelection" :options="selectJob"
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
              {{ $t('pages.tasks.kickstart.selectType') }}
            </span>
          </template>
        </va-timeline-item>
        <va-timeline-item v-if="isValid(jobSelection)" color="success"
          :active="isValid(targetSelection) ? true : false">
          <template #before>
            <span class="title title--info va-timeline-item__text" :style="{ color: 'info' }">
              {{ $t('pages.tasks.kickstart.defineTarget') }}
            </span>
          </template>
          <template #after>
            <va-card stripe stripe-color="info" class="mb-0">
              <va-card-content>
                <va-select v-if="jobSelection.mode === 'single'" :label="$t('pages.tasks.kickstart.target')" v-model="targetSelection"
                  :options="vmTargetOptions" :loading="!this.$store.state.isvmTableReady" searchable
                  highlight-matched-text>
                  <template #prependInner>
                    <va-icon name="adjust" size="small" color="primary" />
                  </template>
                </va-select>
                <va-select v-else :label="$t('pages.tasks.kickstart.target')" v-model="targetSelection" :options="poolTargetOptions"
                  :loading="!this.$store.state.isPoolTableReady" searchable highlight-matched-text>
                  <template #prependInner>
                    <va-icon name="work" size="small" color="primary" />
                  </template>
                </va-select>
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
              {{ $t('pages.tasks.kickstart.selectBackup') }}
            </span>
          </template>
        </va-timeline-item>
        <va-timeline-item>
          <template #after>
            <div class="flex-center ma-3">
              <va-button
                v-if="(isValid(targetSelection) && jobSelection.type === 'backup') || (isValid(backupSelection) && jobSelection.type === 'restore')"
                icon="rocket_launch" @click="startJob()">
                {{ $t('pages.tasks.kickstart.start') }}
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
import axios from 'axios'
import * as spinners from 'epic-spinners'

// TODO Better use simple keys than fullnames.
const taskFromQuery = {
  backup: 'Backup (VM)',
  restore: 'Disk Restore & Replace (VM)'
};

export default {
  name: 'KickstartJob',
  components: { ...spinners, BackupSelector },
  data() {
    return {
      jobList: [],
      jobSelection: {},
      targetSelection: {},
      backupSelection: {},
      taskValue: null,
    }
  },
  watch: {
    jobSelection: function () {
      this.targetSelection = {}
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
    vmTargetOptions() {
      return this.$store.state.resources.vmList.map(x => ({
        text: x.name,
        value: x.uuid
      }))
    },
    poolTargetOptions() {
      return this.$store.state.resources.poolList.map(x => ({
        text: x.name,
        value: x.id
      }))
    }
  },
  methods: {
    isValid(value) {
      if (!value || typeof value !== 'object' || Object.keys(value).length < 1) {
        return false
      } else {
        return true
      }
    },
    startJob() {
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
        route = "/api/v1/tasks/restore/"
        url = `${this.$store.state.endpoint.api}${route}${this.targetSelection.value}`
        args = {
          virtual_machine_id: this.targetSelection.value,
          backup_name: this.backupSelection.value,
          storage: "",
          mode: this.jobSelection.mode
        }
      }
      axios.post(url, args, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$store.dispatch("requestBackupTask")
          this.$store.dispatch("requestRestoreTask")
          if (this.jobSelection.type === 'restore') {
            this.$router.push('/admin/tasks/restore');
          } else {
            this.$router.push('/admin/tasks/backup');
          }
          this.$vaToast.init({ title: response.data.state, message: this.$t('pages.tasks.kickstart.triggered'), color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.tasks.kickstart.errorTitle'),
            message: this.$t('pages.tasks.kickstart.triggerFailed'),
            color: 'danger'
          })
        })

    }
  }
}
</script>
<style scoped></style>