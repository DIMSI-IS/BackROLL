<template>
  <div class="dashboard">
    <dashboard-charts />
    <dashboard-info-block />
  </div>
</template>

<script>
import DashboardCharts from './DashboardCharts'
import DashboardInfoBlock from './DashboardInfoBlock'

export default {
  name: 'dashboard',
  components: {
    DashboardCharts,
    DashboardInfoBlock
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
