<template>
  <va-card>
    <va-card-title>
      <h1>{{ $t('pages.auth.changePassword') }}</h1>
    </va-card-title>
    <va-card-content>
      <va-form ref="form">
        <va-input class="mb-3" :label="$t('pages.auth.currentPassword')" type="password" v-model="oldPassword"
          :rules="[(v) => !!v || $t('pages.auth.required')]" />
        <va-input class="mb-3" :label="$t('pages.auth.newPasswordMin')" type="password" v-model="newPassword"
          :rules="[(v) => v.length >= 8 || $t('pages.auth.atLeast8')]" />
        <va-input class="mb-3" :label="$t('pages.auth.confirm')" type="password" v-model="confirmedNewPassword"
          :rules="[(v) => v === newPassword || $t('pages.auth.passwordsMismatch')]" />
      </va-form>
      <va-button class="mb-3" @click="$refs.form.validate() && changePassword()">
        {{ $t('pages.auth.changePassword') }}
      </va-button>
    </va-card-content>
  </va-card>
</template>
<script>
import axios from "axios";
import { defineComponent } from "vue";

export default defineComponent({
  name: "ChangePassword",
  data() {
    return {
      oldPassword: "",
      newPassword: "",
      confirmedNewPassword: "",
    };
  },
  methods: {
    async changePassword() {
      try {
        const { data } = await axios.post(
          `${this.$store.state.endpoint.api}/api/v1/auth/password/change`,
          {
            old_password: this.oldPassword,
            new_password: this.newPassword,
          },
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        );
        // The previous token is revoked by the password change.
        this.$store.commit("setSession", data);
        this.oldPassword = this.newPassword = this.confirmedNewPassword = "";
        // Emptied fields must not show as invalid.
        this.$nextTick(() => this.$refs.form.resetValidation());
        this.$vaToast.init({
          title: this.$t('pages.auth.changePassword'),
          message: this.$t('pages.auth.passwordChanged'),
          color: "success",
        });
      } catch (error) {
        console.error(error);
        this.$vaToast.init({
          title: this.$t('pages.auth.changeFailed'),
          message: error?.response?.data?.detail ?? error,
          color: "danger",
        });
      }
    },
  },
});
</script>
