export default {
  root: {
    name: "/",
    displayName: "navigationRoutes.home",
  },
  routes: [
    {
      name: "dashboard",
      displayName: "menu.dashboard",
      meta: {
        icon: "vuestic-iconset-dashboard",
      },
    },
    {
      name: "tasks",
      displayName: "menu.tasks",
      meta: {
        icon: "settings_backup_restore",
      },
      disabled: true,
      children: [
        {
          name: "backup",
          displayName: "menu.backup",
        },
        {
          name: "restore",
          displayName: "menu.restore",
        },
        {
          name: "cleanup",
          displayName: "menu.cleanup",
        },
        {
          name: "drp",
          displayName: "menu.drp",
          requiresRole: "editor",
        },
      ],
    },
    {
      name: "resources",
      displayName: "menu.resources",
      meta: {
        icon: "category",
      },
      disabled: true,
      children: [
        {
          name: "pools",
          displayName: "menu.pools",
        },
        {
          name: "hypervisors",
          displayName: "menu.hypervisors",
        },
        {
          name: "virtualmachines",
          displayName: "menu.virtualmachines",
        },
      ],
    },
    {
      name: "configuration",
      displayName: "menu.configuration",
      meta: {
        icon: "assignment",
      },
      disabled: true,
      children: [
        {
          name: "policies",
          displayName: "menu.policies",
        },
        {
          name: "storage",
          displayName: "menu.storage",
        },
        {
          name: "connectors",
          displayName: "menu.connectors",
        },
        {
          name: "externalhooks",
          displayName: "menu.external-hooks",
        },
      ],
    },
    {
      name: "parameters",
      displayName: "menu.parameters",
      meta: {
        icon: "settings",
      },
      disabled: true,
      children: [
        {
          name: "changePassword",
          displayName: "menu.changePassword",
        },
        {
          name: "users",
          displayName: "menu.users",
          requiresRole: "admin",
        },
        {
          name: "settings",
          displayName: "menu.settings",
          requiresRole: "admin",
        },
        {
          name: "directory",
          displayName: "menu.directory",
          requiresRole: "admin",
        },
        {
          name: "auditlog",
          displayName: "menu.audit",
          requiresRole: "admin",
        },
      ],
    },
    {
      name: "documentation",
      displayName: "menu.documentation",
      meta: {
        icon: "menu_book",
      },
    },
  ],
};
