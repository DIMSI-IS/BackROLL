<template>
  <va-dropdown
    class="profile-dropdown"
    v-model="isShown"
    boundary-body
    position="bottom"
    :offset="[0, 13]"
  >
    <template #anchor>
      <span class="profile-dropdown__anchor">
        <slot />
        <va-icon
          class="px-2"
          :name="isShown ? 'angle_up' : 'angle_down'"
          :color="theme.primary"
        />
      </span>
    </template>
    <va-dropdown-content class="profile-dropdown__content">
      <va-list-item>
        <va-button
          @click="logout"
          color="danger"
          icon="logout"
          flat
          :rounded="false"
          class="mr-4"
          >Logout</va-button
        >
      </va-list-item>
    </va-dropdown-content>
  </va-dropdown>
</template>

<script>
import { useGlobalConfig } from "vuestic-ui";

export default {
  name: "profile-section",
  data() {
    return {
      isShown: false,
    };
  },
  computed: {
    theme() {
      return useGlobalConfig().getGlobalConfig();
    },
  },
  methods: {
    // this.$keycloak.logoutFn() // TODO: Implement Keycloak logout
    async logout() {
      try {
        await this.$store.dispatch("logout");
        this.$router.push("/login");
      } catch (error) {
        console.error("Error during logout:", error);
      }
    },
  },
};
</script>

<style lang="scss">
.profile-dropdown {
  cursor: pointer;

  .va-dropdown-popper__anchor {
    display: flex;
    justify-content: flex-end;
  }

  &__content {
    width: 8rem;
  }

  &__item {
    display: block;
    color: var(--va-gray);

    &:hover,
    &:active {
      color: var(--va-primary);
    }
  }

  .va-dropdown__anchor {
    display: inline-block;
  }
}
</style>
