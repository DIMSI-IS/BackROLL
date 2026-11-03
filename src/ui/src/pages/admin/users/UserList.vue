<template>
  <div>
    <va-card>
      <va-card-title>
        <div class="header">
          <h1>{{ $t('pages.users.title') }}</h1>
          <va-button icon="add" color="info" @click="openCreate">{{ $t('pages.users.addUser') }}</va-button>
        </div>
      </va-card-title>
      <va-card-content>
        <va-data-table :no-data-html="$t('pages.common.noItems')" :items="users" :columns="columns">
          <template #cell(role)="{ value }">
            <va-chip size="small" outline square :color="roleColors[value]">{{ roleLabel(value) }}</va-chip>
          </template>
          <template #cell(auth_source)="{ value }">
            <va-chip size="small" outline square :color="value === 'ad' ? 'info' : 'secondary'" class="source">
              {{ value === 'ad' ? $t('pages.users.sourceAd') : $t('pages.users.sourceLocal') }}
            </va-chip>
          </template>
          <template #cell(is_active)="{ rowIndex }">
            <va-chip v-if="users[rowIndex].locked" size="small" outline square color="warning">{{ $t('pages.users.locked') }}</va-chip>
            <va-chip v-else size="small" outline square :color="users[rowIndex].is_active ? 'success' : 'danger'">
              {{ users[rowIndex].is_active ? $t('pages.users.active') : $t('pages.users.disabled') }}
            </va-chip>
          </template>
          <template #cell(created_at)="{ value }">
            {{ value ? new Date(value).toLocaleString() : "" }}
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button v-if="users[rowIndex].locked" icon="lock_open" :title="$t('pages.users.unlockAccount')"
                @click="unlock(users[rowIndex])" />
              <va-button icon="settings" @click="openEdit(users[rowIndex])" />
              <va-button icon="delete" :disabled="isSelf(users[rowIndex])" @click="openDelete(users[rowIndex])" />
            </va-button-group>
          </template>
        </va-data-table>
        <div v-if="loading" class="flex-center ma-3">
          <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
        </div>
      </va-card-content>
    </va-card>

    <va-modal v-model="showFormModal" :title="editedUser ? $t('pages.users.editUser', { name: editedUser.name }) : $t('pages.users.addUser')" :ok-text="$t('pages.users.save')"
      :before-ok="submit" @cancel="showFormModal = false">
      <va-form ref="form" class="form">
        <va-input v-if="!editedUser" class="mb-3" :label="$t('pages.users.username')" v-model="form.name"
          :rules="[(v) => /^[A-Za-z0-9._@-]{3,64}$/.test(v) || $t('pages.users.usernameRule')]" />
        <va-select class="mb-3" :label="$t('pages.users.role')" v-model="form.role" :options="roleOptions" text-by="text" value-by="value"
          :disabled="editedUser && (isSelf(editedUser) || isDirectory(editedUser))" />
        <va-alert v-if="editedUser && isDirectory(editedUser)" class="mb-3 directory-note" color="info" icon="info" dense>
          {{ $t('pages.users.directoryNote') }}
        </va-alert>
        <simple-checkbox toggle v-if="editedUser" class="mb-3" v-model="form.is_active" :label="$t('pages.users.activeLabel')"
          :disabled="isSelf(editedUser)" />
        <va-input v-if="!editedUser || !isDirectory(editedUser)" class="mb-3" type="password"
          :label="editedUser ? $t('pages.users.newPasswordKeep') : $t('pages.users.passwordMin')"
          v-model="form.password" :rules="[passwordRule]" />
      </va-form>
      <div class="roles-help">
        <b>{{ $t('pages.users.roleViewer') }}</b>: {{ $t('pages.users.helpViewer') }} <b>{{ $t('pages.users.roleEditor') }}</b>: {{ $t('pages.users.helpEditor') }}
        <b>{{ $t('pages.users.roleAdmin') }}</b>: {{ $t('pages.users.helpAdmin') }}
      </div>
    </va-modal>

    <va-modal v-model="showDeleteModal" :ok-text="$t('pages.users.delete')" @ok="deleteUser">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          {{ $t('pages.users.removingUser') }}
        </h2>
      </template>
      <hr>
      <div v-if="selectedUser">
        {{ $t('pages.users.aboutToRemove') }} <b>{{ selectedUser.name }}</b>.
        <br>{{ $t('pages.users.confirmAction') }}
      </div>
    </va-modal>
  </div>
</template>

<script>
import SimpleCheckbox from "@/components/forms/SimpleCheckbox.vue";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import axios from "axios";

export default defineComponent({
  name: "UserList",
  components: { ...spinners, SimpleCheckbox },
  data() {
    return {
      users: [],
      loading: false,
      roles: ["viewer", "editor", "admin"],
      roleColors: { viewer: "info", editor: "warning", admin: "danger" },
      showFormModal: false,
      showDeleteModal: false,
      editedUser: null,
      selectedUser: null,
      form: { name: "", role: "viewer", is_active: true, password: "" },
    };
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.users.colName") },
        { key: "role", label: this.$t("pages.users.colRole") },
        { key: "auth_source", label: this.$t("pages.users.colSource") },
        { key: "is_active", label: this.$t("pages.users.colStatus") },
        { key: "created_at", label: this.$t("pages.users.colCreated") },
        { key: "actions", label: this.$t("pages.users.colActions") },
      ];
    },
    roleOptions() {
      return this.roles.map((role) => ({ value: role, text: this.roleLabel(role) }));
    },
    endpoint() {
      return `${this.$store.state.endpoint.api}/api/v1/users`;
    },
    headers() {
      return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.$store.state.token}`,
      };
    },
  },
  methods: {
    roleLabel(role) {
      const key = { viewer: "roleViewer", editor: "roleEditor", admin: "roleAdmin" }[role];
      return key ? this.$t(`pages.users.${key}`) : role;
    },
    isDirectory(user) {
      return user.auth_source === "ad";
    },
    isSelf(user) {
      return user.id === this.$store.state.user?.id;
    },
    passwordRule(value) {
      if (this.editedUser && !value) return true;
      return (value && value.length >= 8) || this.$t('pages.users.atLeast8');
    },
    notifyError(title, error) {
      console.error(error);
      this.$vaToast.init({
        title,
        message: error?.response?.data?.detail?.[0]?.msg ?? error?.response?.data?.detail ?? error,
        color: "danger",
      });
    },
    async load() {
      this.loading = true;
      try {
        const { data } = await axios.get(this.endpoint, { headers: this.headers });
        this.users = data;
      } catch (error) {
        this.notifyError(this.$t('pages.users.unableList'), error);
      } finally {
        this.loading = false;
      }
    },
    openCreate() {
      this.editedUser = null;
      this.form = { name: "", role: "viewer", is_active: true, password: "" };
      this.showFormModal = true;
    },
    openEdit(user) {
      this.editedUser = user;
      this.form = { name: user.name, role: user.role, is_active: user.is_active, password: "" };
      this.showFormModal = true;
    },
    async unlock(user) {
      try {
        await axios.patch(`${this.endpoint}/${user.id}`, { unlock: true }, { headers: this.headers });
        this.$vaToast.init({ title: this.$t('pages.users.toastTitle'), message: this.$t("pages.users.unlocked", { name: user.name }), color: "success" });
        this.load();
      } catch (error) {
        this.notifyError(this.$t('pages.users.unableUnlock'), error);
      }
    },
    openDelete(user) {
      this.selectedUser = user;
      this.showDeleteModal = true;
    },
    // Returns false to keep the modal open on error.
    async submit() {
      if (!this.$refs.form.validate()) return false;

      try {
        if (this.editedUser) {
          // The role and the password of a user of the directory are not ours to change.
          const body = { is_active: this.form.is_active };
          if (!this.isDirectory(this.editedUser)) body.role = this.form.role;
          if (this.form.password && !this.isDirectory(this.editedUser)) body.password = this.form.password;
          await axios.patch(`${this.endpoint}/${this.editedUser.id}`, body, { headers: this.headers });
        } else {
          await axios.post(this.endpoint, {
            name: this.form.name,
            password: this.form.password,
            role: this.form.role,
          }, { headers: this.headers });
        }
        this.$vaToast.init({ title: this.$t('pages.users.toastTitle'), message: this.$t('pages.users.saved'), color: "success" });
        this.load();
        return true;
      } catch (error) {
        this.notifyError(this.$t('pages.users.unableSave'), error);
        return false;
      }
    },
    async deleteUser() {
      try {
        await axios.delete(`${this.endpoint}/${this.selectedUser.id}`, { headers: this.headers });
        this.$vaToast.init({ title: this.$t('pages.users.toastTitle'), message: this.$t('pages.users.removed'), color: "success" });
        this.load();
      } catch (error) {
        this.notifyError(this.$t('pages.users.unableRemove'), error);
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

.form {
  min-width: 20rem;
}

.roles-help {
  font-size: 0.85rem;
  color: var(--va-gray);
}
</style>
