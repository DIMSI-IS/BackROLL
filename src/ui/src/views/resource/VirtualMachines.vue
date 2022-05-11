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
    <div v-if="!this.$store.state.loadingVMs">
      <div class="main-content">
        <b-card title="Virtual machines">
          <b-card-body>
            <b-form-input v-model="searchQuery" type="search" placeholder="Search"></b-form-input>
            <b-table
              :items="this.filteredResources"
              :fields="fields"
              stacked="md"
              striped
              hover
              borderless
              ref="selectableTable"
              show-empty
              emptyText="No virtual machine"
              small
            >
              <template #empty="scope">
                <h5 style="text-align: center;">{{ scope.emptyText }}</h5>
              </template>
              <template #cell(host)="row">
                {{ getHypervisor(row.item.host)[0].hostname }}
              </template>
              <template #cell(cpus)="row">
                {{ row.item.cpus }} Core{{ row.item.cpus > 1 ? 's' : '' }}
              </template>
              <template #cell(mem)="row">
                {{ row.item.mem / 1024 }} MB
              </template>
              <template #cell(host_tag)="row">
                <div v-if="row.item.host_tag">
                  <h5><b-badge :variant="row.item.host_tag === 'management' ? 'warning' : 'light'">{{ row.item.host_tag }}</b-badge></h5>
                </div>
                <div v-else>
                  <b-icon icon="arrow-clockwise" animation="spin" font-scale="1"/><span> Loading</span>
                </div>
              </template>
              <template #cell(state)="row">
                <h5><b-badge :variant="getBadgeType(row.item.state)">{{ row.item.state }}</b-badge></h5>
              </template>
              <template #cell(actions)="row">
                <b-button
                  style="margin-left: 10px;"
                  size="sm"
                  variant="info"
                  class="mb-2"
                  v-b-tooltip.hover title="Edit"
                  :to="`/resource/virtual_machines/${row.item.name}`"
                >
                  <b-icon icon="gear" aria-hidden="true"></b-icon>
                </b-button>
              </template>
            </b-table>
          </b-card-body>
        </b-card>
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
  name: 'virtual_machines',
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Resources', active: true},
            {text: 'Virtual Machines', to: '/resource/virtual_machines', active: true},
          ],
          fields: [
            // {key: 'id', label:'ID'},
            {key: 'name', label:'Name'},
            {key: 'cpus', label:'VCPU'},
            {key: 'mem', label:'Memory'},
            {key: 'host', label:'Hypervisor', sortable: true},
            {key: 'host_tag', label:'Tags', sortable: true},
            {key: 'state', label:'State'},
            'actions'
          ],
          searchQuery: ''
      }
  },
  computed: {
    filteredResources () {
      if (this.searchQuery) {
        return this.tableData.filter((item) => {
          return item.name.toLowerCase().includes(this.searchQuery.toLowerCase())
        })
      } else {
        return this.tableData
      }
    },
    filteredData () {
      return this.$store.state.vmsList.filter((item) => {
        return item.name.toLowerCase()
      })
    },
    tableData() {
      return this.filteredData.map(x => ({
        id: x.id,
        name: x.name,
        cpus: x.cpus,
        mem: x.mem,
        host: x.host,
        host_tag: x.host_tag,
        state: x.state
      }))
    }
  },
  mounted () {
    this.requestVirtualMachineList()
  },
  methods: {
    getBadgeType(state) {
      if (state === 'Running') {
        return 'success'
      } else {
        return 'danger'
      }
    },
    getVirtualMachineList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getVirtualMachineList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$store.state.loadingVMs = false
            this.$store.state.vmsList = response.data.info
        } else if (response.data.state === 'FAILURE') {
          this.$bvToast.toast(response.data.status, {
            variant: 'danger',
            solid: true
          })
        }
      })
      .catch(e => {
        console.log(e)
        this.errors.push(e)
      })
    },
    requestVirtualMachineList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getVirtualMachineList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    getHypervisor (id) {
      return this.$store.state.hostsList.filter((item) => {
        return item.id == id
      })
    }
  }
}
</script>
