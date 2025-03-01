<template>
  <div>
    <va-data-table :items="data" :columns="columns" :per-page="perPage" :current-page="currentPage">
      <template #cell(started)="{ value }">
        <va-chip v-if="value" size="small" square outline color="primary">
          {{ new Date(value * 1000).toLocaleTimeString() }}
        </va-chip>
        <div v-else>
          <b>N/A</b>
        </div>
      </template>
      <template #cell(target)="{ value }">
        <div>
          <va-chip size="small" square color="primary">
            {{ value }}
          </va-chip>
        </div>
      </template>
      <template #cell(runtime)="{ rowIndex }">
        <div v-if="data[rowIndex].state == 'STARTED'">
          <va-chip size="small" color="info">
            <va-icon name="loop" spin="counter-clockwise" />
          </va-chip>
        </div>
        <div v-else-if="data[rowIndex].runtime !== null">
          <va-chip size="small" square outline color="primary">
            {{
              new Date(data[rowIndex].runtime * 1000)
                .toISOString()
                .substr(11, 8)
            }}
          </va-chip>
        </div>
        <div v-else>
          <b>N/A</b>
        </div>
      </template>
      <template #cell(state)="{ value }">
        <va-chip v-if="value === 'STARTED'" size="small" color="info">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'SUCCESS'" size="small" color="success">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'FAILURE'" size="small" color="danger">
          {{ value }}
        </va-chip>
        <va-chip v-else-if="value === 'RECEIVED'" size="small" color="purple">
          QUEUED
        </va-chip>
      </template>
      <template #cell(args)="{ value }">
        {{ value.name }}
      </template>

      <template #cell(actions)="{ rowIndex }">
        <va-button-group gradient :rounded="false">
          <va-button icon="settings" @click="
            this.$router.push(
              `/resources/${data[rowIndex].targetPage}/${data[rowIndex].targetUuid}`
            )
            " :disabled="!data[rowIndex].targetUuid" />
          <va-button v-if="data[rowIndex].state == 'FAILURE'" icon="bug_report"
            @click="showTaskError(data[rowIndex])" />
        </va-button-group>
      </template>

      <template v-if="pagination" #bodyAppend>
        <tr>
          <td colspan="8" class="table--pagination">
            <va-pagination v-model="currentPage" input :pages="pages" size="small" />
          </td>
        </tr>
      </template>
    </va-data-table>
    <error-modal v-model="taskErrorToShow" :title="`Task logs (${selectedTask?.target})`"></error-modal>
  </div>
</template>
<script>
import axios from "axios";

import ErrorModal from "../modals/ErrorModal.vue";

export default {
  name: "backup-table",
  components: { ErrorModal },
  props: {
    pagination: { type: Boolean, default: false },
    perPage: { type: Number, default: 500 },
    data: { type: Array },
    columns: { type: Array },
  },
  data() {
    return {
      currentPage: 1,
      selectedTask: null,
      taskErrorToShow: null,
    };
  },
  computed: {
    pages() {
      if (this.pagination) {
        return this.perPage && this.perPage !== 0
          ? Math.ceil(this.data.length / this.perPage)
          : this.filtered.length;
      } else {
        return null;
      }
    },
  },
  methods: {
    showTaskError(task) {
      this.selectedTask = task;
      this.taskErrorToShow = "Retrieving logs…";
      axios
        .get(`${this.$store.state.endpoint.api}/api/v1/logs/${task.uuid}`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.$keycloak.token}`,
          },
        })
        .then((response) => {
          this.taskErrorToShow = JSON.parse(response.data).traceback;
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
  },
};
</script>
<style scoped>
.table--pagination {
  text-align: center;
  text-align: -webkit-center;
}

.consoleStyle {
  padding: 1% 1% 1% 1%;
  background: black;
  color: silver;
  font-size: 1em;
  border-radius: 5px;
  max-height: 5%;
  width: auto;
}
</style>
