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
    <div v-if="!this.$store.state.loadingHosts">
      <div class="main-content">
        <b-card title="Hypervisors">
          <div style="text-align: right; margin-bottom: 1%;">
            <b-button variant="info" @click="$router.push('/resource/hypervisors/new').catch(()=>{})">
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
            emptyText="No hypervisor"
            small
          >
            <template #cell(pool_id)="row">
              {{ getPool(row.item.pool_id)[0].name }}
            </template>
            <template #cell(tags)="row">
              {{ row.item.tags }}
            </template>
            <template #cell(state)="row">
              <h5><b-badge :variant="getBadgeType(row.item.state)">{{ row.item.state }}</b-badge></h5>
            </template>
            <template #cell(actions)="row">
              <div style="text-align: right;">
                <b-button
                  v-if="row.item.ssh == 'Unconfigured' && row.item.state == 'Reachable'"
                  size="sm"
                  variant="secondary"
                  class="mb-2"
                  @click="sshConnectModal = !sshConnectModal; selectedHost = row.item; form.username = null; form.password = null; username2 = null"
                >
                  <b-icon icon="key-fill" aria-hidden="true"></b-icon>
                </b-button>
                <b-button
                  style="margin-left: 10px;"
                  size="sm"
                  variant="danger"
                  class="mb-2"
                  v-b-modal.deleteModal
                  v-b-tooltip.hover title="Remove"
                  @click="selectedHost = row.item"
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
    <b-modal
      v-model="sshConnectModal"
      id="sshConnectModal"
      size="lg"
      :title="'Connection to ' + selectedHost.hostname"
      hide-footer
      @ok="first_ssh_connection()"
    >
      <b-tabs content-class="mt-3">        
        <b-card>
          The local user must have access rights to KVM.
        </b-card>
        <br>
        <b-tab :title-link-class="'tab-title'" title="Using IDs" active>
          <b-form @submit.stop.prevent="onSubmit" class="my-4">
            <b-form-group id="input-group-1" label="Username" label-for="input-1">
              <b-form-input
                id="input-username"
                v-model="$v.form.username.$model"
                :state="validateState('username')"
                aria-describedby="input-live-help input-live-feedback"
                trim
              ></b-form-input>
              <b-form-invalid-feedback
                id="input-1-live-feedback"
              >
                {{ mandatory}}
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group id="input-group-2" label="Password" label-for="input-2">
              <b-form-input
                id="input-password"
                type="password"
                v-model="$v.form.password.$model"
                :state="validateState('password')"
                aria-describedby="input-live-help input-live-feedback"
                trim
              ></b-form-input>
              <b-form-invalid-feedback
                id="input-1-live-feedback"
              >
                {{ mandatory}}
              </b-form-invalid-feedback>
            </b-form-group>
            <br>
            <b-button block type="submit" variant="primary">Submit</b-button>
          </b-form>
        </b-tab>
        <b-tab :title-link-class="'tab-title'" title="Using SSH public key">
          <label>
            1. Copy the key below into the authorized_keys file of your server
          </label>
          <b-card no-body class="text-center">
            <div class="bg-light text-dark">
              Example: /{local_user}/.ssh/authorized_keys
            </div>
          </b-card>
          <br>
          <div style="text-align: right; padding-bottom: 5px;">
            <b-button
              size="sm"
              variant="dark"
              v-clipboard:copy="this.$store.state.sshPublicKey"
              v-clipboard:success="onCopy"
              v-clipboard:error="onError"
            >
              <b-icon icon="files" aria-hidden="true"></b-icon>
              Copy to clipboard
            </b-button>
          </div>
          <b-form-textarea
            id="textarea-small"
            size="sm"
            v-model="this.$store.state.sshPublicKey"
            rows="3"
            max-rows="8"
            readonly
          ></b-form-textarea>
          <hr>
          <label>2. Specify the user on the server</label>
          <b-form-input v-model="username2"></b-form-input>
          <br>
          <label>3. Check connection</label>
          <div>
            <b-button
              block
              variant="primary"
              :disabled="!username2"
              @click="trySSHConn()"
            >
              Submit
            </b-button>
          </div>
        </b-tab>
      </b-tabs>
    </b-modal>
    <b-modal
      id="deleteModal"
      size="lg"
      title="Hypervisor deletion"
      okTitle="Yes"
      cancelTitle="No"
      @ok="deleteHost()"
    >
      <p class="my-4">Do you really want to remove hypervisor: {{ selectedHost.hostname }} ?
        <br>
        <em>This action will have no impact on the virtual machines hosted on this hypervisor.</em>
      </p>
    </b-modal>
  </div>
</template>
<script>
import axios from 'axios'
import Vue from 'vue'
import VueClipboard from 'vue-clipboard2'
VueClipboard.config.autoSetContainer = true // add this line
Vue.use(VueClipboard)

import { validationMixin } from "vuelidate";
import { required } from "vuelidate/lib/validators";
export default {
  mixins: [validationMixin],
  name: 'Hypervisors',
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Resources', active: true},
            {text: 'Hypervisors', to: '/resource/hypervisors', active: true},
          ],
          fields: [
            {key: 'hostname', label:'Name'},
            {key: 'pool_id', label:'Pool'},
            {key: 'ipaddress', label:'IP address'},
            {key: 'ssh', label:'SSH access'},
            {key: 'tags', label:'Tag'},
            {key: 'state', label:'State'},
            'Actions'
          ],
          form: {
            username: null,
            password: null
          },
          username2: null,
          mandatory: 'Mandatory field',
          sshConnectModal: false,
          selectedHost: {},
          username: 'root',
          password: ''
      }
  },
  validations: {
    form: {
      username: {
        required
      },
      password: {
        required
      }
    }
  },
  computed: {
    tableData() {
      return this.$store.state.hostsList.map(x => ({
        id: x.id,
        pool_id: x.pool_id,
        hostname: x.hostname,
        ipaddress: x.ipaddress,
        username: x.username,
        ssh: x.ssh === 0 ? 'Unconfigured' : 'Configured',
        tags: x.tags,
        state: x.state
      }))
    }
  },
  mounted () {
    this.requestHostList()
  },
  methods: {
    onCopy: function () {
      this.$bvToast.toast('Public key has been successfully copied to clipboard', {
        title:'Success !',
        autoHideDelay: 5000,
        solid: true
      })
    },
    onError: function () {
      alert('Failed to copy texts')
    },
    getBadgeType(state) {
      if (state === 'Reachable') {
        return 'success'
      } else {
        return 'danger'
      }
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.form[name];
      return $dirty ? !$error : null;
    },
    onSubmit() {
      // Used for SSH connection using credentials
      this.$v.form.$touch();
      if (this.$v.form.$anyError) {
        return;
      }
      this.sshConnectModal = false
      axios.post(`${this.$store.state.endpoint.api}/api/connect/${this.selectedHost.id}`, {'host_id': this.selectedHost.id, 'ip_address': this.selectedHost.ipaddress, 'username': this.form.username, 'password': this.form.password}, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestHostList()
        this.$bvToast.toast("SSH Connection to host is now established", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        console.log(e)
        this.$bvToast.toast('Unable to connect to host. Check your configuration.', {
          title: 'Failure !',
          variant: 'danger',
          solid: true
        })
      })

    },
    trySSHConn() {
      // Used for SSH connection using public key
      this.sshConnectModal = false
      axios.post(`${this.$store.state.endpoint.api}/api/connect/${this.selectedHost.id}`, {'host_id': this.selectedHost.id, 'ip_address': this.selectedHost.ipaddress, 'username': this.username2}, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestHostList()
        this.$bvToast.toast("SSH Connection to host is now established", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        console.log(e)
        this.$bvToast.toast('Unable to connect to host. Check your configuration.', {
          title: 'Failure !',
          variant: 'danger',
          solid: true
        })
      })
    },
    first_ssh_connection(username, password) {
      axios.post(`${this.$store.state.endpoint.api}/api/connect/${this.selectedHost.id}`, {'host_id': this.selectedHost.id, 'ip_address': this.selectedHost.ipaddress, 'username': username, 'password': password}, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestHostList()
        this.$bvToast.toast("SSH Connection to host is now established", {
          title: response.data.state,
          variant: 'success',
          solid: true
        })
      })
      .catch(e => {
        console.log(e)
        this.$bvToast.toast('Unable to connect to host. Check your configuration.', {
          title: 'Failure !',
          variant: 'danger',
          solid: true
        })
      })

    },
    getHostList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
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
        console.log(e)
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
    deleteHost () {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/hosts/${this.selectedHost.id}`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.requestHostList()
        this.$bvToast.toast("Host has been successfully deleted", {
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
    getPool (id) {
      console.log(id)
      return this.$store.state.poolsList.filter((item) => {
        return item.id == id
      })
    }
  }
}
</script>