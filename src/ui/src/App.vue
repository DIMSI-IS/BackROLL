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
  <div id="app">
    <vue-topprogress
      ref="topProgress"
      :height="6"
      :maximum="88.7"
    />
    <Navbar />
    <router-view/>
  </div>
</template>

<script>
import axios from 'axios'
import Vue from 'vue'
import Navbar from './components/Navbar.vue'
import { vueTopprogress } from 'vue-top-progress'

Vue.prototype.$multiwatch = function (props, watcher) {
  const iterator = function (prop) {
    this.$watch(prop, watcher)
  }
  props.forEach(iterator, this)
}
export default {
  name: 'App',
  components: {
    Navbar,
    vueTopprogress
  },
  mounted () {
    this.$refs.topProgress.start()
    this.requestSSHPublicKey()
    this.requestPoolList()
    this.requestHostList()
    this.requestBackupPolicyList()
    this.requestVirtualMachineList()
  },
  methods: {
    getPoolList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, {headers: { 'Authorization': `Bearer ${this.$keycloak.token}` }})
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
    getBackupPolicyList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
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
    getHostList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getHostList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$store.state.loadingHosts = false
            this.$store.state.hostsList = response.data.info
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
    requestHostList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/hosts`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getHostList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    getVirtualMachineList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getVirtualMachineList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$refs.topProgress.done()
            this.$store.state.loadingVMs = false
            this.$store.state.vmsList = response.data.info
        } else if (response.data.state === 'FAILURE') {
          this.$refs.topProgress.done()
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
    requestVirtualMachineList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/virtualmachines`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getVirtualMachineList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    retrieveJobs() {
      this.$store.state.loadingJobs = true
    },
    requestSSHPublicKey() {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/publickeys`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$store.state.sshPublicKey = response.data.info.public_key
      })
      .catch(e => {
        console.log(e)
      })
    },
    updateTaskList: function () {
      const self = this
      this.$store.dispatch('getTaskList')
        .then(
          setTimeout(function () {
            self.updateTaskList()
          }, 5000)
        )
    },
  }
}
</script>
