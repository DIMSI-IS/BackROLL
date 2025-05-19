<template>
    <va-card>
        <va-card-title>
            <h1>Set password</h1>
        </va-card-title>
        <va-card-content>
            <va-form ref="form">
                <va-input class="mb-3" label="Password" v-model="password" />
                <va-input class="mb-3" label="Confirm" v-model="confirmedPassword" />
            </va-form>
            <va-button class="mb-3" @click="$refs.form.validate() && setPassword()">
                {{ "Set password" }}
            </va-button>
        </va-card-content>
    </va-card>
</template>
<script>

</script>