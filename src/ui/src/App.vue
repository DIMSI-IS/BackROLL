<template>
  <router-view />
</template>
<script>
export default {
  name: "app-main",
  props: ["refreshPool"],
  mounted() {
    setInterval(() => {
      //this.$store.dispatch("requestConnector")
      //this.$store.dispatch("requestPool")
      //this.$store.dispatch("requestHost")
      //this.$store.dispatch("requestPolicy")
      this.$store.dispatch("requestVirtualMachine");
      this.$store.dispatch("requestJob");
      this.$store.dispatch("requestStorage");
      this.$store.dispatch("requestExternalHook");
      this.$store.dispatch("requestBackupTask");
      this.$store.dispatch("requestRestoreTask");
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
