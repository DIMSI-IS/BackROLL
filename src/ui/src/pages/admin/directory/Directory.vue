<template>
  <div class="directory">
    <va-card>
      <va-card-title>
        <div class="header">
          <h1>{{ $t('pages.directory.title') }}</h1>
          <div>
            <va-button class="mr-2" icon="refresh" color="info" @click="load">{{ $t('pages.directory.refresh') }}</va-button>
            <va-button class="mr-2 test-connection" icon="network_check" color="info" outline :loading="testing"
              @click="testConnection">{{ $t('pages.directory.test') }}</va-button>
            <va-button class="save" :disabled="!changed || !validForm" :loading="saving" @click="save">{{ $t('pages.directory.save') }}</va-button>
          </div>
        </div>
      </va-card-title>
      <va-card-content>
        <va-alert color="info" icon="info" dense class="mb-3">{{ $t('pages.directory.intro') }}</va-alert>

        <div class="enable mb-3">
          <simple-checkbox toggle v-model="form.enabled" :label="$t('pages.directory.enabled')" />
          <va-chip size="small" square outline :color="saved.enabled ? 'success' : 'secondary'" class="ml-3">
            {{ saved.enabled ? $t('pages.directory.statusOn') : $t('pages.directory.statusOff') }}
          </va-chip>
        </div>

        <div class="fields">
          <div class="field">
            <va-input v-model="form.server_url" :label="$t('pages.directory.serverUrl')" placeholder="ldaps://dc01.example.com:636"
              :rules="[urlRule]" />
            <p class="hint">{{ $t('pages.directory.serverUrlHint') }}</p>
          </div>
          <div class="field">
            <va-input v-model="form.base_dn" :label="$t('pages.directory.baseDn')" placeholder="DC=example,DC=com" />
            <p class="hint">{{ $t('pages.directory.baseDnHint') }}</p>
          </div>
          <div class="field">
            <va-input v-model="form.bind_dn" :label="$t('pages.directory.bindDn')" placeholder="svc-backroll@example.com" />
            <p class="hint">{{ $t('pages.directory.bindDnHint') }}</p>
          </div>
          <div class="field">
            <va-input v-model="form.bind_password" type="password" :label="$t('pages.directory.bindPassword')"
              :placeholder="config.has_bind_password ? $t('pages.directory.bindPasswordKeep') : ''" autocomplete="new-password" />
            <p class="hint">{{ $t('pages.directory.bindPasswordHint') }}</p>
          </div>
          <div class="field wide">
            <va-input v-model="form.user_filter" :label="$t('pages.directory.userFilter')" :rules="[filterRule]" />
            <p class="hint">{{ $t('pages.directory.userFilterHint') }}</p>
          </div>
          <div class="field">
            <va-input v-model.number="form.timeout_seconds" type="number" min="2" max="60" :label="$t('pages.directory.timeout')">
              <template #appendInner><span class="unit">s</span></template>
            </va-input>
          </div>
        </div>

        <div class="checks mt-3">
          <simple-checkbox v-model="form.start_tls" :label="$t('pages.directory.startTls')" />
          <simple-checkbox v-model="form.verify_certificate" :label="$t('pages.directory.verifyCertificate')" />
          <simple-checkbox v-model="form.nested_groups" :label="$t('pages.directory.nestedGroups')" />
        </div>
        <va-input v-model="form.ca_certificate" class="mt-3" type="textarea" :min-rows="3" :max-rows="8"
          :label="$t('pages.directory.caCertificate')" placeholder="-----BEGIN CERTIFICATE-----" />

        <va-alert v-if="testResult" class="mt-3 test-result" :color="testResult.ok ? 'success' : 'danger'"
          :icon="testResult.ok ? 'check_circle' : 'error'" dense>
          {{ testResult.ok ? $t('pages.directory.testOk') : testResult.message }}
        </va-alert>
      </va-card-content>
    </va-card>

    <va-card class="mt-3">
      <va-card-title><h2>{{ $t('pages.directory.groupsTitle') }}</h2></va-card-title>
      <va-card-content>
        <p class="va-text-secondary mb-3">{{ $t('pages.directory.groupsHelp') }}</p>
        <va-data-table :no-data-html="$t('pages.directory.noGroups')" :items="groups" :columns="groupColumns" class="groups">
          <template #cell(role)="{ rowIndex }">
            <va-select :model-value="groups[rowIndex].role" :options="roleOptions" text-by="text" value-by="value"
              class="role-select" :clearable="false" @update:modelValue="changeRole(groups[rowIndex], $event)" />
          </template>
          <template #cell(group_dn)="{ value }"><code>{{ value }}</code></template>
          <template #cell(id)="{ rowIndex }">
            <va-button icon="delete" :title="$t('pages.directory.removeGroup')" @click="askRemove(groups[rowIndex])" />
          </template>
        </va-data-table>
        <div class="add-group mt-3">
          <va-input v-model="newGroup" class="group-input" :label="$t('pages.directory.groupName')"
            :placeholder="$t('pages.directory.groupPlaceholder')" @keydown.enter="addGroup" />
          <va-select v-model="newRole" class="role-select" :label="$t('pages.directory.role')" :options="roleOptions"
            text-by="text" value-by="value" :clearable="false" />
          <va-button class="add-button" icon="add" :disabled="!newGroup.trim()" :loading="adding" @click="addGroup">
            {{ $t('pages.directory.addGroup') }}
          </va-button>
        </div>
        <div class="roles-help mt-3">
          <b>{{ $t('pages.users.roleViewer') }}</b>: {{ $t('pages.users.helpViewer') }}
          <b>{{ $t('pages.users.roleEditor') }}</b>: {{ $t('pages.users.helpEditor') }}
          <b>{{ $t('pages.users.roleAdmin') }}</b>: {{ $t('pages.users.helpAdmin') }}
        </div>
      </va-card-content>
    </va-card>

    <va-card class="mt-3">
      <va-card-title><h2>{{ $t('pages.directory.lookupTitle') }}</h2></va-card-title>
      <va-card-content>
        <p class="va-text-secondary mb-3">{{ $t('pages.directory.lookupHelp') }}</p>
        <div class="add-group">
          <va-input v-model="lookupName" class="group-input" :label="$t('pages.directory.lookupUser')" @keydown.enter="lookup" />
          <va-button class="lookup-button" icon="search" :disabled="!lookupName.trim()" :loading="looking" @click="lookup">
            {{ $t('pages.directory.lookupButton') }}
          </va-button>
        </div>
        <div v-if="lookupResult" class="lookup-result mt-3">
          <p v-if="!lookupResult.found"><va-icon name="person_off" color="warning" /> {{ $t('pages.directory.lookupNotFound') }}</p>
          <template v-else>
            <p><b>{{ lookupResult.display_name || lookupResult.username }}</b> <code>{{ lookupResult.dn }}</code></p>
            <p v-if="lookupResult.disabled"><va-icon name="block" color="danger" /> {{ $t('pages.directory.lookupDisabled') }}</p>
            <p>{{ $t('pages.directory.lookupGroups') }}
              <va-chip v-for="name in lookupResult.groups" :key="name" size="small" square outline class="mr-1">{{ name }}</va-chip>
              <span v-if="!lookupResult.groups.length">-</span>
            </p>
            <p v-if="lookupResult.role"><va-icon name="verified_user" color="success" />
              {{ $t('pages.directory.lookupRole') }} <b>{{ roleLabel(lookupResult.role) }}</b></p>
            <p v-else><va-icon name="block" color="danger" /> {{ $t('pages.directory.lookupNoRole') }}</p>
          </template>
        </div>
      </va-card-content>
    </va-card>

    <va-modal v-model="showRemove" :ok-text="$t('pages.directory.remove')" @ok="removeGroup">
      <template #header>
        <h2><va-icon name="warning" color="danger" /> {{ $t('pages.directory.removing') }}</h2>
      </template>
      <hr>
      <div v-if="selectedGroup">{{ $t('pages.directory.removeIntro', { name: selectedGroup.name }) }}</div>
    </va-modal>
  </div>
</template>

<script>
import { defineComponent } from "vue";
import axios from "axios";
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";

const FIELDS = ["enabled", "server_url", "start_tls", "verify_certificate", "ca_certificate", "base_dn", "bind_dn",
  "user_filter", "nested_groups", "timeout_seconds"];

export default defineComponent({
  name: "Directory",
  components: { SimpleCheckbox },
  data() {
    return {
      config: { has_bind_password: false },
      saved: { enabled: false },
      form: { enabled: false, server_url: "", start_tls: false, verify_certificate: true, ca_certificate: "", base_dn: "",
        bind_dn: "", bind_password: "", user_filter: "", nested_groups: true, timeout_seconds: 10 },
      groups: [],
      newGroup: "",
      newRole: "viewer",
      selectedGroup: null,
      showRemove: false,
      adding: false,
      saving: false,
      testing: false,
      testResult: null,
      lookupName: "",
      lookupResult: null,
      looking: false,
    };
  },
  computed: {
    changed() {
      return FIELDS.some((field) => this.form[field] !== this.saved[field]) || Boolean(this.form.bind_password);
    },
    validForm() {
      return this.urlRule(this.form.server_url) === true && this.filterRule(this.form.user_filter) === true;
    },
    roleOptions() {
      return ["viewer", "editor", "admin"].map((role) => ({ value: role, text: this.roleLabel(role) }));
    },
    groupColumns() {
      return [
        { key: "name", label: this.$t("pages.directory.colGroup") },
        { key: "group_dn", label: this.$t("pages.directory.colDn") },
        { key: "role", label: this.$t("pages.directory.colRole") },
        { key: "id", label: this.$t("pages.directory.colActions") },
      ];
    },
  },
  methods: {
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    url(path = "") {
      return `${this.$store.state.endpoint.api}/api/v1/directory${path}`;
    },
    roleLabel(role) {
      const key = { viewer: "roleViewer", editor: "roleEditor", admin: "roleAdmin" }[role];
      return key ? this.$t(`pages.users.${key}`) : role;
    },
    urlRule(value) {
      if (!value) return true;
      return /^ldaps?:\/\/[^\s/]+(:\d+)?$/i.test(value) || this.$t("pages.directory.urlRule");
    },
    filterRule(value) {
      return (value || "").includes("{username}") || this.$t("pages.directory.filterRule");
    },
    apply(data) {
      this.config = data.config;
      this.saved = Object.fromEntries(FIELDS.map((field) => [field, data.config[field]]));
      this.form = { ...this.saved, bind_password: "" };
      this.groups = data.groups;
    },
    fail(title, error) {
      const detail = error?.response?.data?.detail;
      this.$vaToast.init({ title, message: typeof detail === "string" ? detail : String(error), color: "danger" });
    },
    async load() {
      try {
        const { data } = await axios.get(this.url(), { headers: this.headers() });
        this.apply(data);
      } catch (error) {
        this.fail(this.$t("pages.directory.unableLoad"), error);
      }
    },
    values() {
      // The password only when it was typed: the server keeps the current one otherwise.
      const values = { ...this.form };
      if (!values.bind_password) delete values.bind_password;
      return values;
    },
    async save() {
      this.saving = true;
      try {
        const { data } = await axios.put(this.url(), this.values(), { headers: this.headers() });
        this.apply(data);
        this.testResult = null;
        this.$vaToast.init({ message: this.$t("pages.directory.saved"), color: "success" });
      } catch (error) {
        this.fail(this.$t("pages.directory.unableSave"), error);
      } finally {
        this.saving = false;
      }
    },
    async testConnection() {
      this.testing = true;
      this.testResult = null;
      try {
        const { data } = await axios.post(this.url("/test"), this.values(), { headers: this.headers() });
        this.testResult = data;
      } catch (error) {
        this.testResult = { ok: false, message: error?.response?.data?.detail || String(error) };
      } finally {
        this.testing = false;
      }
    },
    async addGroup() {
      if (!this.newGroup.trim()) return;
      this.adding = true;
      try {
        await axios.post(this.url("/groups"), { group: this.newGroup.trim(), role: this.newRole }, { headers: this.headers() });
        this.newGroup = "";
        this.$vaToast.init({ message: this.$t("pages.directory.groupAdded"), color: "success" });
        await this.load();
      } catch (error) {
        this.fail(this.$t("pages.directory.unableAddGroup"), error);
      } finally {
        this.adding = false;
      }
    },
    async changeRole(group, role) {
      try {
        const { data } = await axios.patch(this.url(`/groups/${group.id}`), { role }, { headers: this.headers() });
        this.groups = data.groups;
      } catch (error) {
        this.fail(this.$t("pages.directory.unableChangeRole"), error);
        await this.load();
      }
    },
    askRemove(group) {
      this.selectedGroup = group;
      this.showRemove = true;
    },
    async removeGroup() {
      try {
        const { data } = await axios.delete(this.url(`/groups/${this.selectedGroup.id}`), { headers: this.headers() });
        this.groups = data.groups;
      } catch (error) {
        this.fail(this.$t("pages.directory.unableRemoveGroup"), error);
      }
    },
    async lookup() {
      if (!this.lookupName.trim()) return;
      this.looking = true;
      this.lookupResult = null;
      try {
        const { data } = await axios.post(this.url("/lookup"), { username: this.lookupName.trim() }, { headers: this.headers() });
        this.lookupResult = data;
      } catch (error) {
        this.fail(this.$t("pages.directory.unableLookup"), error);
      } finally {
        this.looking = false;
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

.enable {
  display: flex;
  align-items: center;
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(26rem, 1fr));
  gap: 1.25rem 2rem;
}

.field.wide {
  grid-column: 1 / -1;
}

.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.hint {
  margin: 0.3rem 0 0;
  font-size: 0.8rem;
  opacity: 0.7;
}

.unit {
  opacity: 0.6;
}

.add-group {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 1rem;
}

.group-input {
  flex: 1 1 22rem;
}

.role-select {
  min-width: 11rem;
}

.roles-help {
  font-size: 0.85rem;
  opacity: 0.8;
}

code {
  font-size: 0.8rem;
  word-break: break-all;
}
</style>
