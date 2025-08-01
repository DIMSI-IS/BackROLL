<template>
  <div>
    <va-card>
      <va-card-title>
        <ListHeader
          title="Hypervisors"
          plus-button-title="Add hypervisor"
          plus-button-route="/admin/resources/hypervisors/new"
          :dependencies-resolved="areDependenciesResolved"
          dependencies-message="You need to create a pool."
          go-button-title="Go to pools"
          go-button-route="/admin/resources/pools"
        />
      </va-card-title>
      <va-card-content>
        <va-data-table
          :items="$store.state.resources.hostList"
          :columns="columns"
        >
          <template #cell(name)="{ value }">{{ value.toUpperCase() }}</template>
          <template #cell(pool_id)="{ value }">
            <va-chip
              v-if="getPool(value)"
              size="small"
              square
              @click="this.$router.push('/admin/resources/pools')"
            >
              {{ getPool(value) }}
            </va-chip>
          </template>
          <template #cell(ipaddress)="{ value }">
            <va-chip size="small" square outline>
              {{ value }}
            </va-chip>
          </template>
          <template #cell(ssh)="{ value }">
            <va-chip
              size="small"
              square
              outline
              :color="JSON.parse(value) ? 'success' : 'danger'"
            >
              <va-icon v-if="!JSON.parse(value)" name="warning" />
              {{ JSON.parse(value) ? "Configured" : "Unconfigured" }}
            </va-chip>
          </template>
          <template #cell(tags)="{ value }">
            <va-chip v-if="value" size="small" square outline>
              {{ value }}
            </va-chip>
          </template>
          <template #cell(state)="{ value }">
            <va-chip
              size="small"
              :color="value === 'Reachable' ? 'success' : 'danger'"
            >
              {{ value === "Reachable" ? "Reachable" : "Unreachable" }}
            </va-chip>
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button
                v-if="!$store.state.resources.hostList[rowIndex].ssh"
                icon="link"
                :disabled="sshKeys.length == 0"
                @click="
                  (selectedHost = $store.state.resources.hostList[rowIndex]),
                    (showConnectModal = true)
                "
              />
              <va-button
                icon="settings"
                @click="
                  this.$router.push(
                    `/admin/resources/hypervisors/${$store.state.resources.hostList[rowIndex].id}`
                  )
                "
              />
              <va-button
                icon="delete"
                @click="
                  (selectedHost = $store.state.resources.hostList[rowIndex]),
                    (showDeleteModal = true)
                "
              />
            </va-button-group>
          </template>
        </va-data-table>
        <div v-if="!$store.state.isHostTableReady" class="flex-center ma-3">
          <spring-spinner
            :animation-duration="2000"
            :size="30"
            color="#2c82e0"
          />
        </div>
      </va-card-content>
    </va-card>
    <va-modal v-model="showConnectModal" size="large" hide-default-actions>
      <template #header>
        <h2>
          <va-icon name="link" />
          Connecting to the hypervisor at {{ selectedHost.hostname }}
        </h2>
      </template>
      <hr class="mb-4" />
      <va-form ref="form" @validation="(validation = $event), connectHost()">
        <va-input
          label="Specify the user on the server"
          messages="The user must have the access rights to KVM."
          v-model="user"
          type="text"
          :rules="[(value) => value?.trim().length > 0 || 'Field is required']"
          class="mb-3"
        />
        <va-tabs v-model="currentTabKey">
          <template #tabs>
            <va-tab v-for="{ name } in sshKeys" :key="name" :name="name">
              {{ name.toUpperCase() }}
            </va-tab>
          </template>
          <div style="position: relative">
            <va-input
              label="BackROLL SSH key"
              messages="Copy-paste one of the keys into the ~/.ssh/authorized_keys file on the server."
              v-model="currentSshKey"
              type="textarea"
              :autosize="true"
              :min-rows="2"
              readonly
              class="mb-4"
            />
            <va-icon
              :name="isKeyCopied ? 'check' : 'content_copy'"
              :size="20"
              @click="copyToClipboard(currentSshKey)"
              style="
                position: absolute;
                top: 0;
                right: 0;
                margin-top: 6px;
                margin-right: 4px;
              "
            />
          </div>
        </va-tabs>
        <div class="d-flex">
          <va-button flat @click="showConnectModal = false"> Cancel </va-button>
          <va-spacer class="spacer" />
          <va-button @click="$refs.form.validate()"> Done </va-button>
        </div>
      </va-form>
    </va-modal>
    <va-modal v-model="showDeleteModal" @ok="deleteHost()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          Removing hypervisor
        </h2>
      </template>
      <hr />
      <div>
        You are about to remove hypervisor
        <b>{{ JSON.parse(JSON.stringify(this.selectedHost)).hostname }}</b
        >. <br />Please confirm action.
      </div>
    </va-modal>
  </div>
</template>

<script>
import axios from "axios";
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";

import ListHeader from "@/components/lists/ListHeader.vue";

export default defineComponent({
  name: "HypervisorsTable",
  components: {
    ...spinners,
    ListHeader,
  },
  data() {
    return {
      columns: [
        { key: "hostname" },
        { key: "pool_id", label: "Pool", sortable: true },
        { key: "ipaddress" },
        { key: "ssh", label: "SSH Connection" },
        { key: "tags", sortable: true },
        { key: "state", sortable: true },
        { key: "actions" },
      ],
      validation: false,
      user: null,
      sshKeys: [],
      currentTabKey: null,
      isKeyCopied: false,
      showConnectModal: false,
      showDeleteModal: false,
      selectedHost: null,
    };
  },
  computed: {
    areDependenciesResolved() {
      // Prevent showing irrelevant alert by checking if the table is ready.
      return (
        !this.$store.state.isPoolTableReady ||
        this.$store.state.resources.poolList.length > 0
      );
    },
    currentSshKey() {
      return this.sshKeys.find(({ name }) => name == this.currentTabKey)
        ?.fullLine;
    },
  },
  watch: {
    sshKeys(newValue) {
      this.currentTabKey = newValue[0]?.name;
    },
    showConnectModal(newValue, oldValue) {
      if (newValue && !oldValue) {
        this.isKeyCopied = false;
      }
    },
    currentTabKey() {
      this.isKeyCopied = false;
    },
  },
  methods: {
    copyToClipboard(text) {
      // Works in HTTP (unsafe context).

      // Crée un élément textarea temporaire
      const textarea = document.createElement("textarea");
      textarea.value = text;

      // Ajoute le textarea au document
      document.body.appendChild(textarea);

      // Sélectionne le texte dans le textarea
      textarea.select();
      textarea.setSelectionRange(0, 99999); // Pour les appareils mobiles

      // Copie le texte sélectionné dans le presse-papier
      document.execCommand("copy");

      // Supprime le textarea du document
      document.body.removeChild(textarea);

      this.isKeyCopied = true;
    },
    getPool(id) {
      const result = this.$store.state.resources.poolList.find(
        (item) => item.id === id
      );
      if (result) {
        return result.name.toUpperCase();
      } else {
        return null;
      }
    },
    connectHost() {
      if (this.validation) {
        axios
          .post(
            `${this.$store.state.endpoint.api}/api/v1/connect/${this.selectedHost.id}`,
            { ip_address: this.selectedHost.ipaddress, username: this.user },
            {
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${this.$store.state.token}`,
              },
            }
          )
          .then((response) => {
            this.$store.dispatch("requestHost");
            this.$vaToast.init({
              title: response.data.state,
              message: `Successfully connected to ${this.selectedHost.hostname}`,
              color: "success",
            });
            this.showConnectModal = false;
          })
          .catch((error) => {
            console.error(error);
            this.$vaToast.init({
              title: "Error",
              message: error?.response?.data?.detail ?? error,
              color: "danger",
            });
          });
      }
    },
    requestKeys() {
      axios
        .get(`${this.$store.state.endpoint.api}/api/v1/publickeys`, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.$store.state.token}`,
          },
        })
        .then((response) => {
          this.sshKeys = response.data.info.map(({ name, full_line }) => ({
            name,
            fullLine: full_line,
          }));
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: "Unable to retrieve BackROLL SSH keys",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
    deleteHost() {
      axios
        .delete(
          `${this.$store.state.endpoint.api}/api/v1/hosts/${this.selectedHost.id}`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestHost");
          this.$vaToast.init({
            title: response.data.state,
            message: "Hypervisor has been successfully deleted",
            color: "success",
          });
          if (response.data.warnings?.length > 0) {
            for (const warning of response.data.warnings) {
              this.$vaToast.init({
                title: "Warning",
                message: warning,
                color: "warning",
              });
            }
          }
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: "Unable to delete Hypervisor",
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
  mounted() {
    this.requestKeys();
    this.$store.dispatch("requestHost");
  },
});
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
