<template>
    <va-card>
        <va-card-title>
            <h1>Change password</h1>
        </va-card-title>
        <va-card-content>
            <va-form ref="form">
                <va-input class="mb-3" label="Current password" v-model="oldPassword" />
                <va-input class="mb-3" label="New password" v-model="newPassword" />
                <va-input class="mb-3" label="Confirm" v-model="confirmedNewPassword" />
            </va-form>
            <va-button class="mb-3" @click="$refs.form.validate() && changePassword()">
                {{ "Change password" }}
            </va-button>
        </va-card-content>
    </va-card>
</template>
<script>
import axios from "axios"
import { defineComponent } from "vue";

export default defineComponent({
    name: "ChangePassowrd",
    data() {
        return {
            oldPassword: "",
            newPassword: "",
            confirmedNewPassword: "",
        }
    },
    methods: {
        async changePassword() {
            try {
                // TODO check confirmed password

                await axios.post(`${this.$store.state.endpoint.api}/api/v1/auth/password/change`,
                    {
                        username: process.env.VUE_APP_DEFAULT_USER_NAME,
                        old_password: this.oldPassword,
                        new_password: this.newPassword,
                    },
                    { headers: { 'Content-Type': 'application/json' } })
                this.$vaToast.init({
                    title: "Change password",
                    message: "Password successfully changed.",
                    color: "success",
                })
            } catch (error) {
                console.error(error)
                this.$vaToast.init({
                    title: 'Change password failed.',
                    message: error?.response?.data?.detail ?? error,
                    color: 'danger'
                })
            }
        }
    }
})
</script>
