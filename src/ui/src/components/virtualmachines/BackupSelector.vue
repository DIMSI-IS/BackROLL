<template>
  <va-select :label="$t('pages.resources.selector.backup')" v-model="backupSelection" :options="selectDataVirtualMachine"
    :loading="this.loadingBackups">
    <template #prependInner>
      <va-icon name="today" size="small" color="primary" />
    </template>
  </va-select>
</template>
<script>
import { defineComponent } from 'vue'
import axios from 'axios'

export default defineComponent({
  name: 'BackupList',
  props: ['virtualMachine', 'job'],
  data() {
    return {
      loadingBackups: false,
      selectedBackup: null,
      backupInfo: { archives: [] }
    }
  },
  watch: {
    virtualMachine: function () {
      this.requestBackupList()
    }
  },
  mounted() {
    this.requestBackupList()
  },
  computed: {
    selectDataVirtualMachine() {
      if (this.backupInfo.archives) {
        // The backups of folders and files are not disks: they are restored from the file browser.
        const result = this.backupInfo.archives.filter(x => !x.name.startsWith('files_')).map(x => ({
          text: `${x.archive.split('_')[0].toUpperCase()} (${new Date(x.start).toLocaleDateString()} ${new Date(x.start).toLocaleTimeString()})`,
          value: x.name
        }))
        return result.sort().reverse()
      }
      return [];
    },
  },
  methods: {
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
            message: error,
            color: "danger"
          })
        })
    },
    requestBackupList() {
      const urlToCall = `${this.$store.state.endpoint.api}/api/v1/virtualmachines/${this.virtualMachine}/backups`;
      axios.get(urlToCall, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.loadingBackups = true
          this.getBackupList(response.data.Location)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.resources.common.unexpectedError'),
            message: error,
            color: "danger"
          })
        })
    },
  }
})
</script>