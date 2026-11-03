<template>
  <va-card>
    <va-card-title>
      <div class="header">
        <h1>{{ $t('pages.audit.title') }}</h1>
        <va-button icon="refresh" color="info" @click="load">{{ $t('pages.audit.refresh') }}</va-button>
      </div>
    </va-card-title>
    <va-card-content>
      <div class="filters mb-3">
        <va-input v-model="filters.username" :label="$t('pages.audit.user')" clearable @keydown.enter="search" />
        <va-input v-model="filters.action" :label="$t('pages.audit.action')" clearable @keydown.enter="search" />
        <va-select v-model="filters.source" class="source-filter" :label="$t('pages.audit.source')" :options="sourceOptions"
          text-by="text" value-by="value" :clearable="false" @update:modelValue="search" />
        <simple-checkbox v-model="filters.failedOnly" :label="$t('pages.audit.failedOnly')" @update:modelValue="search" />
        <va-button @click="search">{{ $t('pages.audit.search') }}</va-button>
      </div>

      <va-data-table :no-data-html="$t('pages.common.noItems')" :items="items" :columns="columns">
        <template #cell(created_at)="{ value }">
          {{ new Date(value).toLocaleString() }}
        </template>
        <template #cell(status_code)="{ value }">
          <va-chip size="small" outline square :color="value < 400 ? 'success' : 'danger'">
            {{ value < 400 ? $t('pages.audit.success') : value }}
          </va-chip>
        </template>
        <template #cell(username)="{ value }">
          {{ value || "-" }}
        </template>
        <template #cell(source)="{ value }">
          <va-chip size="small" outline square :color="value === 'ad' ? 'info' : 'secondary'" class="source">
            {{ value === 'ad' ? $t('pages.audit.sourceAd') : $t('pages.audit.sourceLocal') }}
          </va-chip>
        </template>
      </va-data-table>
      <div v-if="loading" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>

      <div class="footer mt-3">
        <span>{{ $t('pages.audit.entries', { total: total }) }}</span>
        <va-pagination v-if="pages > 1" v-model="page" :pages="pages" :visible-pages="5"
          @update:modelValue="load" />
      </div>
    </va-card-content>
  </va-card>
</template>

<script>
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import axios from "axios";

const PER_PAGE = 25;

export default defineComponent({
  name: "AuditLog",
  components: { ...spinners, SimpleCheckbox },
  data() {
    return {
      items: [],
      total: 0,
      page: 1,
      loading: false,
      filters: { username: "", action: "", failedOnly: false, source: "" },
    };
  },
  watch: {
    "$store.state.refresh.tick"() {
      this.load();
    },
  },
  computed: {
    columns() {
      return [
        { key: "created_at", label: this.$t("pages.audit.colTime") },
        { key: "username", label: this.$t("pages.audit.colUser") },
        { key: "source", label: this.$t("pages.audit.colSource") },
        { key: "action", label: this.$t("pages.audit.colAction") },
        { key: "detail", label: this.$t("pages.audit.colDetails") },
        { key: "status_code", label: this.$t("pages.audit.colResult") },
        { key: "ip_address", label: this.$t("pages.audit.colIp") },
      ];
    },
    sourceOptions() {
      return [
        { value: "", text: this.$t("pages.audit.sourceAll") },
        { value: "local", text: this.$t("pages.audit.sourceLocal") },
        { value: "ad", text: this.$t("pages.audit.sourceAd") },
      ];
    },
    pages() {
      return Math.ceil(this.total / PER_PAGE);
    },
  },
  methods: {
    search() {
      this.page = 1;
      this.load();
    },
    async load() {
      this.loading = true;
      try {
        const params = {
          limit: PER_PAGE,
          offset: (this.page - 1) * PER_PAGE,
          failed_only: this.filters.failedOnly,
        };
        if (this.filters.username) params.username = this.filters.username;
        if (this.filters.action) params.action = this.filters.action;
        if (this.filters.source) params.source = this.filters.source;

        const { data } = await axios.get(
          `${this.$store.state.endpoint.api}/api/v1/audit`,
          {
            params,
            headers: { Authorization: `Bearer ${this.$store.state.token}` },
          }
        );
        this.items = data.items;
        this.total = data.total;
      } catch (error) {
        console.error(error);
        this.$vaToast.init({
          title: this.$t('pages.audit.unableLoad'),
          message: error?.response?.data?.detail ?? error,
          color: "danger",
        });
      } finally {
        this.loading = false;
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
}

.filters {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
