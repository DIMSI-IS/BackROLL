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
    <div v-if="!this.$store.state.loadingPools">
      <div class="main-content">
        <b-card title="Pools">
          <div style="text-align: right; margin-bottom: 1%;">
            <b-button variant="info" @click="$router.push('/resource/pools/new').catch(()=>{})">
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
            emptyText="No pool"
            small
          >
            <template #cell(policy_id)="row">
              {{ getBackupPolicy(row.item.policy_id)[0].name }}
            </template>
            <template #cell(actions)="row">
              <div style="text-align: right;">
                <b-button
                  style="margin-left: 10px;"
                  size="sm"
                  variant="danger"
                  class="mb-2"
                  v-b-modal.deleteModal
                  v-b-tooltip.hover title="Remove"
                  @click="selectedPool = row.item"
                >
                  <b-icon icon="trash-fill" aria-hidden="true"></b-icon>
                </b-button>
              </div>
            </template>
            <template #empty="scope">
              <h5 style="text-align: center;">{{ scope.emptyText }}</h5>
            </template>
          </b-table>
        </b-card>
      </div>
      <b-modal
        id="deleteModal"
        size="lg"
        title="Pool deletion"
        okTitle="Yes"
        cancelTitle="No"
        @ok="delete_pool()"
      >
        <p class="my-4">Do you really want to remove pool: {{ selectedPool.name }} ?</p>
      </b-modal>
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
  components: {},
  name: 'Pools',
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Resources', active: true},
            {text: 'Pools', to: '/resource/pools', active: true},
          ],
          fields: [
            // {key: 'id', label:'ID'},
            {key: 'name', label:'Name'},
            {key: 'policy_id', label:'Associated policy'},
            {key: 'actions', label: null}
          ],
          selectedPool: {}
      }
  },
  computed: {
    tableData() {
      return this.$store.state.poolsList.map(x => ({
        id: x.id,
        name:x.name,
        policy_id: x.policy_id !== null ? x.policy_id : 'None'
      }))
    }
  },
  mounted () {
    this.requestPoolList()
  },
  methods: {
    getPoolList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getPoolList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$store.state.loadingPools = false
            this.$store.state.poolsList = response.data.info
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
    requestPoolList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/pools`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getPoolList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    delete_pool () {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/pools/${this.selectedPool.id}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestPoolList()
        this.$bvToast.toast("Pool has been successfully deleted", {
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
    getBackupPolicy (id) {
      return this.$store.state.backupPolicyList.filter((item) => {
        return item.id == id
      })
    }
  }
}
</script>