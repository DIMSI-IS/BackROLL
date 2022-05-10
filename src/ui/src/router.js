// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

import Vue from 'vue'
import Router from 'vue-router'

import Home from './views/Home.vue'
// Resources
import Pools from './views/resource/Pools.vue'
import Hypervisors from './views/resource/Hypervisors.vue'
import BackupPolicyDetails from './views/resource/PolicyDetails'
import VirtualMachines from './views/resource/VirtualMachines.vue'
import VirtualMachineDetails from './views/resource/VirtualMachineDetails.vue'
// Create resource
import create_pool from './views/create/Pool.vue'
import createHypervisor from './views/create/Hypervisor.vue'
import create_backup_policy from './views/create/Policy.vue'
// Backups
import BackupPolicies from './views/resource/Policies.vue'
import BackupTasks from './views/backup/Tasks.vue'
// Restore
import restore_tasks from './views/restore/Tasks.vue'
// Tasks
import createTask from './views/create/Task.vue'

Vue.use(Router)

const router = new Router({
    base: process.env.BASE_URL,
    routes: [
      {
        path: '/',
        name: 'home',
        component: Home,
      },
      {
        path: '/resource/pools',
        name: 'pools',
        component: Pools,
      },
      {
        path: '/resource/pools/new',
        name: 'create_pool',
        component: create_pool,
      },
      {
        path: '/resource/hypervisors',
        name: 'hypervisors',
        component: Hypervisors,
      },
      {
        path: '/resource/hypervisors/new',
        name: 'createHypervisor',
        component: createHypervisor,
      },
      {
        path: '/resource/virtual_machines',
        name: 'virtualmachines',
        component: VirtualMachines,
      },
      {
        path: '/resource/virtual_machines/:virtual_machine',
        name: 'virtualmachinesDetails',
        component: VirtualMachineDetails,
      },
      {
        path: '/backups/policies',
        name: 'policies',
        component: BackupPolicies,
      },
      {
        path: '/backups/policies/new',
        name: 'create_backup_policy',
        component: create_backup_policy,
      },
      {
        path: '/backups/policies/:id/:name',
        name: 'backupPolicyDetails',
        component: BackupPolicyDetails,
      },
      {
        path: '/backups/tasks',
        name: 'tasks',
        component: BackupTasks,
      },
      {
        path: '/backups/tasks/new',
        name: 'createTask',
        component: createTask,
      },
      {
        path: '/restore/tasks',
        name: 'tasks',
        component: restore_tasks,
      }
    ]
  })

export default router