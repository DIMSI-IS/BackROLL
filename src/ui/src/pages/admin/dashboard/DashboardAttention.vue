<template>
  <div v-if="machines.length" class="row attention">
    <div class="flex xs12">
      <va-card stripe stripe-color="danger">
        <va-card-title>
          <span>
            <va-icon name="report_problem" color="danger" />
            {{ $t('pages.dashboard.attention.title', { count: machines.length }) }}
          </span>
        </va-card-title>
        <va-card-content>
          <p class="mb-3">{{ $t('pages.dashboard.attention.help') }}</p>
          <va-list>
            <va-list-item v-for="machine in machines" :key="machine.vm_uuid + machine.disk" class="machine">
              <va-list-item-section>
                <va-list-item-label>{{ machine.vm_name }} · {{ machine.disk }}</va-list-item-label>
                <va-list-item-label caption>{{ machine.message }}</va-list-item-label>
                <va-list-item-label caption>
                  {{ $t('pages.dashboard.attention.since', { when: when(machine.since) }) }}
                </va-list-item-label>
              </va-list-item-section>
              <va-list-item-section v-if="$store.getters.isAdmin" icon>
                <va-button size="small" color="danger" outline class="resume" @click="ask(machine)">
                  {{ $t('pages.dashboard.attention.resume') }}
                </va-button>
              </va-list-item-section>
            </va-list-item>
          </va-list>
        </va-card-content>
      </va-card>
    </div>

    <va-modal v-model="confirm" :ok-text="$t('pages.dashboard.attention.resumeOk')"
      :cancel-text="$t('pages.dashboard.attention.cancel')" @ok="resume">
      <template #header>
        <h2>{{ $t('pages.dashboard.attention.resumeTitle') }}</h2>
      </template>
      <hr>
      <div v-if="chosen">
        {{ $t('pages.dashboard.attention.resumeBody', { name: chosen.vm_name, disk: chosen.disk }) }}
      </div>
    </va-modal>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "DashboardAttention",
  data() {
    return { machines: [], confirm: false, chosen: null };
  },
  watch: {
    "$store.state.refresh.tick"() {
      this.load();
    },
  },
  methods: {
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    when(value) {
      return value ? new Date(value).toLocaleString() : "";
    },
    async load() {
      try {
        const { data } = await axios.get(`${this.$store.state.endpoint.api}/api/v1/attention`,
          { headers: this.headers() });
        this.machines = data;
      } catch (error) {
        // The card only appears when there is something to say: a failed read must not show an empty alert.
        console.error(error);
      }
    },
    ask(machine) {
      this.chosen = machine;
      this.confirm = true;
    },
    async resume() {
      const machine = this.chosen;
      try {
        await axios.post(
          `${this.$store.state.endpoint.api}/api/v1/attention/${encodeURIComponent(machine.vm_uuid)}/resolve`,
          null, { params: { disk: machine.disk }, headers: this.headers() });
        this.$vaToast.init({ message: this.$t("pages.dashboard.attention.resumed", { name: machine.vm_name }), color: "success" });
      } catch (error) {
        this.$vaToast.init({ message: this.$t("pages.dashboard.attention.resumeFailed"), color: "danger" });
      }
      await this.load();
    },
  },
  mounted() {
    this.load();
  },
};
</script>

<style scoped>
.attention {
  margin-bottom: 0.75rem;
}
</style>
