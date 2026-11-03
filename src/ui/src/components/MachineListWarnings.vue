<template>
  <div v-if="$store.state.resources.vmWarnings.length" class="machine-list-warnings">
    <va-alert v-for="warning in $store.state.resources.vmWarnings" :key="warning" color="warning" icon="warning" class="mb-2"
      data-testid="machine-list-warning">
      {{ warning }}
    </va-alert>
  </div>
</template>

<script>
export default {
  name: 'machine-list-warnings',
}
</script>
