<template>
    <div id="main-container" class="br-container">
        <h1>{{ title }}</h1>
        <div id="right-container" class="br-container">
            <va-alert v-if="!dependenciesResolved" color="danger" border="top" class="mr-8"
                style="text-transform: none;">
                {{ dependenciesMessage }}
            </va-alert>
            <va-button color="info" :to="buttonRoute" :disabled="!dependenciesResolved">
                {{ buttonTitle }}
            </va-button>
        </div>
    </div>
</template>
<script>
import { defineComponent } from 'vue'

export default defineComponent({
    name: "ListHeader",
    props: {
        title: String,
        buttonTitle: String,
        buttonRoute: String,
        dependenciesResolved: Boolean,
        dependenciesMessage: String,
    }
})
</script>
<style scoped>
.br-container {
    display: flex;
    flex-direction: row;
    align-items: baseline;
}

#main-container {
    width: 100%;
    justify-content: space-between;
}

#right-container {
    gap: 16px;
}
</style>