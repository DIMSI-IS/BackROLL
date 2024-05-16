<template>
  <va-sidebar
    :width="width"
    :minimized="minimized" 
    :minimizedWidth="minimizedWidth"
  >
    <menu-minimized v-if="minimized" :items="items" />
    <menu-accordion v-else :items="items" />
  </va-sidebar>    
</template>

<script>
import { useGlobalConfig } from 'vuestic-ui';
import MenuAccordion from '@/components/sidebar/menu/MenuAccordion';
import MenuMinimized from '@/components/sidebar/menu/MenuMinimized';
import NavigationRoutes from '@/components/sidebar/NavigationRoutes';


export default {
  components: {
    MenuAccordion,
    MenuMinimized,
  },
  props: {
    width: { type: String, default: '16rem' },
    color: { type: String, default: "secondary" },
    minimized: { type: Boolean, required: true },
    minimizedWidth: {
      type: String,
      required: false,
      default: undefined
    },
  },
  data() {
    return {
      items: NavigationRoutes.routes,
    };
  },
  computed: {
    computedClass() {
      return {
        "app-sidebar--minimized": this.minimized
      };
    },
    colors() {
      return useGlobalConfig().getGlobalConfig().colors
    },
  },
};
</script>

<style lang="scss">
.va-sidebar {
  .va-collapse__body {
    margin-top: 0 !important;
  }

  &__menu {
    padding: 2rem 0;
    &__inner {
      padding-bottom: 8rem;
    }
  }

  &-item {
    &-content {
      padding: 0.75rem 1rem;
    }

    &__icon {
      width: 1.5rem;
      height: 1.5rem;
      display: flex;
      justify-content: center;
      align-items: center;
    }
  }
}
</style>

<style lang="scss" scoped>
.va-sidebar {
  flex-shrink: 0;
}

// .va-sidebar--minimized {
//   width: auto !important;
// }
</style>
