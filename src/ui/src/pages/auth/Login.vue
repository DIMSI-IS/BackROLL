<template>
    <div class="login-page-style">
        <va-card>
            <va-card-title>
                <h1>Login</h1>
            </va-card-title>
            <va-card-content>
                <va-form ref="form" @submit.prevent="submitOnEnter">
                    <va-input class="mb-3" label="Username" v-model="username" name="username"/>
                    <va-input class="mb-3" label="Password" v-model="password"  name="password" type="password" @keydown.enter.prevent="submitOnEnter"/>
                </va-form>
                <va-button class="mb-3" @click="submitOnEnter">
                    {{ "Login" }}
                </va-button>
            </va-card-content>
        </va-card>
    </div>
</template>

<style scoped>
.login-page-style {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
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
