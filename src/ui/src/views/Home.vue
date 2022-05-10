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
      <b-card-group deck>
        <card-widget :loading="this.$store.state.loadingPools" title="Pool(s)" icon="collection" :quantity="this.$store.state.poolsList.length" />
        <card-widget :loading="this.$store.state.loadingHosts" title="Hypervisor(s)" icon="hdd-stack" :quantity="this.$store.state.hostsList.length" />
        <card-widget :loading="this.$store.state.loadingVMs" title="Virtual machine(s)" icon="display" :quantity="this.$store.state.vmsList.length" />
      </b-card-group>
    </div>
  </div>
</template>
<script>
import CardWidget from '../components/CardWidget.vue'
export default {
  name: 'Dashboard',
  components: { CardWidget },
  data() {
      return {
          items: [
            {text: 'Dashboard', to: '/', active: true},
          ],
      }
  },
}
</script>