<template>
  <va-button-group  :rounded="false" toggle-color="dark" size="small">
    <va-button text-color="white" :disabled="selectedThemeName === THEME_NAMES.LIGHT" icon="light_mode" @click="selectedThemeName = THEME_NAMES.LIGHT" />
    <va-button text-color="white" :disabled="selectedThemeName === THEME_NAMES.DARK" icon="dark_mode" @click="selectedThemeName = THEME_NAMES.DARK" />
  </va-button-group>

</template>

<script>
import { computed, onMounted } from 'vue'
import { THEME_NAMES, useTheme } from '@/services/vuestic-ui/themes'

export default {
  emits: ['change-theme'],
  setup() {
    const { setTheme, themeName } = useTheme()

    const selectedThemeName = computed({
      get: () => themeName.value,
      set: (newThemeName) => setTheme(newThemeName)
    })

    const darkMode = JSON.parse(localStorage.getItem("nightMode")) || false

    const darkModeFromStorage = () => {
      if (darkMode) {
        return THEME_NAMES.DARK
      } else {
        return THEME_NAMES.LIGHT
      }
    }

    onMounted(() => {
      setTheme(darkModeFromStorage())
    })

    return { selectedThemeName, darkMode, THEME_NAMES }
  },
  watch: {
    selectedThemeName: function () {
      if (this.selectedThemeName === THEME_NAMES.DARK) {
        localStorage.setItem("nightMode", true)
      } else {
        localStorage.setItem("nightMode", false)
      }
    }
  }
}
</script>

<style lang="scss" scoped>

.color-dropdown {
  cursor: pointer;

  &__icon {
    position: relative;
    display: flex;
    align-items: center;
  }

  .va-dropdown__anchor {
    display: inline-block;
  }
}

.button-restore {
  display: flex;
  margin: 0.375rem auto;
}

table { 
  margin: 1rem 0;
}
</style>
