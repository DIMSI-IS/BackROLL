<template>
  <div class="app-navbar-actions">
    <va-chip
      class="app-navbar-actions__item"
      v-show="pendingTaskNumber && pendingTaskNumber > 0"
      color="primary"
      to='/admin/tasks/backup'
      shadow
    >
      <va-icon name="loop" spin="counter-clockwise" />
      <span style="font-style: bold; padding-left: 5px;">
        {{ pendingTaskNumber }}
      </span>
    </va-chip>
    <dark-mode-selector class="app-navbar-actions__item" />
    <notification-dropdown class="app-navbar-actions__item"/>
    <language-dropdown class="app-navbar-actions__item"/>
    <profile-dropdown class="app-navbar-actions__item app-navbar-actions__item--profile">
      <span>{{userName}}</span>
    </profile-dropdown>
  </div>
</template>

<script>
import LanguageDropdown from './dropdowns/LanguageDropdown'
import ProfileDropdown from './dropdowns/ProfileDropdown'
import DarkModeSelector from './DarkModeSelector'

export default {
  name: 'app-navbar-actions',

  components: {
    DarkModeSelector,
    LanguageDropdown,
    ProfileDropdown,
  },

  props: {
    userName: {
      type: String,
      default: '',
    },
    isTopBar: {
      type: Boolean,
      default: false,
    },
  },

  computed: {
    filteredTaskList() {
      return Object.values(this.$store.state.backupTaskList).filter(x =>(x.name === 'Single_VM_Backup' || x.name === 'backup_subtask'))
    },
    pendingTaskNumber() {
      return this.filteredTaskList.filter(x => x.state === 'STARTED').length
    },
    isTopBarProxy: {
      get () {
        return this.isTopBar
      },
      set (isTopBar) {
        this.$emit('update:isTopBar', isTopBar)
      },
    },
  },
}
</script>

<style lang="scss">
.app-navbar-actions {
  display: flex;
  align-items: center;

  .va-dropdown__anchor {
    color: var(--va-primary);
    fill: var(--va-primary);
  }

  &__item {
    padding: 0;
    margin-left: 1.25rem;
    margin-right: 1.25rem;

    svg {
      height: 24px;
    }

    &:last-of-type {
      margin-right: 0;
    }

    &--profile {
      display: flex;
      justify-content: center;
      margin: auto 0 auto 1.25rem;
    }

    .va-dropdown-content {
      background-color: var(--va-white);
    }

    @media screen and (max-width: 768px) {
      margin-right: 0;

      &:first-of-type {
        margin-left: 0;
      }

      &--profile {
        position: absolute;
        right: 0.75rem;
        top: 1.25rem;
        height: fit-content;
        margin: auto;
      }
    }
  }
}
</style>
