<!--
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
-->

<template>
  <div>
    <div class="bc-content">
      <b-breadcrumb :items="items"></b-breadcrumb>
    </div>
    <div v-if="!this.$store.state.loadingBackupPolicies">
      <div class="main-content">
        <b-card title="Backup policies">
          <b-overlay opacity="1" :show="this.$store.state.loadingBackupPolicies" rounded="sm">
            <div style="text-align: right; margin-bottom: 1%;">
              <b-button variant="info" @click="$router.push('/backups/policies/new').catch(()=>{})">
                <b-icon icon="plus-circle" aria-hidden="true"></b-icon> Add new
              </b-button>
            </div>
            <b-table
              :items="tableData"
              :fields="fields"
              stacked="md"
              striped
              hover
              borderless
              ref="selectableTable"
              show-empty
              emptyText="No backup policy"
              small
            >
              <template #cell(enabled)="row">
                <h5><b-badge :variant="getBadgeType(row.item.enabled)">{{ row.item.enabled === 0 ? 'Disabled' : 'Enabled' }}</b-badge></h5>
              </template>
              <template #cell(retention)="row">
                {{ readable(row.item.retention) }}
              </template>
              <template #cell(actions)="row">
                <div style="text-align: right;">

                  <b-button
                    v-if="row.item.enabled !== 0"
                    style="margin-left: 10px;"
                    size="sm"
                    variant="dark"
                    class="mb-2"
                    v-b-tooltip.hover title="Disable"
                    @click="disablePolicy(row.item.id)"
                  >
                    <b-icon icon="x-circle-fill" aria-hidden="true"></b-icon>
                  </b-button>

                  <b-button
                    style="margin-left: 10px;"
                    size="sm"
                    variant="primary"
                    class="mb-2"
                    v-b-tooltip.hover title="Edit"
                    :to="`/backups/policies/${row.item.id}/${row.item.name}`"
                  >
                    <b-icon icon="gear" aria-hidden="true"></b-icon>
                  </b-button>

                  <b-button
                    style="margin-left: 10px;"
                    size="sm"
                    variant="danger"
                    class="mb-2"
                    v-b-modal.deleteModal
                    v-b-tooltip.hover title="Remove"
                    @click="selectedPolicy = row.item"
                  >
                    <b-icon icon="trash-fill" aria-hidden="true"></b-icon>
                  </b-button>
                </div>
              </template>
              <template #empty="scope">
                <h5 style="text-align: center;">{{ scope.emptyText }}</h5>
              </template>
            </b-table>
          </b-overlay>
        </b-card>
        <b-modal
          id="deleteModal"
          size="lg"
          title="Backup policy deletion"
          okTitle="Yes"
          cancelTitle="No"
          @ok="deletePolicy()"
        >
          <p class="my-4">Do you really want to remove backup policy: {{ selectedPolicy.name }} ?</p>
        </b-modal>
      </div>
    </div>
    <div
      class="text-center"
      v-else
    >
      <b-spinner
        variant="dark"
        label="Spinning"
      />
      <span style="font-size: 2em;">
        Discovering resources...
      </span>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
export default {
  name: 'Dashboard',
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Backups', active: true},
            {text: 'Policies', to: '/backup/policies', active: true},
          ],
          fields: [
            {key: 'name', label:'Name'},
            {key: 'schedule', label:'Schedule'},
            {key: 'retention', label:'Retention'},
            {key: 'enabled', label: 'State'},
            'actions'
          ],
          selectedPolicy: {}
      }
  },
  computed: {
    tableData() {
      if (this.$store.state.backupPolicyList) {
        return this.$store.state.backupPolicyList.map(x => ({
          id: x.id,
          name: x.name,
          schedule: x.schedule,
          retention: x.retention !== null ? JSON.parse(x.retention) : {},
          enabled: parseInt(x.enabled)
        }))
      } else {
        return []
      }
    }
  },
  mounted () {
    this.requestBackupPolicyList()
  },
  methods: {
    getBadgeType(state) {
      if (state === 1) {
        return 'success'
      } else {
        return 'danger'
      }
    },
    readable(jsonCron) {
      if (jsonCron.daily) {
        return `J=${jsonCron.daily},S=${jsonCron.weekly},M=${jsonCron.monthly},A=${jsonCron.yearly}`
      } else {
        return ''
      }
    },
    disablePolicy(backup_policy_id) {
      axios.patch(`${this.$store.state.endpoint.api}/api/v1/backup_policies/${backup_policy_id}`, { policy_id: backup_policy_id, enabled: false }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestBackupPolicyList()
        this.$bvToast.toast("Backup policy has been successfully disabled", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        this.$bvToast.toast(e.data.status, {
          title: e.data.state,
          variant: 'danger',
          solid: true
        })
      })
    },
    getBackupPolicyList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getBackupPolicyList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$store.state.loadingBackupPolicies = false
            this.$store.state.backupPolicyList = response.data.info
        } else if (response.data.state === 'FAILURE') {
          this.$bvToast.toast(response.data.status, {
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        this.errors.push(e)
      })

    },
    requestBackupPolicyList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/backup_policies`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getBackupPolicyList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    deletePolicy () {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/backup_policies/${this.selectedPolicy.id}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestBackupPolicyList()
        this.$bvToast.toast("Backup policy has been successfully deleted", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        this.$bvToast.toast(e.data.status, {
          title: e.data.state,
          variant: 'danger',
          solid: true
        })
      })
    }
  }
}
</script>