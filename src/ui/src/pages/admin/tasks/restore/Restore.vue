<template>
  <task-page title="Restore" kickstart-title="Start restore task" kickstart-task="restore"
    :get-task-list="getTaskList" />
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
  computed: {
    getTaskList() {
      return (taskFilter) => {
        return Object.values(this.$store.state.restoreTaskList)
          .filter(taskFilter)
          .map(task => {
            const taskArg = task.args[0]
            return {
              uuid: task.uuid,
              name: task.name.replaceAll('_', ' '),
              target: taskArg?.name ?? "N/A",
              targetPage: "virtualmachines",
              targetUuid: taskArg?.uuid,
              started: task.started,
              ipAddress: task.ip_address,
              runtime: task.runtime,
              state: task.state,
            }
          })
      }
    },
  },
  mounted() {
    this.$store.dispatch("requestRestoreTask");
  },
})
</script>
