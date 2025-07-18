<template>
  <task-page title="Backups" kickstart-title="Start backup task" kickstart-task="backup" :get-task-list="getTaskList" />
</template>

<script>
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

import TaskTable from "@/components/tasks/TaskTable.vue"
import TaskPage from '@/components/tasks/TaskPage.vue'

export default defineComponent({
  name: 'BackupsTable',
  components: {
    ...spinners,
    TaskTable,
    TaskPage
  },
  mounted() {
    this.$store.dispatch("requestBackupTask", { token: this.$store.state.token });
  },
  computed: {
    getTaskList() {
      return (taskFilter) => {
        return Object.values(this.$store.state.backupTaskList)
          .filter(taskFilter)
          .filter(({ name }) => ['Single_VM_Backup', 'backup_subtask'].includes(name))
          .map(task => {
            const isPool = task.name == "Pool_VM_Backup"
            const taskArg = task.args[0]
            const poolId = taskArg?.pool_id
            return {
              uuid: task.uuid,
              name: task.name.replaceAll('_', ' '),
              target: isPool ? this.$store.state.resources.poolList.find(e => e.id == poolId)?.name : taskArg?.name ?? "N/A",
              targetPage: isPool ? "pools" : "virtualmachines",
              targetUuid: taskArg?.uuid,
              started: task.started,
              ipAddress: task.ip_address,
              runtime: isPool ? null : task.runtime,
              state: task.state
            }
          })
      }
    }
  },
})
</script>
