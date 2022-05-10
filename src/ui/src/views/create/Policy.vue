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
      <h4>Add new backup pool</h4>
      <hr>
      <b-form @submit.stop.prevent="onSubmit">
        <div role="group">
          <b-form-group id="input-group-1" label="Name" label-for="input-1">
            <b-form-input
              id="input-name"
              v-model="$v.form.policyName.$model"
              :state="validateState('policyName')"
              aria-describedby="input-live-help input-live-feedback"
              trim
            ></b-form-input>
            <b-form-invalid-feedback
              id="input-1-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="input-group-3" label="Description" label-for="input-3">
            <b-form-textarea
              id="input-description"
              v-model="$v.form.description.$model"
              :state="validateState('description')"
              aria-describedby="input-live-help input-live-feedback"
              trim
            ></b-form-textarea>
            <b-form-invalid-feedback
              id="input-1-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
        </div>
        <br>
        <b-button block type="submit" variant="info" size="lg">Submit</b-button>
      </b-form>
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
          {text: 'Backups', active: true},
          {text: 'Policies', to: '/backups/policies'},
          {text: 'Add new', to: '/backups/policies/new', active: true},
        ],
        form: {
          policyName: null,
          description: null
        },
        mandatory: 'Ce champs est obligatoire',
        backup_id: null
      }
  },
  validations: {
    form: {
      policyName: {
        required
      },
      description: {
        required
      }
    }
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.form[name];
      return $dirty ? !$error : null;
    },
    onSubmit() {
      this.$v.form.$touch();
      if (this.$v.form.$anyError) {
        return;
      }
      axios.post(`${this.$store.state.endpoint.api}/api/v1/backup_policies`, { name: this.form.policyName, description: this.form.description }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$router.push('/backups/policies')
        this.$root.$bvToast.toast("Backup policy has been successfully created", {
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