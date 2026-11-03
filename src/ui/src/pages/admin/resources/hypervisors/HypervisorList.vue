<template>
  <div>
    <va-card>
      <va-card-title>
        <ListHeader
          :title="$t('pages.resources.hypervisor.title')"
          :plus-button-title="$t('pages.resources.hypervisor.addButton')"
          plus-button-route="/admin/resources/hypervisors/new"
          :dependencies-resolved="areDependenciesResolved"
          :dependencies-message="$t('pages.resources.hypervisor.needPool')"
          :go-button-title="$t('pages.resources.hypervisor.goToPools')"
          go-button-route="/admin/resources/pools"
        />
      </va-card-title>
      <va-card-content>
        <va-data-table :no-data-html="$t('pages.common.noItems')"
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
              {{ JSON.parse(value) ? $t('pages.resources.hypervisor.configured') : $t('pages.resources.hypervisor.unconfigured') }}
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
              {{ value === "Reachable" ? $t('pages.resources.hypervisor.reachable') : $t('pages.resources.hypervisor.unreachable') }}
            </va-chip>
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button-group gradient :rounded="false">
              <va-button
                v-if="!$store.state.resources.hostList[rowIndex].ssh"
                icon="link"
                :disabled="(sshKeys.length == 0) || !$store.getters.canEdit"
                @click="
                  (selectedHost = $store.state.resources.hostList[rowIndex]),
                    (showConnectModal = true)
                "
              />
              <va-button :disabled="!$store.getters.canEdit"
                icon="settings"
                @click="
                  this.$router.push(
                    `/admin/resources/hypervisors/${$store.state.resources.hostList[rowIndex].id}`
                  )
                "
              />
              <va-button :disabled="!$store.getters.canEdit"
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
          {{ $t('pages.resources.hypervisor.connectingTo', { name: selectedHost.hostname }) }}
        </h2>
      </template>
      <hr class="mb-4" />
      <va-form ref="form" @validation="(validation = $event), connectHost()">
        <va-input
          :label="$t('pages.resources.hypervisor.sshUser')"
          :messages="$t('pages.resources.hypervisor.sshUserHint')"
          v-model="user"
          type="text"
          :rules="[(value) => value?.trim().length > 0 || $t('pages.resources.common.required')]"
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
              :label="$t('pages.resources.hypervisor.sshKey')"
              :messages="$t('pages.resources.hypervisor.sshKeyHint')"
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
          <va-button flat @click="showConnectModal = false"> {{ $t('pages.resources.common.cancel') }} </va-button>
          <va-spacer class="spacer" />
          <va-button @click="$refs.form.validate()"> {{ $t('pages.resources.common.done') }} </va-button>
        </div>
      </va-form>
    </va-modal>
    <va-modal v-model="showDeleteModal" :ok-text="$t('pages.resources.common.ok')" :cancel-text="$t('pages.resources.common.cancel')" @ok="deleteHost()">
      <template #header>
        <h2>
          <va-icon name="warning" color="danger" />
          {{ $t('pages.resources.hypervisor.removing') }}
        </h2>
      </template>
      <hr />
      <div>
        {{ $t('pages.resources.hypervisor.removeIntro') }}
        <b>{{ JSON.parse(JSON.stringify(this.selectedHost)).hostname }}</b
        >. <br />{{ $t('pages.resources.common.confirmAction') }}
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
    columns() {
      return [
        { key: "hostname", label: this.$t("pages.resources.hypervisor.colHostname") },
        { key: "pool_id", label: this.$t("pages.resources.hypervisor.colPool"), sortable: true },
        { key: "ipaddress", label: this.$t("pages.resources.hypervisor.colIp") },
        { key: "ssh", label: this.$t("pages.resources.hypervisor.colSsh") },
        { key: "tags", label: this.$t("pages.resources.hypervisor.colTags"), sortable: true },
        { key: "state", label: this.$t("pages.resources.hypervisor.colState"), sortable: true },
        { key: "actions", label: this.$t("pages.resources.hypervisor.colActions") },
      ];
    },
    columns() {
      return [
        { key: "hostname", label: this.$t("pages.resources.hypervisor.colHostname") },
        { key: "pool_id", label: this.$t("pages.resources.hypervisor.colPool"), sortable: true },
        { key: "ipaddress", label: this.$t("pages.resources.hypervisor.colIp") },
        { key: "ssh", label: this.$t("pages.resources.hypervisor.colSsh") },
        { key: "tags", label: this.$t("pages.resources.hypervisor.colTags"), sortable: true },
        { key: "state", label: this.$t("pages.resources.hypervisor.colState"), sortable: true },
        { key: "actions", label: this.$t("pages.resources.hypervisor.colActions") },
      ];
    },
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
        (item) => String(item.id) === String(id)
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
              message: this.$t('pages.resources.hypervisor.connected', { name: this.selectedHost.hostname }),
              color: "success",
            });
            this.showConnectModal = false;
          })
          .catch((error) => {
            console.error(error);
            this.$vaToast.init({
              title: this.$t('pages.resources.common.error'),
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
            title: this.$t('pages.resources.hypervisor.keysFailed'),
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
            message: this.$t('pages.resources.hypervisor.deleted'),
            color: "success",
          });
          if (response.data.warnings?.length > 0) {
            for (const warning of response.data.warnings) {
              this.$vaToast.init({
                title: this.$t('pages.resources.common.warning'),
                message: warning,
                color: "warning",
              });
            }
          }
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t('pages.resources.hypervisor.deleteFailed'),
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
