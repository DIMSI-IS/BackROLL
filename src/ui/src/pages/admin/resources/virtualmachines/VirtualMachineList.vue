<template>
  <va-card>
    <va-card-title>
      <ListHeader :title="$t('pages.resources.vm.title')" :dependencies-resolved="areDependenciesResolved"
        :dependencies-message="$t('pages.resources.vm.needHypervisor')" :go-button-title="$t('pages.resources.vm.goToHypervisors')"
        go-button-route="/admin/resources/hypervisors" />
    </va-card-title>
    <va-card-content>
      <machine-list-warnings />
      <div class="row">
        <va-input class="flex mb-2 md6" :placeholder="$t('pages.resources.vm.filter')" v-model="filter" />
        <simple-checkbox class="flex mb-2 md6" :label="$t('pages.resources.vm.exactMatch')" v-model="useCustomFilteringFn" />
      </div>
      <va-data-table :no-data-html="$t('pages.common.noItems')" :current-page="currentPage" :per-page="perPage" :items="$store.state.resources.vmList"
        :columns="columns" :filter="filter" :filter-method="customFilteringFn"
        @filtered="filteredCount = $event.items.length">
        <template #header(cpus)>{{ $t('pages.resources.vm.colCpu') }}</template>
        <template #header(mem)>{{ $t('pages.resources.vm.colMemory') }}</template>
        <template #header(host)>{{ $t('pages.resources.vm.colHypervisor') }}</template>
        <template #header(host_tag)>{{ $t('pages.resources.vm.colTags') }}</template>
        <template #header(ssh)>{{ $t('pages.resources.vm.colSsh') }}</template>
        <template #cell(name)="{ value }">{{ value.toUpperCase() }}</template>
        <template #cell(cpus)="{ value }">
          <va-chip size="small" square outline> {{ $t('pages.resources.vm.cores', { count: value }) }} </va-chip>
        </template>
        <template #cell(mem)="{ value }">
          <va-chip size="small" square outline>
            {{ (value / 1024 / 1024).toFixed(0) }} GiB
          </va-chip>
        </template>
        <template #cell(host)="{ value }">
          <va-chip v-if="value" size="small" square @click="this.$router.push('/admin/resources/hypervisors')">
            {{ getHost(value)?.hostname }}
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
            <span style="padding-left: 5px">
              {{ value }}
            </span>
          </va-chip>
        </template>
        <template #cell(actions)="{ rowIndex }">
          <va-button-group gradient :rounded="false">
            <va-button icon="info" @click="
              this.$router.push(
                `/resources/virtualmachines/${$store.state.resources.vmList[rowIndex].uuid}`
              )
              " />
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
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";
import MachineListWarnings from "@/components/MachineListWarnings.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";

import ListHeader from "@/components/lists/ListHeader.vue";

export default defineComponent({
  name: "VMsTable",
  components: {
    ...spinners,
    ListHeader,
    SimpleCheckbox,
    MachineListWarnings,
  },
  data() {
    return {
      selectedHost: null,
      perPage: 25,
      currentPage: 1,
      filter: "",
      useCustomFilteringFn: false,
      filteredCount: this.$store.state.resources.vmList.length,
    };
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.vm.colName"), sortable: true },
        { key: "cpus", label: this.$t("pages.resources.vm.colCpu"), sortable: true },
        { key: "mem", label: this.$t("pages.resources.vm.colMemory"), sortable: true },
        { key: "host", label: this.$t("pages.resources.vm.colHypervisor"), sortable: true },
        { key: "host_tag", label: this.$t("pages.resources.vm.colTags"), sortable: true },
        { key: "state", label: this.$t("pages.resources.vm.colState"), sortable: true },
        { key: "actions", label: this.$t("pages.resources.vm.colActions") },
      ];
    },
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.vm.colName"), sortable: true },
        { key: "cpus", label: this.$t("pages.resources.vm.colCpu"), sortable: true },
        { key: "mem", label: this.$t("pages.resources.vm.colMemory"), sortable: true },
        { key: "host", label: this.$t("pages.resources.vm.colHypervisor"), sortable: true },
        { key: "host_tag", label: this.$t("pages.resources.vm.colTags"), sortable: true },
        { key: "state", label: this.$t("pages.resources.vm.colState"), sortable: true },
        { key: "actions", label: this.$t("pages.resources.vm.colActions") },
      ];
    },
    areDependenciesResolved() {
      // Prevent showing irrelevant alert by checking if the table is ready.
      return (
        !this.$store.state.isHostTableReady ||
        this.$store.state.resources.hostList.length > 0
      );
    },
    pages() {
      return this.perPage && this.perPage !== 0
        ? Math.ceil(this.$store.state.resources.vmList.length / this.perPage)
        : this.filtered.length;
    },
    customFilteringFn() {
      return this.useCustomFilteringFn ? this.filterExact : undefined;
    },
  },
  methods: {
    filterExact(source) {
      if (this.filter === "") {
        return true;
      }

      return source?.toString?.() === this.filter;
    },
    getHost(id) {
      const result = this.$store.state.resources.hostList.filter((item) => {
        return item.id == id;
      });
      return result[0];
    },
  },
  mounted() {
    this.$store.dispatch("requestVirtualMachine");
  },
});
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
