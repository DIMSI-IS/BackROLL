<template>
  <va-select
    label="Backup"
    v-model="backupSelection"
    :options="selectDataVirtualMachine"
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
  props: ['virtualMachine','job'],
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
    selectDataVirtualMachine() {
      if (this.backupInfo.archives) {
        const result = this.backupInfo.archives.map(x => ({
          text: `${x.archive.split('_')[0].toUpperCase()} (${new Date(x.start).toLocaleDateString()} ${new Date(x.start).toLocaleTimeString()})`,
          value: x.name
        }))
        return result.sort().reverse()
      }
      return [];
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
    getVirtualMachineBackupsFromPath(archives) {
      if(archives){
        this.loadingBackups = false;
        if(archives.length > 0) {
          this.backupInfo = archives;
        }
      }      
    },
    requestBackupList () {
      if(this.job == "mounted") {
        const urlToCall = `${this.$store.state.endpoint.api}/api/v1/virtualmachinebackupsfrompath`;

        let virtualMachineBackupsRequest = {}
        virtualMachineBackupsRequest.virtualMachineName = this.virtualMachine.substring(this.virtualMachine.lastIndexOf('/'))
        virtualMachineBackupsRequest.storagePath = this.virtualMachine.substring(0, this.virtualMachine.lastIndexOf('/'));

        axios.post(urlToCall, JSON.stringify(virtualMachineBackupsRequest), { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
          .then(response => {
            this.loadingBackups = true
            // this.getVirtualMachineBackupsFromPath(response.data.backups.archives)
            this.getBackupList(response.data.Location)
          })
          .catch(e => {
            console.log(e)
          })
      }
      else {
        const urlToCall = `${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine}/backups`;
        axios.get(urlToCall, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
        .then(response => {
          this.loadingBackups = true
          this.getBackupList(response.data.Location)
        })
        .catch(e => {
          console.log(e)
        })
      }
    },
  }
})
</script>