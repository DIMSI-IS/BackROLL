export default {
  root: {
    name: '/',
    displayName: 'navigationRoutes.home',
  },
  routes: [
    {
      name: 'dashboard',
      displayName: 'menu.dashboard',
      meta: {
        icon: 'vuestic-iconset-dashboard',
      },
    },

    {
      name: 'tasks',
      displayName: 'menu.tasks',
      meta: {
        icon: 'settings_backup_restore',
      },
      disabled: true,
      children: [
        {
          name: 'backup',
          displayName: 'menu.backup'
        },
        {
          name: 'restore',
          displayName: 'menu.restore',
        },
      ],
    },

    {
      name: 'resources',
      displayName: 'menu.resources',
      meta: {
        icon: 'category',
      },
      disabled: true,
      children: [
        {
          name: 'pools',
          displayName: 'menu.pools',
        },
        {
          name: 'hypervisors',
          displayName: 'menu.hypervisors',
        },
        {
          name: 'virtualmachines',
          displayName: 'menu.virtualmachines',
        },
      ],
    },

    {
      name: 'configuration',
      displayName: 'menu.configuration',
      meta: {
        icon: 'settings',
      },
      disabled: true,
      children: [
        {
          name: 'policies',
          displayName: 'menu.policies',
        },
        {
          name: 'storage',
          displayName: 'menu.storage',
        },
        {
          name: 'externalhooks',
          displayName: 'menu.external-hooks',
        }
      ],
    }
  ],
}
