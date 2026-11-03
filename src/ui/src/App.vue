<template>
  <router-view />
</template>
<script>
export default {
  name: "app-main",
  props: ["refreshPool"],
  beforeUnmount() {
    clearInterval(this.timer);
  },
  mounted() {
    // A session restored after a page refresh has not gone through the login page,
    // which is what loads the lists.
    if (this.$store.state.token) {
      [
        "requestJob",
        "requestBackupTask",
        "requestRestoreTask",
        "requestPool",
        "requestHost",
        "requestVirtualMachine",
        "requestPolicy",
        "requestStorage",
        "requestConnector",
        "requestExternalHook",
      ].forEach((action) => this.$store.dispatch(action));
    }

    // One check per second: the period is chosen in the top bar and can change at any time.
    // Nothing is loaded while the tab is hidden.
    this.timer = setInterval(() => {
      const refresh = this.$store.state.refresh;
      if (!this.$store.state.token || refresh.seconds === 0 || document.hidden) {
        return;
      }
      if (refresh.lastAt === null || Date.now() - refresh.lastAt >= refresh.seconds * 1000) {
        this.$store.dispatch("refreshAll");
      }
    }, 1000);
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
