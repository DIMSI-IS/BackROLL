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
      <h4>Add hypervisor</h4>
      <hr>
      <b-form @submit.stop.prevent="onSubmit">
        <div role="group">
          <b-form-group id="input-group-1" label="Hostname" label-for="input-1">
            <b-form-input
              id="input-name"
              v-model="$v.form.hostname.$model"
              :state="validateState('hostname')"
              aria-describedby="input-live-help input-live-feedback"
              trim
            ></b-form-input>
            <b-form-invalid-feedback
              id="input-1-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="input-group-2" label="IP Address" label-for="input-2">
            <b-form-input
              id="input-ip"
              v-model="$v.form.ipAddress.$model"
              :state="validateState('ipAddress')"
              aria-describedby="input-live-help input-live-feedback"
              trim
            ></b-form-input>
            <b-form-invalid-feedback
              id="input-2-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="input-group-3" label="Select pool" label-for="input-3">
            <b-form-select
              v-model="$v.form.pool.$model"
              :state="validateState('pool')"
              :options="selectData"
            />
            <b-form-invalid-feedback
              id="input-3-live-feedback"
            >
              {{ mandatory}}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="input-group-1" label="Tag (optional)" label-for="input-1">
            <b-form-input
              id="input-name"
              v-model="hostTag"
              aria-describedby="input-live-help input-live-feedback"
              trim
            />
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
          {text: 'Resources', active: true},
          {text: 'Hypervisors', to: '/resource/hypervisors'},
          {text: 'Add new', to: '/resource/new/hypervisor', active: true},
        ],
        form: {
          hostname: null,
          ipAddress: null,
          pool: null
        },
        mandatory: 'This field is mandatory',
        hostTag: null
      }
  },
  validations: {
    form: {
      hostname: {
        required
      },
      ipAddress: {
        required
      },
      pool: {
        required
      }
    }
  },
  computed: {
    selectData() {
      return this.$store.state.poolsList.map(x => ({
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
      console.log(this.tagList)
      axios.post(`${this.$store.state.endpoint.api}/api/v1/hosts`, { hostname: this.form.hostname, tags: this.hostTag, ip_address: this.form.ipAddress, pool_id: this.form.pool.id }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$router.push('/resource/hypervisors')
        this.$root.$bvToast.toast("Host has been successfully created", {
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