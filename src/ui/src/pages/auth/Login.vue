<template>
    <va-card>
        <va-card-title>
            <h1>Login</h1>
        </va-card-title>
        <va-card-content>
            <va-form ref="form">
                <va-input class="mb-3" label="Password" v-model="password" />
            </va-form>
            <va-button class="mb-3" @click="$refs.form.validate() && login()">
                {{ "Login" }}
            </va-button>
        </va-card-content>
    </va-card>
</template>
<script>
import axios from "axios"
import { defineComponent } from "vue";

export default defineComponent({
    name: "Login",
    data() {
        return {
            password: ""
        }
    },
    methods: {
        async login() {
            try {
                const response = await axios.post(
                    `${this.$store.state.endpoint.api}/api/v1/login`,
                    {
                        password: this.password
                    },
                    { headers: { 'Content-Type': 'application/json' } })
                this.$keycloak.token = response.data.token
                this.$vaToast.init({
                    title: "Login",
                    message: "You are logged in.",
                    color: 'success',
                })
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