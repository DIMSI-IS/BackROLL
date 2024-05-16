<template>
  <component
    ref="chart"
    class='va-chart'
    :is="chartComponent"
    :options="options"
    :data="chartData"
  />
</template>

<script>
import { chartTypesMap } from './VaChartConfigs'
import { Pie,Bubble, Doughnut, Bar , Line} from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement)

export default {
  name: 'va-chart',
  props: {
    chartData: {},
    options: {},
    type: {
      validator (type) {
        return type in chartTypesMap
      },
    },
  },
  mounted() {
    console.log(this.chartData);
  },
  components: { Pie,Bubble,Doughnut, Bar, Line } ,
  computed: {
    chartComponent () {
      return chartTypesMap[this.type]
    },
  },
  methods: {
    refresh() {
      this.$refs.chart.refresh()
    },
  }
}
</script>

<style lang='scss'>
.va-chart {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  > * {
    height: 100%;
    width: 100%;
  }

  canvas {
    width: 100%;
    height: auto;
    min-height: 320px;
  }
}
</style>
