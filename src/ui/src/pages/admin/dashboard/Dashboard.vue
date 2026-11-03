<template>
  <div class="dashboard">
    <dashboard-attention />
    <machine-list-warnings />
    <div class="row">
      <div class="flex xs12 xl8">
        <dashboard-info-block part="counters" />
        <dashboard-activity />
      </div>
      <div class="flex xs12 xl4">
        <dashboard-info-block part="storage" />
      </div>
    </div>
    <dashboard-protection />
    <dashboard-charts />
  </div>
</template>

<script>
import DashboardActivity from './DashboardActivity'
import DashboardAttention from './DashboardAttention'
import DashboardProtection from './DashboardProtection'
import DashboardCharts from './DashboardCharts'
import DashboardInfoBlock from './DashboardInfoBlock'
import MachineListWarnings from '@/components/MachineListWarnings.vue'

export default {
  name: 'dashboard',
  components: {
    DashboardActivity,
    DashboardAttention,
    DashboardProtection,
    DashboardCharts,
    DashboardInfoBlock,
    MachineListWarnings
  },
}
</script>

<style lang="scss">
.row-equal .flex {
  .va-card {
    height: 100%;
  }
}

.row:first-child {
  margin-top: -0.75rem !important;
}

.row:last-child {
  margin-bottom: -0.75rem !important;
}

.dashboard {
  .va-card {
    margin-bottom: 0 !important;

    &__title {
      display: flex;
      justify-content: space-between;
    }
  }
}
</style>
