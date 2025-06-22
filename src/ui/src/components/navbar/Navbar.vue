<template>
  <div class="app-layout__navbar">
    <va-navbar>
      <template v-slot:left>
        <div class="left">
          <va-icon-menu-collapsed 
            @click="isSidebarMinimized = !isSidebarMinimized"
            :class="{ 'x-flip': isSidebarMinimized }"
            class="va-navbar__item"
            :color="colors.primary"
          />
          <router-link to="/">
            <navbar-logo class="logo"/>
          </router-link>          
        </div>
      </template>
      <template #right>
        <app-navbar-actions
          class="app-navbar__actions md5 lg4"
          :user-name="this.$keycloak?.userName ?? 'TODO'"
        />
      </template>
    </va-navbar>
  </div>
</template>

<script>
import { useColors } from 'vuestic-ui'
import { useStore } from 'vuex'
import { computed } from 'vue'
import NavbarLogo from '@/components/navbar-logo'
import VaIconMenuCollapsed from '@/components/icons/VaIconMenuCollapsed'
import AppNavbarActions from './components/AppNavbarActions'

export default {
  components: { NavbarLogo, AppNavbarActions, VaIconMenuCollapsed },
  setup() {
    const { getColors } = useColors()
    const colors = computed(() => getColors() )
    const store = useStore()

    const isSidebarMinimized = computed({
      get: () => store.state.isSidebarMinimized,
      set: (value) => store.commit('updateSidebarCollapsedState', value)
    })
    return {
      colors,
      isSidebarMinimized
    }
  }
}
</script>

<style lang="scss" scoped>
  .va-navbar {
    box-shadow: var(--va-box-shadow);
    z-index: 2;
    &__center {
      @media screen and (max-width: 1200px) {
        .app-navbar__github-button {
          display: none;
        }
      }
      @media screen and (max-width: 950px) {
        .app-navbar__text {
          display: none;
        }
      }
    }

    @media screen and (max-width: 950px) {
      .left {
        width: 100%;
      }
      .app-navbar__actions {
        width: 100%;
        display: flex;
        justify-content: space-between;
      }
    }
  }

  .left {
    display: flex;
    align-items: center;
    & > * {
      margin-right: 1.5rem;
    }
    & > *:last-child {
      margin-right: 0;
    }
  }

  .x-flip {
    transform: scaleX(-100%);
  }

  .app-navbar__text > * {
    margin-right: 0.5rem;
    &:last-child {
      margin-right: 0;
    }
  }
</style>