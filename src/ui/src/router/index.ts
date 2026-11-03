import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import AppLayout from "@/layout/app-layout.vue";

import RouteViewComponent from "./route-view.vue";
import UIRoute from "@/pages/admin/ui/route";
import store from "@/store";

const routes: Array<RouteRecordRaw> = [
  {
    name: "login",
    path: "/login",
    component: () => import("@/pages/auth/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    name: "setup",
    path: "/setup",
    component: () => import("@/pages/auth/Setup.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    redirect: { name: "dashboard" },
    meta: { requiresAuth: true },
  },
  {
    path: "/:catchAll(.*)",
    redirect: { name: "/404" },
    meta: { requiresAuth: false },
  },
  {
    name: "admin",
    path: "/admin",
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        name: "dashboard",
        path: "dashboard",
        component: () => import("@/pages/admin/dashboard/Dashboard.vue"),
      },
      {
        name: "documentation",
        path: "documentation",
        component: () => import("@/pages/admin/documentation/Documentation.vue"),
      },

      {
        name: "tasks",
        path: "tasks",
        component: RouteViewComponent,
        children: [
          {
            name: "backup",
            path: "backup",
            component: () => import("@/pages/admin/tasks/backup/Backup.vue"),
          },
          {
            name: "restore",
            path: "restore",
            component: () => import("@/pages/admin/tasks/restore/Restore.vue"),
          },
          {
            name: "cleanup",
            path: "/admin/tasks/cleanup",
            component: () => import("@/pages/admin/tasks/cleanup/Cleanup.vue"),
          },
          {
            name: "drp",
            path: "/admin/tasks/drp",
            meta: { requiresRole: "editor" },
            component: () => import("@/pages/admin/tasks/drp/DrpRestore.vue"),
          },
          {
            name: "kickstart_task",
            path: "/admin/tasks/kickstart",
            meta: { requiresRole: "editor" },
            component: () => import("@/pages/admin/tasks/Kickstart.vue"),
          },
        ],
      },
      {
        name: "resources",
        path: "resources",
        component: RouteViewComponent,
        meta: { requiresAuth: true },
        children: [
          {
            name: "pools",
            path: "pools",
            component: () =>
              import("@/pages/admin/resources/pools/PoolList.vue"),
          },
          {
            name: "add pool",
            path: "/admin/resources/pools/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/resources/pools/PoolForm.vue"),
          },
          {
            name: "updatePool",
            path: "/admin/resources/pools/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/resources/pools/PoolForm.vue"),
          },
          {
            name: "hypervisors",
            path: "hypervisors",
            component: () =>
              import("@/pages/admin/resources/hypervisors/HypervisorList.vue"),
          },
          {
            name: "add hypervisor",
            path: "/admin/resources/hypervisors/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/resources/hypervisors/HypervisorForm.vue"),
          },
          {
            name: "Update hypervisor",
            path: "/admin/resources/hypervisors/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/resources/hypervisors/HypervisorForm.vue"),
          },
          {
            name: "virtualmachines",
            path: "virtualmachines",
            component: () =>
              import(
                "@/pages/admin/resources/virtualmachines/VirtualMachineList.vue"
              ),
          },
          {
            path: "/resources/virtualmachines/:id/backups/:backup/files",
            name: "backupFiles",
            meta: { requiresRole: "editor" },
            component: () =>
              import(
                "@/pages/admin/resources/virtualmachines/BackupFiles.vue"
              ),
          },
          {
            path: "/resources/virtualmachines/:id",
            name: "virtualmachinesDetails",
            component: () =>
              import(
                "@/pages/admin/resources/virtualmachines/VirtualMachineDetails.vue"
              ),
          },
        ],
      },
      {
        name: "configuration",
        path: "configuration",
        component: RouteViewComponent,
        meta: { requiresAuth: true },
        children: [
          {
            name: "policies",
            path: "policies",
            component: () =>
              import("@/pages/admin/configuration/policies/PolicyList.vue"),
          },
          {
            name: "updatePolicy",
            path: "/admin/configuration/policy/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/configuration/policies/PolicyForm.vue"),
          },
          {
            name: "add policy",
            path: "/admin/configuration/policies/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/configuration/policies/PolicyForm.vue"),
          },
          {
            name: "storage",
            path: "storage",
            component: () =>
              import("@/pages/admin/configuration/storage/StorageList.vue"),
          },
          {
            name: "add storage",
            path: "/admin/configuration/storage/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/configuration/storage/StorageForm.vue"),
          },
          {
            name: "updateStorage",
            path: "/admin/configuration/storage/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import("@/pages/admin/configuration/storage/StorageForm.vue"),
          },
          {
            name: "connectors",
            path: "connectors",
            component: () =>
              import(
                "@/pages/admin/configuration/connectors/ConnectorList.vue"
              ),
          },
          {
            name: "add connector",
            path: "/admin/configuration/connectors/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import(
                "@/pages/admin/configuration/connectors/ConnectorForm.vue"
              ),
          },
          {
            name: "update connector",
            path: "/admin/configuration/connectors/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import(
                "@/pages/admin/configuration/connectors/ConnectorForm.vue"
              ),
          },
          {
            name: "externalhooks",
            path: "externalhooks",
            component: () =>
              import(
                "@/pages/admin/configuration/externalhooks/ExternalHookList.vue"
              ),
          },
          {
            name: "add externalhook",
            path: "/admin/configuration/externalhooks/new",
            meta: { requiresRole: "editor" },
            component: () =>
              import(
                "@/pages/admin/configuration/externalhooks/ExternalHookForm.vue"
              ),
          },
          {
            name: "update externalhook",
            path: "/admin/configuration/externalhooks/:id",
            meta: { requiresRole: "editor" },
            component: () =>
              import(
                "@/pages/admin/configuration/externalhooks/ExternalHookForm.vue"
              ),
          },
        ],
      },
      {
        name: "auth",
        path: "auth",
        component: RouteViewComponent,
        meta: { requiresAuth: true },
        children: [
          {
            name: "changePassword",
            path: "changePassword",
            component: () => import("@/pages/admin/ChangePassword.vue"),
          },
          {
            name: "users",
            path: "users",
            meta: { requiresRole: "admin" },
            component: () => import("@/pages/admin/users/UserList.vue"),
          },
          {
            name: "settings",
            path: "settings",
            meta: { requiresRole: "admin" },
            component: () => import("@/pages/admin/settings/Settings.vue"),
          },
          {
            name: "directory",
            path: "directory",
            meta: { requiresRole: "admin" },
            component: () => import("@/pages/admin/directory/Directory.vue"),
          },
          {
            name: "auditlog",
            path: "audit",
            meta: { requiresRole: "admin" },
            component: () => import("@/pages/admin/audit/AuditLog.vue"),
          },
        ],
      },
      UIRoute,
    ],
  },
  {
    name: "/404",
    path: "/404",
    component: () => import("@/pages/404-pages/VaPageNotFoundSimple.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  //  mode: process.env.VUE_APP_ROUTER_MODE_HISTORY === 'true' ? 'history' : 'hash',
  routes,
});

// Navigation guard
router.beforeEach((to, _from, next) => {
  const isAuthenticated = store.getters.isAuthenticated;
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: "login" });
  } else if ((to.name === "login" || to.name === "setup") && isAuthenticated) {
    next({ name: "dashboard" });
  } else if (
    to.meta.requiresRole === "admin" && !store.getters.isAdmin ||
    to.meta.requiresRole === "editor" && !store.getters.canEdit
  ) {
    next({ name: "dashboard" });
  } else {
    next();
  }
});

export default router;
