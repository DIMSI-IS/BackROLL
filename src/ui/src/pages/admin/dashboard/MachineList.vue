<template>
  <div class="machine-list">
    <!-- With a long list the name is searched in all the machines, not only in the ones that are shown. -->
    <va-input v-if="machines.length > pageSize" v-model="search" class="search mt-3"
      :placeholder="$t('pages.dashboard.searchMachine')" clearable />
    <va-list v-if="visible.length" class="mt-3">
      <va-list-item v-for="machine in visible" :key="machine.uuid" :to="`/resources/virtualmachines/${machine.uuid}`">
        <va-list-item-section>
          <va-list-item-label>
            {{ machine.name }}
            <va-chip v-if="machine.state" size="small" square outline color="warning" class="not-running ml-2">
              {{ $t('pages.dashboard.notRunning', { state: machine.state }) }}
            </va-chip>
          </va-list-item-label>
          <va-list-item-label caption>{{ machine.detail }}</va-list-item-label>
        </va-list-item-section>
      </va-list-item>
    </va-list>
    <p v-else-if="search" class="no-match mt-3 mb-0">{{ $t('pages.dashboard.noMachineMatches') }}</p>
    <div v-if="remaining > 0" class="more mt-2">
      <va-button size="small" outline @click="shown += pageSize">
        {{ $t('pages.dashboard.showMore', { count: Math.min(pageSize, remaining), remaining }) }}
      </va-button>
    </div>
  </div>
</template>

<script>
// A list of machines of the dashboard: the first ones, a button for the next ones, and a search when it is long.
export default {
  name: "MachineList",
  props: {
    machines: { type: Array, required: true },
    pageSize: { type: Number, default: 10 },
  },
  data() {
    return { search: "", shown: this.pageSize };
  },
  computed: {
    matching() {
      const text = (this.search || "").trim().toLowerCase();
      return text ? this.machines.filter((machine) => machine.name.toLowerCase().includes(text)) : this.machines;
    },
    visible() {
      return this.matching.slice(0, this.shown);
    },
    remaining() {
      return Math.max(0, this.matching.length - this.shown);
    },
  },
  watch: {
    // A new search starts again from the first ones.
    search() {
      this.shown = this.pageSize;
    },
  },
};
</script>
