import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import AppLayout from '@/layout/app-layout.vue'

import RouteViewComponent from './route-view.vue'
import UIRoute from '@/pages/admin/ui/route'

const routes: Array<RouteRecordRaw> = [
  {
    path: "/",
    redirect: { name: 'dashboard' },
  },
  {
    path: "/:catchAll(.*)",
    redirect: { name: '/404' },
  },
  {
    name: 'admin',
    path: '/admin',
    component: AppLayout,
    children: [
      {
        name: 'dashboard',
        path: 'dashboard',
        component: () => import('@/pages/admin/dashboard/Dashboard.vue'),
      },

      {
        name: 'tasks',
        path: 'tasks',
        component: RouteViewComponent,
        children: [
          {
            name: 'backup',
            path: 'backup',
            component: () => import('@/pages/admin/tasks/backup/Backup.vue')
          },
          {
            name: 'restore',
            path: 'restore',
            component: () => import('@/pages/admin/tasks/restore/Restore.vue')
          },
          {
            name: 'kickstart_task',
            path: '/admin/tasks/kickstart',
            component: () => import('@/pages/admin/tasks/Kickstart.vue')
          },
        ],
      },

      {
        name: 'resources',
        path: 'resources',
        component: RouteViewComponent,
        children: [
          {
            name: 'pools',
            path: 'pools',
            component: () => import('@/pages/admin/resources/pools/Pools.vue')
          },
          {
            name: 'add pool',
            path: '/admin/resources/pools/new',
            component: () => import('@/pages/admin/resources/pools/AddPool.vue')
          },
          {
            name: 'updatePool',
            path: '/admin/resources/pools/:id',
            component: () => import('@/pages/admin/resources/pools/UpdatePool.vue')
          },
          {
            name: 'hypervisors',
            path: 'hypervisors',
            component: () => import('@/pages/admin/resources/hypervisors/Hypervisors.vue')
          },
          {
            name: 'add hypervisor',
            path: '/admin/resources/hypervisors/new',
            component: () => import('@/pages/admin/resources/hypervisors/AddHypervisor.vue')
          },
          {
            name: 'Update hypervisor',
            path: '/admin/resources/hypervisors/:id',
            component: () => import('@/pages/admin/resources/hypervisors/UpdateHypervisor.vue')
          },
          {
            name: 'virtualmachines',
            path: 'virtualmachines',
            component: () => import('@/pages/admin/resources/virtualmachines/Virtualmachines.vue')
          },
          {
            path: '/resources/virtualmachines/:id',
            name: 'virtualmachinesDetails',
            component: () => import('@/pages/admin/resources/virtualmachines/VirtualmachineDetails.vue')
          },
        ],
      },

      {
        name: 'configuration',
        path: 'configuration',
        component: RouteViewComponent,
        children: [
          {
            name: 'policies',
            path: 'policies',
            component: () => import('@/pages/admin/configuration/policies/Policies.vue')
          },
          {
            name: 'updatePolicy',
            path: '/admin/configuration/policy/:id',
            component: () => import('@/pages/admin/configuration/policies/UpdatePolicy.vue')
          },
          {
            name: 'add policy',
            path: '/admin/configuration/policies/new',
            component: () => import('@/pages/admin/configuration/policies/AddPolicy.vue')
          },
          {
            name: 'storage',
            path: 'storage',
            component: () => import('@/pages/admin/configuration/storage/Storage.vue')
          },
          {
            name: 'add storage',
            path: '/admin/configuration/storage/new',
            component: () => import('@/pages/admin/configuration/storage/AddStorage.vue')
          },
          {
            name: 'updateStorage',
            path: '/admin/configuration/storage/:id',
            component: () => import('@/pages/admin/configuration/storage/UpdateStorage.vue')
          },
          {
            name: 'connectors',
            path: 'connectors',
            component: () => import('@/pages/admin/configuration/connectors/Connectors.vue')
          },
          {
            name: 'add connector',
            path: '/admin/configuration/connectors/new',
            component: () => import('@/pages/admin/configuration/connectors/AddConnector.vue')
          },
          {
            name: 'update connector',
            path: '/admin/configuration/connectors/:id',
            component: () => import('@/pages/admin/configuration/connectors/UpdateConnector.vue')
          },
          {
            name: 'externalhooks',
            path: 'externalhooks',
            component: () => import('@/pages/admin/configuration/externalhooks/ExternalHooks.vue')
          },
          {
            name: 'add externalhook',
            path: '/admin/configuration/externalhooks/new',
            component: () => import('@/pages/admin/configuration/externalhooks/AddExternalHook.vue')
          },
          {
            name: 'update externalhook',
            path: '/admin/configuration/externalhooks/:id',
            component: () => import('@/pages/admin/configuration/externalhooks/UpdateExternalHook.vue')
          }
        ],
      },
      UIRoute,
    ]
  },
  {
    name: '/404',
    path: '/404',
    component: () => import('@/pages/404-pages/VaPageNotFoundSimple.vue')
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  //  mode: process.env.VUE_APP_ROUTER_MODE_HISTORY === 'true' ? 'history' : 'hash',
  routes
})

export default router
