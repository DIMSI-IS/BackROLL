<template>
  <router-view/>
</template>
<script>

export default {
  name: 'app-main',
  props: [ 'refreshPool' ],
  mounted () {    
    this.$store.dispatch("requestConnector", { token: this.$keycloak.token })
    this.$store.dispatch("requestPool", { token: this.$keycloak.token })
    this.$store.dispatch("requestHost", { token: this.$keycloak.token })
    this.$store.dispatch("requestPolicy", { token: this.$keycloak.token })
    this.$store.dispatch("requestVirtualMachine", { token: this.$keycloak.token })
    this.$store.dispatch("requestJob", { token: this.$keycloak.token })
    this.$store.dispatch("requestStorage", { token: this.$keycloak.token })
    this.$store.dispatch("requestExternalHook", { token: this.$keycloak.token })
    this.$store.dispatch("requestBackupTask", { token: this.$keycloak.token })
    this.$store.dispatch("requestRestoreTask", { token: this.$keycloak.token })
  }
}
</script>

<style lang="scss">
@import './sass/main.scss';
#app {
  font-family: 'Source Sans Pro', Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

body {
  margin: 0;
  background: var(--va-background);
}
</style>
