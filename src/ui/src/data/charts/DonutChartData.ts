let generatedData: {
  labels: string[];
  datasets: {label: string; backgroundColor: string[]; data: number[]}[];
}

export const getDonutChartData = (themes: ColorThemes, poolLabels: string[], poolData: number[]) => {
  console.log(themes, poolData, poolData);
  if (generatedData) {
    generatedData.datasets[0].backgroundColor = [themes.variables.danger, themes.variables.info, themes.variables.primary]
  } else {
    generatedData = {
      labels: poolLabels,
      datasets: [{
        label: 'VM distribution by pool',
        backgroundColor: [themes.variables.primary, themes.variables.warning],
        data: poolData,
      }],
    }
  }
  console.log(themes, poolData, poolData);
  return generatedData
}
