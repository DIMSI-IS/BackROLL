<template>
  <va-card>
    <va-card-title>
      Task kickstart
    </va-card-title>
    <va-card-content>
      <va-timeline vertical style="min-width: 200px;">
        <va-timeline-item color="success" :active="isValid(jobSelection) ? true : false">
          <template #before>
            <va-card
              stripe
              stripe-color="info"
            >
              <va-card-content>
                <va-select
                  label="Available task(s)"
                  v-model="jobSelection"
                  :options="selectJob"
                  :loading="!this.$store.state.isjobTableReady"
                >
                  <template #prependInner>
                    <va-icon
                      name="work"
                      size="small"
                      color="primary"
                    />
                  </template>
                </va-select>
              </va-card-content>
            </va-card>
          </template>
          <template #after>
            <span
              class="title title--info va-timeline-item__text"
              :style="{color: 'info'}"
            >
              Select type of task you want to kickstart
            </span>
          </template>
        </va-timeline-item>
        <va-timeline-item v-if="isValid(jobSelection)" color="success" :active="isValid(targetSelection) ? true : false">
          <template #before>
            <span
              class="title title--info va-timeline-item__text"
              :style="{color: 'info'}"
            >
              Define your task target
            </span>
          </template>
          <template #after>
            <va-card
              stripe
              stripe-color="info"
              class="mb-0"
            >
              <va-card-content>
                <va-select
                  v-if="jobSelection.mode === 'single'"
                  label="Target"
                  v-model="targetSelection"
                  :options="selectData"
                  :loading="!this.$store.state.isvmTableReady"
                >
                  <template #prependInner>
                    <va-icon
                      name="adjust"
                      size="small"
                      color="primary"
                    />
                  </template>
                </va-select>
                <va-select
                  v-else
                  label="Target"
                  v-model="targetSelection"
                  :options="selectData2"
                  :loading="!this.$store.state.ispoolTableReady"
                >
                  <template #prependInner>
                    <va-icon
                      name="work"
                      size="small"
                      color="primary"
                    />
                  </template>
                </va-select>
              </va-card-content>
            </va-card>
          </template>
        </va-timeline-item>

        <va-timeline-item color="success" v-if="isValid(targetSelection) && jobSelection.type === 'restore'" :active="isValid(backupSelection) ? true : false">
          <template #before>
            <va-card
              stripe
              stripe-color="info"
            >
              <va-card-content>
                <backup-selector
                  v-if="isValid(targetSelection) && jobSelection.mode === 'single' && jobSelection.type === 'restore'"
                  v-model="backupSelection"
                  :virtualMachine="targetSelection.value"
                />
              </va-card-content>
            </va-card>
          </template>
          <template #after>
            <span
              class="title title--info va-timeline-item__text"
              :style="{color: 'info'}"
            >
              Select backup you want to restore
            </span>
          </template>
        </va-timeline-item>

        <va-timeline-item>
          <template #after>
            <div class="flex-center ma-3">
              <va-button
                v-if="(isValid(targetSelection) && jobSelection.type === 'backup') || (isValid(backupSelection) && jobSelection.type === 'restore')"
                icon="rocket_launch"
                @click="startJob()"
              >
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
import axios from 'axios'
import * as spinners from 'epic-spinners'

export default {
  name: 'KickstartJob',
  components: { ...spinners, BackupSelector },
  data () {
    return {
      jobList: [],
      jobSelection: {},
      targetSelection: {},
      backupSelection: {}
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
    startJob () {
      const self  = this
      let route = null
      let args = {}
      if (this.jobSelection.type === 'backup') {
        if (this.jobSelection.mode === 'single') {
          route = "/api/v1/tasks/singlebackup/"
        } else {
          route = "/api/v1/tasks/poolbackup/"
        }
      } else if (this.jobSelection.type === 'restore') {
        route = "/api/v1/tasks/restore/"
        args = {
          virtual_machine_id: this.targetSelection.value,
          backup_name: this.backupSelection.value
        }
      }
      axios.post(`${this.$store.state.endpoint.api}${route}${this.targetSelection.value}`, args, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.dispatch("requestBackupTask", { token: this.$keycloak.token })
        this.$store.dispatch("requestRestoreTask", { token: this.$keycloak.token })
        this.$router.push('/admin/tasks/backup')
        this.$vaToast.init(({ title: response.data.state, message: `Task has been successfully triggered`, color: 'success' }))
      })
      .catch(function (error) {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          self.$vaToast.init(({ message: 'Task triggering has failed', title: 'Error', color: 'danger' }))
        }
      })

    }    
  }
}
</script>
<style scoped>

</style>