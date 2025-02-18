<template>
    <va-modal modal-class="fit-content-modal" v-model="showModal" size="large" :hide-default-actions="true">
        <template #header>
            <h2>
                <va-icon name="bug_report" color="info" />
                {{ title }}
            </h2>
        </template>
        <hr />
        <div class="console">
            {{ error }}
        </div>
        <template #footer>
            <va-button @click="error = null">
                Close
            </va-button>
        </template>
    </va-modal>
</template>
<script>
export default {
    name: "error-modal",
    props: {
        modelValue: String,
        title: String
    },
    computed: {
        error: {
            get() {
                return this.modelValue;
            },
            set(value) {
                this.$emit("update:modelValue", value);
            }
        },
        showModal() {
            return Boolean(this.error);
        }
    }
}
</script>
<style>
.fit-content-modal {
    width: fit-content !important;
    max-width: none !important;
    min-width: auto !important;
}

.console {
    padding: 1% 1% 1% 1%;
    background: black;
    color: silver;
    font-size: 1em;
    border-radius: 5px;

    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
}
</style>