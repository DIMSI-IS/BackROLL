<template>
  <div class="login-wrapper">
    <h1 class="login-title">{{ $t('pages.auth.welcomeTo') }}</h1>
    <img class="va-icon-vuestic logo" height="80" style="margin-bottom: 2rem"
      src="/img/logo2-deg-backroll-cropped.9feb6084.svg" data-v-45c0bfaf="" />
    <va-card class="login-form">
      <va-card-title>
        <h1>{{ $t('pages.auth.pleaseLogin') }}</h1>
      </va-card-title>
      <va-card-content>
        <va-form ref="form" @submit.prevent="submit">
          <va-input class="mb-3" :label="$t('pages.auth.username')" v-model="username" />
          <va-input class="mb-3" :label="$t('pages.auth.password')" v-model="password" type="password" @keydown.enter.prevent="submit" />
        </va-form>
        <p v-if="directory" class="directory-hint">{{ $t('pages.auth.directoryHint') }}</p>
        <va-button class="mb-3" @click="submit">
          {{ $t('pages.auth.login') }}
        </va-button>
      </va-card-content>
    </va-card>
  </div>
</template>

<style scoped>
.login-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f8f9fa;
  /* Optionnel, ajoute un fond clair */
  padding: 2rem;
}

/* .login-form{
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
} */
.directory-hint {
  margin: 0 0 1rem;
  font-size: 0.85rem;
  opacity: 0.7;
}

.login-title {
  font-size: 5rem;
  font-weight: bold;
  margin-bottom: 2rem;
  text-align: center;
}
</style>

<script>
import axios from "axios";
import { defineComponent } from "vue";

export default defineComponent({
  name: "Login",
  data() {
    return {
      username: "",
      password: "",
      // The Active Directory is on: the users of the company may use their account.
      directory: false,
    };
  },
  async mounted() {
    // Until the first user exists, the administrator account must be created.
    try {
      const { data } = await axios.get(
        `${this.$store.state.endpoint.api}/api/v1/auth/setup`
      );
      if (data.required) this.$router.replace({ name: "setup" });
    } catch (error) {
      console.error(error);
    }
    try {
      const { data } = await axios.get(`${this.$store.state.endpoint.api}/api/v1/auth/providers`);
      this.directory = Boolean(data.directory);
    } catch (error) {
      // Nothing is said about the directory.
    }
  },
  methods: {
    async submit() {
      if (this.$refs.form.validate()) {
        await this.login();
      }
    },
    async login() {
      try {
        const { data } = await axios.post(
          `${this.$store.state.endpoint.api}/api/v1/auth/password/login`,
          {
            username: this.username,
            password: this.password,
          },
          { headers: { "Content-Type": "application/json" } }
        );
        this.$store.commit("setSession", data);
        this.$vaToast.init({
          title: this.$t('pages.auth.login'),
          message: this.$t('pages.auth.loggedIn'),
          color: "success",
        });

        // Initial loading for a better experience
        // when first opening a list.

        this.$store.dispatch("requestJob");
        this.$store.dispatch("requestBackupTask");
        this.$store.dispatch("requestRestoreTask");

        this.$store.dispatch("requestPool");
        this.$store.dispatch("requestHost");
        this.$store.dispatch("requestVirtualMachine");

        this.$store.dispatch("requestPolicy");
        this.$store.dispatch("requestStorage");
        this.$store.dispatch("requestConnector");
        this.$store.dispatch("requestExternalHook")

        this.$router.push({ name: "dashboard" });
      } catch (error) {
        console.error(error);
        if (error.response) {
          // Handle HTTP error status codes
          if (error.response.status === 401 || error.response.status === 403) {
            this.$vaToast.init({
              title: this.$t('pages.auth.authError'),
              message: this.$t('pages.auth.badCredentials'),
              color: "danger",
            });
          } else if (error.response.status === 503) {
            this.$vaToast.init({
              title: this.$t('pages.auth.error'),
              message: this.$t('pages.auth.directoryUnavailable'),
              color: "danger",
            });
          } else if (error.response.status === 500) {
            this.$vaToast.init({
              title: this.$t('pages.auth.serverError'),
              message: this.$t('pages.auth.serverErrorLogin'),
              color: "danger",
            });
          } else {
            this.$vaToast.init({
              title: this.$t('pages.auth.error'),
              message: error.response.data?.detail || this.$t('pages.auth.unknownError'),
              color: "danger",
            });
          }
        } else {
          // No response from server (network error, etc)
          this.$vaToast.init({
            title: this.$t('pages.auth.error'),
            message: this.$t('pages.auth.unreachable'),
            color: "danger",
          });
        }
      }
    },
  },
});
</script>
