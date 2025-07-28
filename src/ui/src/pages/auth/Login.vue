<template>
  <div class="login-wrapper">
    <h1 class="login-title">Welcome to</h1>
    <img class="va-icon-vuestic logo" height="80" style="margin-bottom: 2rem"
      src="/img/logo2-deg-backroll-cropped.9feb6084.svg" data-v-45c0bfaf="" />
    <va-card class="login-form">
      <va-card-title>
        <h1>Please login to continue</h1>
      </va-card-title>
      <va-card-content>
        <va-form ref="form" @submit.prevent="submit">
          <va-input class="mb-3" label="Username" v-model="username" />
          <va-input class="mb-3" label="Password" v-model="password" type="password"
            @keydown.enter.prevent="submitOnEnter" />
        </va-form>
        <va-button class="mb-3" @click="submit">
          {{ "Login" }}
        </va-button>
        <div class="links">
          <a href="#">Forgot password?</a><!-- TODO -->
        </div>
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
    };
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
        this.$store.commit("insertToken", data);
        // TODO Provide username in token.
        // this.$store.commit("insertUserName", data);
        this.$vaToast.init({
          title: "Login",
          message: "You are logged in.",
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
              title: "Authentication Error",
              message: "Incorrect username or password.",
              color: "danger",
            });
          } else if (error.response.status === 500) {
            this.$vaToast.init({
              title: "Server Error",
              message: "Server error, login failed.",
              color: "danger",
            });
          } else {
            this.$vaToast.init({
              title: "Error",
              message: error.response.data?.detail || "Unknown error occurred.",
              color: "danger",
            });
          }
        } else {
          // No response from server (network error, etc)
          this.$vaToast.init({
            title: "Error",
            message: "Unable to reach the server.",
            color: "danger",
          });
        }
      }
    },
  },
});
</script>
