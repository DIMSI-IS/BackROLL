<template>
    <div id="container">
        <h1>{{ title }}</h1>
        <va-button icon="clear" color="info" @click="$router.go(-1)">Close</va-button>
    </div>
</template>
<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "FormHeader",
    props: {
        title: String,
    }
})
</script>
<style scoped>
#container {
    width: 100%;

    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
}
</style>
