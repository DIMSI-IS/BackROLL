<template>
  <va-select
    label="Backup"
    v-model="backupSelection"
    :options="selectData"
    :loading="this.loadingBackups"
  >
    <template #prependInner>
      <va-icon
        name="today"
        size="small"
        color="primary"
      />
    </template>
  </va-select>
</template>
<script>
import { defineComponent } from 'vue'
import axios from 'axios'

export default defineComponent({
  name: 'BackupList',
  props: ['virtualMachine'],
  data () {
    return {
      loadingBackups: false,
      selectedBackup: null,
      backupInfo: {archives: []}
    }
  },
  watch: {
    virtualMachine: function () {
      this.requestBackupList()
    }
  },
  mounted () {
    this.requestBackupList()
  },
  computed: {
    selectData() {
      if (this.backupInfo.archives) {
        const result = this.backupInfo.archives.map(x => ({
          text: `${x.archive.split('_')[0].toUpperCase()} (${new Date(x.start).toLocaleDateString()})`,
          value: x.id
        }))
        return result.sort().reverse()
      }
    },
  },
  methods: {
    getBackupList (location) {
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
          this.$vaToast.init(({ message: response.data.status, color: 'danger' }))
        }
      })
      .catch(e => {
        console.log(e)
      })
    },
    requestBackupList () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine}/backups`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.loadingBackups = true
        this.getBackupList(response.data.Location)
      })
      .catch(e => {
        console.log(e)
      })
    },
  }
})
</script>