let generatedData: {
  labels: string[];
  datasets: {label: string; backgroundColor: string[]; data: number[]}[];
}

export const getDonutChartData = (themes: ColorThemes, poolLabels: string[], poolData: number[]) => {
  if (generatedData) {
    generatedData.datasets[0].backgroundColor = [themes.danger, themes.info, themes.primary]
  } else {
    generatedData = {
      labels: poolLabels,
      datasets: [{
        label: 'VM distribution by pool',
        backgroundColor: [themes.primary, themes.warning],
        data: poolData,
      }],
    }
  }

  return generatedData
}
