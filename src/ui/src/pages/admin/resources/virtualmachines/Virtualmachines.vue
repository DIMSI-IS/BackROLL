<template>
  <va-card>
    <va-card-title>
      <h1>Virtual Machines</h1>
    </va-card-title>
    <va-card-content>
      <div class="row">
        <va-input class="flex mb-2 md6" placeholder="Filter..." v-model="filter" />
        <va-checkbox class="flex mb-2 md6" label="Look for an exact match" v-model="useCustomFilteringFn" />
      </div>
      <va-data-table :current-page="currentPage" :per-page="perPage" :items="$store.state.resources.vmList"
        :columns="columns" :filter="filter" :filter-method="customFilteringFn"
        @filtered="filteredCount = $event.items.length">
        <template #header(cpus)>CPU</template>
        <template #header(mem)>Memory</template>
        <template #header(host)>Hypervisor</template>
        <template #header(host_tag)>Tag(s)</template>
        <template #header(ssh)>SSH Connection</template>
        <template #cell(name)="{ value }">{{ value.toUpperCase() }}</template>
        <template #cell(cpus)="{ value }">
          <va-chip size="small" square outline>
            {{ value }} Cores
          </va-chip>
        </template>
        <template #cell(mem)="{ value }">
          <va-chip size="small" square outline>
            {{ ((value / 1024) / 1024).toFixed(0) }} GiB
          </va-chip>
        </template>
        <template #cell(host)="{ value }">
          <va-chip v-if="value" size="small" square @click="this.$router.push('/admin/resources/hypervisors')">
            {{ getHost(value).hostname }}
          </va-chip>
        </template>
        <template #cell(host_tag)="{ value }">
          <va-chip v-if="value" size="small" square outline>
            {{ value }}
          </va-chip>
        </template>
        <template #cell(state)="{ value }">
          <va-chip size="small" :color="value === 'Running' ? 'success' : 'dark'">
            <va-icon :name="value === 'Running' ? 'bolt' : 'power_off'" />
            <span style="padding-left: 5px;">
              {{ value }}
            </span>
          </va-chip>
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button icon="settings"
              @click="this.$router.push(`/resources/virtualmachines/${$store.state.resources.vmList[rowIndex].uuid}`)" />
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
      <div v-if="!$store.state.isvmTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
</template>

<script>
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

export default defineComponent({
  name: 'VMsTable',
  components: { ...spinners },
  data() {
    return {
      columns: [
        { key: 'name', sortable: true },
        { key: 'cpus', sortable: true },
        { key: 'mem', sortable: true },
        { key: 'host', sortable: true },
        { key: 'host_tag', sortable: true },
        { key: 'state', sortable: true },
        { key: 'actions' }
      ],
      selectedHost: null,
      perPage: 25,
      currentPage: 1,
      filter: '',
      useCustomFilteringFn: false,
      filteredCount: this.$store.state.resources.vmList.length
    }
  },
  computed: {
    pages() {
      return (this.perPage && this.perPage !== 0)
        ? Math.ceil(this.$store.state.resources.vmList.length / this.perPage)
        : this.filtered.length
    },
    customFilteringFn() {
      return this.useCustomFilteringFn ? this.filterExact : undefined
    }
  },
  mounted () {
    this.$store.dispatch("requestVirtualMachine", { token: this.$keycloak.token })
  },
  methods: {
    filterExact(source) {
      if (this.filter === '') {
        return true
      }

      return source?.toString?.() === this.filter
    },
    getHost(id) {
      const result = this.$store.state.resources.hostList.filter((item) => {
        return item.id == id
      })
      return result[0]
    }
  }
})
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}

.table-example--pagination {
  text-align: center;
  text-align: -webkit-center;
}
</style>
