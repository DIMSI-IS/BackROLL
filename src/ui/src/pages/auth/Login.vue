<template>

    <div class="login-wrapper">
        <h1 class="login-title">Welcome to</h1>
        <img class="va-icon-vuestic logo" height="80" style="margin-bottom: 2rem" src="/img/logo2-deg-backroll-cropped.9feb6084.svg" data-v-45c0bfaf="">
        <va-card class="login-form">
            <va-card-title>
                <h1>Please login to continue</h1>
            </va-card-title>
            <va-card-content>
                <va-form ref="form" @submit.prevent="submitOnEnter">
                    <va-input class="mb-3" label="Username" v-model="username" name="username" />
                    <va-input class="mb-3" label="Password" v-model="password"  name="password" type="password" @keydown.enter.prevent="submitOnEnter"/>
                </va-form>
                <va-button class="mb-3" @click="submitOnEnter">
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
  background: #f8f9fa; /* Optionnel, ajoute un fond clair */
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
import axios from "axios"
import { defineComponent } from "vue";

export default defineComponent({
    name: "Login",
    data() {
        return {
            username: "",
            password: "",
        }
    },
    methods: {
        async submitOnEnter() {
            if (this.$refs.form.validate()) {
            this.login();
            }
        },
        async login() {
            try {
                const { data } = await axios.post(
                    `${this.$store.state.endpoint.api}/api/v1/auth/password/login`,
                    {
                        //username: process.env.VUE_APP_DEFAULT_USER_NAME,
                        username: this.username,
                        password: this.password
                    },
                    { headers: { 'Content-Type': 'application/json' } })
                this.$store.dispatch('insertToken', data);
                this.$store.commit('insertToken', data);
                this.$store.commit('insertUserName', data.username); // si l'API le renvoie
                this.$vaToast.init({
                    title: "Login",
                    message: "You are logged in.",
                    color: 'success',
                })
                this.$router.push({ name: 'dashboard' });
            } catch (error) {
                console.error(error)
                this.$vaToast.init({
                    title: 'Login failed.',
                    message: error?.response?.data?.detail ?? error,
                    color: 'danger'
                })
            }
        }
    }
})
</script>
