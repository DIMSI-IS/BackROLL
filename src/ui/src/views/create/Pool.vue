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
      <h4>Add new pool</h4>
      <hr>
      <b-form @submit.stop.prevent="onSubmit">
        <div role="group">
          <b-form-group id="input-group-1" label="Name" label-for="input-1">
            <b-form-input
              id="input-name"
              v-model="$v.form.poolName.$model"
              :state="validateState('poolName')"
              aria-describedby="input-live-help input-live-feedback"
              trim
            ></b-form-input>
            <b-form-invalid-feedback
              id="input-1-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="input-group-3" label="Select backup policy" label-for="input-3">
            <b-form-select
              v-model="selected_backup_policy"
              :options="selectData"
            />
            <b-form-invalid-feedback
              id="input-3-live-feedback"
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
import { required } from "vuelidate/lib/validators"

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
          {text: 'Resources', active: true},
          {text: 'Pools', to: '/resource/pools'},
          {text: 'Add new', to: '/resource/pools/new', active: true},
        ],
        form: {
          poolName: null
        },
        mandatory: 'Ce champs est obligatoire',
        selected_backup_policy: null
      }
  },
  validations: {
    form: {
      poolName: {
        required
      }
    }
  },
  computed: {
    selectData() {
      return this.$store.state.backupPolicyList.map(x => ({
        value: x,
        text: x.name
      }))
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
      axios.post(`${this.$store.state.endpoint.api}/api/v1/pools`, { name: this.form.poolName, backup_policy_id: this.selected_backup_policy.id }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$router.push('/resource/pools')
        this.$root.$bvToast.toast("Pool has been successfully created", {
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