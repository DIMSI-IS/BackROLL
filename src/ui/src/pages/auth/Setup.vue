<template>
  <div class="login-wrapper">
    <h1 class="login-title">{{ $t('pages.auth.welcomeTo') }}</h1>
    <img class="va-icon-vuestic logo" height="80" style="margin-bottom: 2rem"
      src="/img/logo2-deg-backroll-cropped.9feb6084.svg" />
    <va-card class="login-form">
      <va-card-title>
        <h1>{{ $t('pages.auth.createAdmin') }}</h1>
      </va-card-title>
      <va-card-content>
        <p class="mb-3">
          {{ $t('pages.auth.firstStart') }}
        </p>
        <va-form ref="form" @submit.prevent="submit">
          <va-input class="mb-3" :label="$t('pages.auth.username')" v-model="username"
            :rules="[(v) => /^[A-Za-z0-9._@-]{3,64}$/.test(v) || $t('pages.auth.usernameRule')]" />
          <va-input class="mb-3" :label="$t('pages.auth.passwordMin')" type="password" v-model="password"
            :rules="[(v) => v.length >= 8 || $t('pages.auth.atLeast8')]" />
          <va-input class="mb-3" :label="$t('pages.auth.confirmPassword')" type="password" v-model="confirmedPassword"
            :rules="[(v) => v === password || $t('pages.auth.passwordsMismatch')]" @keydown.enter.prevent="submit" />
        </va-form>
        <va-button class="mb-3" :disabled="loading" @click="submit">
          {{ $t('pages.auth.createAccount') }}
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
  padding: 2rem;
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
  name: "Setup",
  data() {
    return {
      username: "",
      password: "",
      confirmedPassword: "",
      loading: false,
    };
  },
  computed: {
    endpoint() {
      return `${this.$store.state.endpoint.api}/api/v1/auth/setup`;
    },
  },
  async mounted() {
    // The setup is only available until the first user exists.
    try {
      const { data } = await axios.get(this.endpoint);
      if (!data.required) this.$router.replace({ name: "login" });
    } catch (error) {
      console.error(error);
    }
  },
  methods: {
    async submit() {
      if (!this.$refs.form.validate()) return;

      this.loading = true;
      try {
        const { data } = await axios.post(this.endpoint, {
          username: this.username,
          password: this.password,
        });
        this.$store.commit("setSession", data);
        this.$vaToast.init({
          title: this.$t('pages.auth.setup'),
          message: this.$t('pages.auth.adminCreated'),
          color: "success",
        });
        this.$router.push({ name: "dashboard" });
      } catch (error) {
        console.error(error);
        this.$vaToast.init({
          title: this.$t('pages.auth.setupFailed'),
          message: error?.response?.data?.detail?.[0]?.msg ?? error?.response?.data?.detail ?? this.$t('pages.auth.unreachable'),
          color: "danger",
        });
        // Someone else may have done the setup first.
        if (error?.response?.status === 409) this.$router.replace({ name: "login" });
      } finally {
        this.loading = false;
      }
    },
  },
});
</script>
