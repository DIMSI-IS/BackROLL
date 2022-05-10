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
    <div class="main-content">
      <!-- {{ retention }} -->
      <div v-if="strategy[0] !== undefined" fluid="sm">
        <b-row>
          <b-col>
            <h2> {{ strategy[0].name }} </h2>
          </b-col>
          <b-col style="text-align: right;">
            <h2>
              Enabled: 
              <b-badge :variant="getBadgeType(strategy[0].enabled)">
                {{ strategy[0].enabled === 0 ? 'False' : 'True' }}
              </b-badge>
            </h2>
          </b-col>
        </b-row>
        <b-row v-if="nextTick !== null">
          <b-col>
            Next execution: {{ nextTick }}
          </b-col>
        </b-row>
        <hr>
        <b-row>
          <b-col md="3">
            <b-list-group style="padding: 0 0 2% 0;">
              <b-list-group-item button :active="active == 0" @click="active = 0">Information</b-list-group-item>
              <b-list-group-item button :active="active == 1" @click="active = 1">Policy</b-list-group-item>
              <b-list-group-item button :active="active == 2" @click="active = 2">Target resources</b-list-group-item>
            </b-list-group>
          </b-col>
          <b-col md="9">
            <b-card>
              <div v-if="active == 0">
                <b-card-text>
                  <label>
                    <strong> Description </strong>
                  </label>
                  <b-row class="mt-2" style="padding: 0 1% 0 1%;">
                    <b-form-textarea
                      id="textarea-default"
                      v-model="strategyDescription"
                      placeholder="Add a description here..."
                    />
                  </b-row>
                </b-card-text>
              </div>
              <div v-if="active === 1">
                <b-card-text>
                  <label> 
                    <strong> Planning Policy </strong>
                  </label>
                  <b-form-checkbox
                    id="checkbox-1"
                    v-model="schedule"
                    name="checkbox-1"
                    :value="true"
                    :unchecked-value="false"
                  >
                    Backup planing
                  </b-form-checkbox>
                  <br>
                  <b-alert show variant="primary" v-if="!schedule">
                    Backup retention is not available if no schedule is enabled
                  </b-alert>
                  <div v-if="schedule">
                    <label>Selected day(s) to perform the backups</label>
                    <b-form-select v-model="selected" :options="days" multiple :select-size="7"/>
                    <div style="text-align: right;">
                      <em> Hold CTRL for multi-select </em>
                    </div>
                    <br>
                    <label>Time of backup</label>
                    <b-form-timepicker
                      v-model="backupTime"
                      locale="de"
                      label-no-time-selected="Aucun horaire indiqué"
                    />
                    <hr>
                    <label> 
                      <strong> Retention policy </strong>
                    </label>
                    <br>
                    <b-alert show variant="primary">
                      <p>Backups kept over a sliding time interval are filled in.</p>
                      <p>For example: If the value <em>Daily</em> is set to 4, this means that we keep 1 backup per day for the last 4 days (4 backups in total)</p>
                    </b-alert>
                    <b-row>
                      <b-col sm style="text-align: center;">
                        <div> Daily </div>
                        <b-form-spinbutton
                          id="sb-vertical"
                          v-model="daily"
                          :min="0"
                          :max="30"
                          vertical
                        />
                      </b-col>
                      <b-col sm  style="text-align: center;">
                        <div> Weekly </div>
                        <b-form-spinbutton
                          id="sb-vertical"
                          v-model="weekly"
                          :min="0"
                          :max="7"
                          vertical
                        />
                      </b-col>
                      <b-col sm  style="text-align: center;">
                        <div> Monthly </div>
                        <b-form-spinbutton
                          id="sb-vertical"
                          v-model="monthly"
                          :min="0"
                          :max="12"
                          vertical
                        />
                      </b-col>
                      <b-col sm  style="text-align: center;">
                        <div> Yearly </div>
                        <b-form-spinbutton
                          id="sb-vertical"
                          v-model="yearly"
                          :min="0"
                          :max="4"
                          vertical
                        />
                      </b-col>
                    </b-row>
                    <div v-if="validPlanification">
                      <br>
                      <b-card title="Policy summary">
                        <label> 
                          <strong> Planner </strong>
                        </label>
                        <p>A backup will be made every :</p>
                        <ul>
                          <li v-for="item in parseDays" :key="item">
                            {{ item }}
                          </li>
                        </ul>
                        <p>At {{ backupTime }}</p>
                        <label> 
                          <strong> Retention </strong>
                        </label>
                        <p>The retained backups are:</p>
                        <p v-if="daily > 0">
                          {{ daily }} selected rolling day(s) <strong>*</strong>
                        </p>
                        <p v-if="weekly > 0">
                          {{ weekly }} selected rolling week(s) <strong>*</strong>
                        </p>
                        <p v-if="monthly > 0">
                          {{ monthly }} selected rolling month(s) <strong>*</strong>
                        </p>
                        <p v-if="yearly > 0">
                          {{ yearly }} selected rolling year(s) <strong>*</strong>
                        </p>
                        <b-alert show>(*) One backup per VM and per occurrence in each cycle</b-alert>
                      </b-card>
                      <div v-if="parseInt(this.strategy[0].enabled) === 0">
                        <hr>
                        <div v-if="alertRetention.state == 'Warning'">
                          <br>
                          <b-alert show variant="warning">
                            <a href="#" class="alert-link">
                              <ul>
                                <li v-for="item in alertRetention.message" :key="item">
                                  {{ item }} for each element concerned
                                </li>
                              </ul>
                            </a>
                          </b-alert>
                        </div>
                        <b-button block variant="primary" @click="enableScheduledPolicy()">
                          Enable policy
                        </b-button>
                      </div>
                    </div>
                  </div>
                </b-card-text>
              </div>
              <div v-if="active === 2">
                <b-card-text>
                  <label>
                    <strong>The following resources are affected by this strategy </strong>
                  </label>
                  <br>
                  <div v-if="this.$store.state.loadingPools || this.$store.state.loadingHosts || this.$store.state.loadingVMs" style="text-align: center;">
                    <b-spinner style="margin-right: 50px; margin-top: 10px;" variant="primary" type="grow" label="Spinning" />
                  </div>
                  <div v-else>
                    <h4>
                      <b-badge v-b-tooltip.hover :title="item.host" style="margin-right: 20px;" variant="info" v-for="(item) in targets" :key="item.id">
                        {{item.name}}
                      </b-badge>
                    </h4>
                  </div>
                </b-card-text>
              </div>
            </b-card>
          </b-col>
        </b-row>
      </div>
      <br>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
export default {
  data() {
    return {
        items: [
          {text: 'Dashboard', to: '/'},
          {text: 'Policies', to: '/backups/policies'},
          {text: this.$route.params.name.toUpperCase(), to: `/backups/policies/${this.$route.params.id}`, active: true}
        ],
        active: 0,
        days: [
          { value: 1, text: 'Monday' },
          { value: 2, text: 'Tuesday' },
          { value: 3, text: 'Wednesday' },
          { value: 4, text: 'Thursday'},
          { value: 5, text: 'Friday' },
          { value: 6, text: 'Saturday' },
          { value: 0, text: 'Sunday' }
        ],
        loadingTargets: true,
        schedule: null,
        backupTime: null,
        selected: [],
        daily: 0,
        weekly: 0,
        monthly: 0,
        yearly: 0,
        strategyDescription: null

    }
  },
  computed: {
    alertRetention () {
      const retention = JSON.parse(this.strategy[0].retention)
      let json = {
        state: 'OK',
        message: []
      }
      if (this.daily < retention.daily) {
        json.state = 'Warning'
        json.message.push(`Please note that this change will result in the removal of ${retention.daily - this.daily} daily backup(s)`)
      }
      if (this.weekly < retention.weekly) {
        json.state = 'Warning'
        json.message.push(`Please note that this change will result in the removal of ${retention.weekly - this.weekly} weekly backup(s)`)
      }
      if (this.monthly < retention.monthly) {
        json.state = 'Warning'
        json.message.push(`Please note that this change will result in the removal of ${retention.monthly - this.monthly} monthly backup(s)`)
      }
      if (this.yearly < retention.yearly) {
        json.state = 'Warning'
        json.message.push(`Please note that this change will result in the removal of ${retention.yearly - this.yearly} yearly backup(s)`)
      }
      return json
    },
    strategy () {
      return this.$store.state.backupPolicyList.filter((item) => {
        return item.id == this.$route.params.id
      })
    },
    interval () {
      var parser = require('cron-parser')
      var options = {
        currentDate: new Date(),
        tz: 'Europe/Paris'
      }
      if (this.strategy[0].schedules) {
        try {
          return parser.parseExpression(this.strategy[0].schedules, options)
        } catch (err) {
          return null
        }
      } else {
        return null
      }
    },
    nextTick () {
      if (this.interval !== null) {
        const options = { hour: 'numeric', minute: 'numeric' }
        return `${new Date(this.interval.next()).toLocaleDateString(undefined, options).toString()}`
      } else {
        return null
      }
    },
    cronPlanification () {
      return `${parseInt(this.backupTime.split(":")[1])} ${parseInt(this.backupTime.split(":")[0])} * * ${this.selected.join()}`
    },
    saveRetention () {
      return `{"daily":${this.daily}, "weekly":${this.weekly}, "monthly":${this.monthly}, "yearly":${this.yearly}}`
    },
    parseDays () {
      var array = []
      this.days.filter((item) => {
        if (this.selected.includes(item.value)) {
          array.push(item.text)
        }
      })
      return array
    },
    validPlanification () {
      if (this.backupTime !== null && this.selected.length > 0) {
        if (this.daily !== 0 || this.weekly !== 0 || this.monthly !== 0 || this.yearly !== 0) {
          return true
        } else {
          return false
        }
      } else {
        return false
      }
    },
    host_list() {
      if (this.$store.state.poolsList) {
        var poolList = this.$store.state.poolsList.filter((item) => {
          return item.backup_id == this.strategy[0].id
        })
        var host_list = []
        poolList.forEach((pool) => {
          this.$store.state.hostsList.forEach((host) => {
            if (pool.id == host.pool) {
              host_list.push(host)
            }
          })
        })
        return host_list
      } else {
        return null
      }
    },
    targets () {
      if (this.$store.state.poolsList) {
        var vm_list = []
        this.host_list.forEach((host) => {
          this.$store.state.vmsList.forEach((vm) => {
            if (host.id == vm.host) {
              vm_list.push(vm)
            }
          })
        })
        return vm_list
      } else {
        return null
      }
    }
  },
  watch: {
    strategy: function () {
      this.strategyAnalyzer()
    },
  },
  mounted () {
    this.strategyAnalyzer()
  },
  methods: {
    strategyAnalyzer () {
      if (this.strategy[0]) {
        this.parseScheduling()
        this.parseDescription()
        this.getBackupDays()
        this.getRetention()
        this.getBackupTime()
      }
    },
    parseDescription() {
      this.strategyDescription = this.strategy[0].description
    },
    parseScheduling () {
      if (parseInt(this.strategy[0].enabled) === 0) {
        this.schedule = false
      } else {
        this.schedule = true
      }
    },
    enableScheduledPolicy () {
      axios.patch(`${this.$store.state.endpoint.api}/api/v1/backup_policies/${this.$route.params.id}`, { policy_id: this.$route.params.id, description: this.strategyDescription, schedule: this.cronPlanification, retention: {daily: this.daily, weekly: this.weekly, monthly: this.monthly, yearly: this.yearly}, enabled: true }, { headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$keycloak.token}`}})
      .then(response => {
        this.$router.push('/backups/policies')
        this.$root.$bvToast.toast("Backup policy has been successfully enabled", {
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
    getBadgeType(state) {
      if (state === 1) {
        return 'success'
      } else {
        return 'danger'
      }
    },
    getBackupDays () {
      if (this.interval !== null) {
        this.selected = this.interval.fields.dayOfWeek
      } else {
        this.selected = []
      }
    },
    getBackupTime () {
      if (this.interval !== null) {
        this.backupTime = `${this.interval.fields.hour}:${this.interval.fields.minute}:${this.interval.fields.second}`
      } else {
        this.backupTime = null
      }
    },
    getRetention () {
      const retention = JSON.parse(this.strategy[0].retention)
      if (this.interval !== null) {
        this.daily = retention.daily.valueOf()
        this.weekly = retention.weekly.valueOf()
        this.monthly = retention.monthly.valueOf()
        this.yearly = retention.yearly.valueOf()
      }
    }
  }
}
</script>
