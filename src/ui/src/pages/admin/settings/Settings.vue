<template>
  <va-card>
    <va-card-title>
      <div class="header">
        <h1>{{ $t('pages.settings.title') }}</h1>
        <div>
          <va-button class="mr-2" icon="refresh" color="info" @click="load">{{ $t('pages.settings.refresh') }}</va-button>
          <va-button :disabled="!changed || !valid" :loading="saving" @click="save">{{ $t('pages.settings.save') }}</va-button>
        </div>
      </div>
    </va-card-title>
    <va-card-content>
      <section v-for="section in sections" :key="section.id" class="section">
        <h3 class="mb-1">{{ $t(`pages.settings.section.${section.id}`) }}</h3>
        <p class="va-text-secondary mb-3">{{ $t(`pages.settings.sectionHelp.${section.id}`) }}</p>
        <div class="fields">
          <div v-for="field in section.fields" :key="field" class="field">
            <va-input v-model.number="form[field]" type="number" :min="limit(field).min" :max="limit(field).max"
              :label="$t(`pages.settings.field.${field}`)"
              :rules="[(v) => validValue(field, v) || $t('pages.settings.range', { min: limit(field).min, max: limit(field).max })]">
              <template #appendInner>
                <span class="unit">{{ $t(`pages.settings.unit.${field}`) }}</span>
              </template>
            </va-input>
            <p class="hint">{{ $t(`pages.settings.fieldHelp.${field}`) }}</p>
          </div>
        </div>
        <p v-if="section.id === 'backups'" class="mt-2">
          {{ $t('pages.settings.runningNow') }} <b>{{ running }}</b>
        </p>
      </section>
      <p class="va-text-secondary mt-3">{{ $t('pages.settings.environmentNote') }}</p>
    </va-card-content>
  </va-card>
</template>

<script>
import { defineComponent } from "vue";
import axios from "axios";

// The values an administrator can change, grouped. Their bounds come from the API.
const SECTIONS = [
  { id: "backups", fields: ["backup_concurrency", "storage_alert_percent"] },
  { id: "history", fields: ["task_history_retention_days", "audit_retention_days", "file_browser_ttl_minutes"] },
  { id: "security", fields: ["jwt_lifetime_minutes", "login_max_attempts", "login_lock_minutes"] },
];
const FIELDS = SECTIONS.flatMap((section) => section.fields);

export default defineComponent({
  name: "Settings",
  data() {
    return {
      sections: SECTIONS,
      form: Object.fromEntries(FIELDS.map((field) => [field, null])),
      saved: Object.fromEntries(FIELDS.map((field) => [field, null])),
      limits: {},
      running: 0,
      saving: false,
    };
  },
  computed: {
    changed() {
      return FIELDS.some((field) => this.form[field] !== this.saved[field]);
    },
    valid() {
      return FIELDS.every((field) => this.validValue(field, this.form[field]));
    },
  },
  methods: {
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    limit(field) {
      return this.limits[field] || { min: 1, max: 1000000 };
    },
    validValue(field, value) {
      const { min, max } = this.limit(field);
      return Number.isInteger(value) && value >= min && value <= max;
    },
    apply(data) {
      for (const field of FIELDS) {
        this.form[field] = data[field];
        this.saved[field] = data[field];
      }
      this.limits = data.limits;
      this.running = data.backups_running;
    },
    async load() {
      try {
        const { data } = await axios.get(
          `${this.$store.state.endpoint.api}/api/v1/settings`,
          { headers: this.headers() });
        this.apply(data);
      } catch (error) {
        this.$vaToast.init({
          title: this.$t('pages.settings.unableLoad'),
          message: error?.response?.data?.detail ?? error,
          color: "danger",
        });
      }
    },
    async save() {
      this.saving = true;
      try {
        // Only what changed is sent.
        const changes = Object.fromEntries(FIELDS.filter((field) => this.form[field] !== this.saved[field])
          .map((field) => [field, this.form[field]]));
        const { data } = await axios.put(
          `${this.$store.state.endpoint.api}/api/v1/settings`, changes, { headers: this.headers() });
        this.apply(data);
        this.$vaToast.init({ message: this.$t('pages.settings.saved'), color: "success" });
      } catch (error) {
        const detail = error?.response?.data?.detail;
        this.$vaToast.init({
          title: this.$t('pages.settings.unableSave'),
          message: typeof detail === "string" ? detail : error,
          color: "danger",
        });
      } finally {
        this.saving = false;
      }
    },
  },
  mounted() {
    this.load();
  },
});
</script>

<style scoped>
.header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.section {
  margin-bottom: 1.75rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--va-background);
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(26rem, 1fr));
  gap: 1.25rem 2rem;
}

.unit {
  opacity: 0.6;
  white-space: nowrap;
}

.hint {
  margin: 0.3rem 0 0;
  font-size: 0.8rem;
  opacity: 0.7;
  line-height: 1.4;
}
</style>
