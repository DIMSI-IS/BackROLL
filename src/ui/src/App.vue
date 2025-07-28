<template>
  <router-view />
</template>
<script>
export default {
  name: "app-main",
  props: ["refreshPool"],
  mounted() {
    setInterval(() => {
      if (this.$store.state.token) {
        // Read-only data that can be refreshed without any conflict.

        this.$store.dispatch("requestJob");
        this.$store.dispatch("requestBackupTask");
        this.$store.dispatch("requestRestoreTask");

        this.$store.dispatch("requestVirtualMachine");
      }
    }, 10000);
  },
};
</script>

<style lang="scss">
@import "~@/sass/main.scss";

#app {
  font-family: "Source Sans Pro", Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

body {
  margin: 0;
  background: var(--va-background);
}
</style>
