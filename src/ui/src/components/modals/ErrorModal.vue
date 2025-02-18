<template>
    <va-modal v-model="isStorageErrorModalShown" size="large" :hide-default-actions="true">
        <template #header>
            <h2>
                <va-icon name="bug_report" color="info" />
                {{ title }}
            </h2>
        </template>
        <hr />
        <div class="consoleStyle">
            {{ error }}
        </div>
        <template #footer>
            <va-button @click="showModal = false">
                Close
            </va-button>
        </template>
    </va-modal>
</template>
<script>
export default {
    name: "error-modal",
    props: {
        title: { type: "string" },
        error: { type: "string" }
    },
    data() {
        return {
            showModal: false,
        }
    },
    watch: {
        error(new_value) {
            this.showModal = Boolean(new_value);
        }
    }
}
</script>
<style>
.consoleStyle {
    padding: 1% 1% 1% 1%;
    background: black;
    color: silver;
    font-size: 1em;
    border-radius: 5px;
    max-height: 5%;
    width: auto;
}
</style>