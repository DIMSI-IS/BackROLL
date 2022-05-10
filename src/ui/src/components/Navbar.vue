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
  <div class="nav-content">
    <b-navbar class="nav-style" toggleable="lg" type="dark" fixed>
      <img src="../../public/storing-backup.svg" width="80" height="30" class="d-inline-block align-top" alt="BackRoll">
      <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>
      <b-collapse id="nav-collapse" is-nav>
        <b-navbar-nav style="padding: 0 0 0 2.5%;">
          <b-nav-item-dropdown right>
            <template slot="button-content">
                <b-icon icon="box-seam"></b-icon>
                Resources
            </template>
            <b-dropdown-item @click="$router.push('/backups/policies').catch(()=>{})"><b-icon-calendar style="padding-right: 5px;"></b-icon-calendar><span>Policies</span></b-dropdown-item>
            <b-dropdown-item @click="$router.push('/resource/pools').catch(()=>{})"><b-icon-box style="padding-right: 5px;"></b-icon-box><span>Pools</span></b-dropdown-item>
            <b-dropdown-item @click="$router.push('/resource/hypervisors').catch(()=>{})"><b-icon-menu-button-wide-fill style="padding-right: 5px;"></b-icon-menu-button-wide-fill><span>Hypervisors</span></b-dropdown-item>
            <b-dropdown-item @click="$router.push('/resource/virtual_machines').catch(()=>{})"><b-icon-display style="padding-right: 5px;"></b-icon-display><span>Virtual machines</span></b-dropdown-item>
          </b-nav-item-dropdown>
          <b-nav-item-dropdown right>
            <template slot="button-content">
                <b-icon icon="cloud-arrow-up"></b-icon>
                Backup
            </template>
            <b-dropdown-item @click="$router.push('/backups/tasks').catch(()=>{})"><b-icon icon="list-task" style="padding-right: 5px;"></b-icon><span>Tasks</span></b-dropdown-item>
          </b-nav-item-dropdown>
          <b-nav-item-dropdown right>
            <template slot="button-content">
                <b-icon icon="arrow-repeat"></b-icon>
                Restore
            </template>
            <b-dropdown-item @click="$router.push('/restore/tasks').catch(()=>{})"><b-icon icon="list-task" style="padding-right: 5px;"></b-icon><span>Tasks</span></b-dropdown-item>
          </b-nav-item-dropdown>
        </b-navbar-nav>

        <!-- Right aligned nav items -->
        <b-navbar-nav class="ml-auto">
          <b-nav-item style="padding-top: 3%;" href="https://github.com/dimsi/backroll" target="_blank">v0.1.0 <b-icon icon="github" /></b-nav-item>
          <b-nav-item>
            <b-button
              variant="danger"
              @click="$keycloak.logoutFn()"
            >
              <b-icon icon="power" aria-hidden="true"></b-icon> Sign out
            </b-button>
          </b-nav-item>
        </b-navbar-nav>
      </b-collapse>
    </b-navbar>
  </div>
</template>

<script>
</script>
