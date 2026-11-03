<template>
  <div class="refresh-control">
    <va-button
      flat
      icon="refresh"
      :loading="running"
      :title="$t('pages.navbar.refreshNow')"
      @click="refreshNow"
    />
    <va-select
      class="refresh-control__select"
      v-model="selected"
      :options="choices"
      text-by="text"
      value-by="value"
      :clearable="false"
      :title="$t('pages.navbar.autoRefresh')"
    />
    <span class="refresh-control__time" v-if="lastAt">{{ lastTime }}</span>
  </div>
</template>

<script>
export default {
  name: "refresh-control",
  data() {
    return {
      now: Date.now(),
      clock: null,
    };
  },
  computed: {
    choices() {
      return [
        { text: this.$t("pages.navbar.refreshOff"), value: 0 },
        { text: this.$t("pages.navbar.sec5"), value: 5 },
        { text: this.$t("pages.navbar.sec10"), value: 10 },
        { text: this.$t("pages.navbar.sec30"), value: 30 },
        { text: this.$t("pages.navbar.min1"), value: 60 },
      ];
    },
    running() {
      return this.$store.state.refresh.running;
    },
    lastAt() {
      return this.$store.state.refresh.lastAt;
    },
    lastTime() {
      return new Date(this.lastAt).toLocaleTimeString();
    },
    selected: {
      get() {
        return this.choices.find((c) => c.value === this.$store.state.refresh.seconds);
      },
      set(choice) {
        const value = choice && typeof choice === "object" ? choice.value : choice;
        this.$store.commit("setRefreshSeconds", value);
        if (value > 0) {
          this.$store.dispatch("refreshAll");
        }
      },
    },
  },
  methods: {
    refreshNow() {
      this.$store.dispatch("refreshAll");
    },
  },
};
</script>

<style lang="scss">
.refresh-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;

  &__select {
    width: 5.5rem;
  }

  &__time {
    font-size: 0.75rem;
    opacity: 0.7;
    white-space: nowrap;
  }

  @media screen and (max-width: 768px) {
    &__time {
      display: none;
    }
  }
}
</style>
