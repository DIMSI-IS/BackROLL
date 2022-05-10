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
    <div class="form-content">
      <div v-if="isCreating" style="text-align: center;">
        <b-spinner variant="primary" label="Spinning" />
        <br>
        <span>
          <h5>Submitting task...</h5>
        </span>
      </div>
      <div v-else>
        <h4>New task</h4>
        <hr>
        <b-form @submit.stop.prevent="onSubmit">
          <div role="group">
            <b-form-group id="input-group-1" label="Task selection" label-for="input-1">
              <b-form-select
                v-model="$v.form.taskType.$model"
                :options="selectData"
              />
              <b-form-invalid-feedback
                id="input-3-live-feedback"
              >
                {{ mandatory}}
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group v-if="form.taskType == '7b9074f2-989a-11ec-96b4-52540076c39b'" id="input-group-2" label="Virtual machine selection" label-for="input-2">
              <b-form-select
                v-model="$v.form.taskTarget.$model"
                :options="vmSelect"
              />
              <b-form-invalid-feedback
                id="input-3-live-feedback"
              >
                {{ mandatory}}
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group v-if="form.taskType == '894fbeea-989a-11ec-96b4-52540076c39b'" id="input-group-2" label="Pool selection" label-for="input-2">
              <b-form-select
                v-model="$v.form.taskTarget.$model"
                :options="poolSelect"
              />
              <b-form-invalid-feedback
                id="input-3-live-feedback"
              >
                {{ mandatory}}
              </b-form-invalid-feedback>
            </b-form-group>
          </div>
          <br>
          <b-button block type="submit" variant="info" size="lg" :disabled="isCreating || (form.taskType == null || form.taskTarget == null)">Submit</b-button>
        </b-form>
      </div>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
import Vue from 'vue'
import { validationMixin } from "vuelidate";
import { required } from "vuelidate/lib/validators";
Vue.prototype.$multiwatch = function (props, watcher) {
  const iterator = function (prop) {
    this.$watch(prop, watcher)
  }
  props.forEach(iterator, this)
}
export default {
  mixins: [validationMixin],
  name: 'createHypervisor',
  data() {
      return {
        items: [
            {text: 'Dashboard', to: '/'},
            {text: 'Backups', to: '/backups', active: true},
            {text: 'Tasks', to: '/backups/tasks'},
            {text: 'New task', to: '/backups/tasks/new', active: true}
        ],
        form: {
          taskType: null,
          taskTarget: null
        },
        mandatory: 'This field is mandatory',
        rawTaskOptions: [],
        isCreating: false
      }
  },
  validations: {
    form: {
      taskType: {
        required
      },
      taskTarget: {
        required
      }
    }
  },
  computed: {
    filteredVMData () {
      return this.$store.state.vmsList.filter((item) => {
        return item.name.toLowerCase().match('^((?!^r-)(?!^s-)(?!^v-).)*$')
      })
    },
    filteredTasks () {
      return this.rawTaskOptions.filter((item) => {
        return item.type == 'backup'
      })
    },
    selectData() {
      if (this.filteredTasks) {
        return this.filteredTasks.map(x => ({
          value: x.id,
          text: x.name
        }))
      } else {
        return []
      }
    },
    vmSelect() {
      return this.filteredVMData.map(x => ({
        value: x.uuid,
        text: x.name
      })).sort((a, b) => a.text > b.text ? 1 : -1)
    },
    poolSelect() {
      return this.$store.state.poolsList.map(x => ({
        value: x,
        text: x.name
      }))
    }
  },
  mounted () {
    this.requestJobList()
  },
  methods: {

    getJobList: function (location) {
      axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: {'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        if (response.data.state === 'PENDING' || response.data.state == 'STARTED') {
          setTimeout(()=>{
            this.getJobList(location)
          },2000)
        } else if (response.data.state === 'SUCCESS') {
            this.$store.state.loadingVMs = false
            this.rawTaskOptions = response.data.info
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
    requestJobList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/jobs`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getJobList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    requestBackupPolicyList: function () {
      axios.get(`${this.$store.state.endpoint.api}/api/v1/list/backup_policies`, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.getBackupPolicyList(response.data.Location)
      })
      .catch(e => {
        this.errors.push(e)
      })
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.form[name];
      return $dirty ? !$error : null;
    },
    parsePool (id) {
      return this.$store.state.hostsList.filter((item) => {
        return item.pool == id
      })
    },
    onSubmit() {
      // Pool VM backup
      if (this.form.taskType == '894fbeea-989a-11ec-96b4-52540076c39b') {
        console.log(this.form.taskTarget.id)
        axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/poolbackup/${this.form.taskTarget.id}`, { pool_id: this.form.taskTarget.id }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
        .then(response => {
          this.isCreating = true
          this.$v.form.$touch();
          if (this.$v.form.$anyError) {
            return;
          }
          this.$router.push('/backups/tasks')
          this.$root.$bvToast.toast("Backup task has been successfully triggered", {
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
      
      // Single VM backup
      } else if (this.form.taskType == '7b9074f2-989a-11ec-96b4-52540076c39b') {
        axios.post(`${this.$store.state.endpoint.api}/api/v1/tasks/singlebackup/${this.form.taskTarget}`, { virtual_machine_id: this.form.taskTarget }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
        .then(response => {
          this.isCreating = true
          this.$v.form.$touch();
          if (this.$v.form.$anyError) {
            return;
          }
          this.$router.push('/backups/tasks')
          this.$root.$bvToast.toast("Backup task has been successfully triggered", {
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
}
</script>