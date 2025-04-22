<template>
    <div id="main-container" class="br-container">
        <h1>{{ title }}</h1>
        <div id="right-container" class="br-container">
            <va-alert v-if="!dependenciesResolved && dependenciesMessage" color="danger" border="top"
                style="text-transform: none;">
                {{ dependenciesMessage }}
            </va-alert>
            <va-button v-if="!dependenciesResolved && goButtonTitle && goButtonRoute" icon="chevron_right"
                color="danger" :to="goButtonRoute">
                {{ goButtonTitle }}
            </va-button>
            <va-button v-if="plusButtonTitle && plusButtonRoute" icon="add" color="info" :to="plusButtonRoute"
                :disabled="!dependenciesResolved">
                {{ plusButtonTitle }}
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
        plusButtonTitle: String,
        plusButtonRoute: String,
        dependenciesResolved: {
            type: Boolean,
            default: true
        },
        dependenciesMessage: String,
        goButtonTitle: String,
        goButtonRoute: String
    }
})
</script>
<style scoped>
.br-container {
    display: flex;
    flex-direction: row;
    align-items: center;
}

#main-container {
    width: 100%;
    justify-content: space-between;
}

#right-container {
    gap: 16px;
}
</style>
