<template>
  <va-card>
    <va-card-title>
      <FormHeader
        :title="
          hypervisorId
            ? $t('pages.resources.hypervisor.updating', { name: stateHypervisor?.hostname ?? '' })
            : $t('pages.resources.hypervisor.adding')
        "
      />
    </va-card-title>
    <va-card-content v-if="!hypervisorId || stateHypervisor">
      <va-form ref="form">
        <va-input
          :label="$t('pages.resources.hypervisor.hostname')"
          v-model="formHypervisor.hostname"
          :rules="[
            (value) => value?.length > 0 || $t('pages.resources.common.required'),
            (value) =>
              isHypervisorNameUnique(value) || $t('pages.resources.hypervisor.hostnameUsed'),
          ]"
        />
        <br />
        <va-input
          :label="$t('pages.resources.hypervisor.address')"
          v-model="formHypervisor.ipAddress"
          :rules="[
            (value) =>
              /^[0-9a-zA-Z.-]+$/.test(value) ||
              $t('pages.resources.hypervisor.addressInvalid'),
            (value) =>
              isHypervisorAddressUnique(value) ||
              $t('pages.resources.hypervisor.addressUsed'),
          ]"
        />
        <br />
        <va-select
          :label="$t('pages.resources.hypervisor.selectPool')"
          v-model="selectedPool"
          :options="poolOptions"
          :rules="[(value) => value || $t('pages.resources.common.required')]"
        />
        <br />
        <va-input :label="$t('pages.resources.hypervisor.tagOptional')" v-model="formHypervisor.tags" />
      </va-form>
      <br />
      <va-button
        class="mb-3"
        @click="
          $refs.form.validate() &&
            (hypervisorId ? updateHypervisor() : addHypervisor())
        "
      >
        {{ hypervisorId ? $t('pages.resources.common.update') : $t('pages.resources.hypervisor.add') }}
      </va-button>
    </va-card-content>
    <div v-else class="flex-center ma-3">
      <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
    </div>
  </va-card>
</template>

<script>
import axios from "axios";
import * as spinners from "epic-spinners";

import FormHeader from "@/components/forms/FormHeader.vue";
import { canonicalName } from "@/pages/admin/forms";

export default {
  components: {
    ...spinners,
    FormHeader,
  },
  data() {
    return {
      hypervisorId: this.$route.params.id,
      formHypervisor: {
        hostname: null,
        ipAddress: null,
        tags: null,
      },
      selectedPool: null,
      hostnameRules: [
        (value) => value?.length > 0 || "Field is required",
        (value) =>
          !this.otherHypervisors.find((h) => h.hostname === value) ||
          "This hostname is already used",
      ],
      ipAddressRules: [
        (value) =>
          /^[0-9a-zA-Z.-]+$/.test(value) ||
          "Field is required and must be a valid IP address or domain name.",
        (value) =>
          !this.otherHypervisors.find((h) => h.ipaddress === value) ||
          "This IP address is already used",
      ],
    };
  },
  computed: {
    stateHypervisor() {
      return this.$store.state.resources.hostList.find(
        (item) => item.id == this.hypervisorId
      );
    },
    poolOptions() {
      return this.$store.state.resources.poolList.map((e) => ({
        text: e.name,
        value: e.id,
      }));
    },
    otherHypervisors() {
      return this.$store.state.resources.hostList.filter(
        (h) => h.id != this.hypervisorId
      );
    },
  },
  watch: {
    stateHypervisor() {
      this.propagateStateHypervisor();
    },
    poolOptions() {
      if (this.selectedPool != null) {
        this.updatePool(this.selectedPool.value);
      }
    },
  },
  mounted() {
    if (this.stateHypervisor) {
      this.propagateStateHypervisor();
    }
  },
  methods: {
    isHypervisorNameUnique(value) {
      const canonical = canonicalName(value);
      return !this.$store.state.resources.hostList.find(
        ({ id, hostname }) =>
          id != this.hypervisorId && canonicalName(hostname) == canonical
      );
    },
    isHypervisorAddressUnique(value) {
      return !this.$store.state.resources.hostList.find(
        ({ id, ipaddress }) => id != this.hypervisorId && ipaddress == value
      );
    },
    propagateStateHypervisor() {
      this.formHypervisor = { ...this.stateHypervisor };

      this.formHypervisor.ipAddress = this.stateHypervisor.ipaddress;

      this.updatePool(this.formHypervisor.pool_id);
    },
    updatePool(id) {
      this.selectedPool = this.poolOptions.find((e) => e.value == id);
    },
    exportHypervisor() {
      const hypervisor = JSON.parse(JSON.stringify(this.formHypervisor));

      hypervisor.ip_address = this.formHypervisor.ipAddress;
      if (this.selectedPool) {
        hypervisor.pool_id = this.selectedPool.value;
      }

      return hypervisor;
    },
    updateHypervisor() {
      this.$store.dispatch("updateHost", {
        vm: this,
        hostValues: this.exportHypervisor(),
      });
    },
    addHypervisor() {
      axios
        .post(
          `${this.$store.state.endpoint.api}/api/v1/hosts`,
          this.exportHypervisor(),
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${this.$store.state.token}`,
            },
          }
        )
        .then((response) => {
          this.$store.dispatch("requestHost");
          this.$router.push("/admin/resources/hypervisors");
          this.$vaToast.init({
            title: response.data.state,
            message: this.$t('pages.resources.hypervisor.added'),
            color: "success",
          });
        })
        .catch((error) => {
          console.error(error);
          this.$vaToast.init({
            title: this.$t('pages.resources.hypervisor.addFailed'),
            message: error?.response?.data?.detail ?? error,
            color: "danger",
          });
        });
    },
  },
};
</script>

<style></style>
