<template>
  <va-card>
    <va-card-title>
      <ListHeader :title="$t('pages.configuration.externalHook.title')" :plus-button-title="$t('pages.configuration.externalHook.addButton')"
        plus-button-route="/admin/configuration/externalhooks/new" />
    </va-card-title>
    <va-card-content>
      <va-data-table :no-data-html="$t('pages.common.noItems')" :items="hookList" :columns="columns">
        <template #cell(value)="{ value }">
          {{ value ? $t('pages.configuration.externalHook.masked') : '' }}
        </template>
        <template #cell(id)="{ value }">
          <va-button-group gradient :rounded="false">
            <va-button :disabled="!$store.getters.canEdit" icon="play_arrow" @click="testHook(value)" />
            <va-button :disabled="!$store.getters.canEdit" icon="settings" :to="`/admin/configuration/externalhooks/${value}`" />
            <va-button :disabled="!$store.getters.canEdit" icon="delete" @click="selectedHookId = value, showDeleteModal = true" />
          </va-button-group>
        </template>
      </va-data-table>
      <div v-if="!$store.state.isexternalHookTableReady" class="flex-center ma-3">
        <spring-spinner :animation-duration="2000" :size="30" color="#2c82e0" />
      </div>
    </va-card-content>
  </va-card>
  <va-modal v-model="showDeleteModal" @ok="deleteHook()">
    <template #header>
      <h2>
        <va-icon name="warning" color="danger" />
        {{ $t('pages.configuration.externalHook.removing') }}
      </h2>
    </template>
    <hr>
    <div>
      {{ $t('pages.configuration.externalHook.removeIntro') }} <b>{{ selectedHook.name }}</b>.
      <br>{{ $t('pages.configuration.common.confirm') }}
    </div>
  </va-modal>
</template>
<script>
import axios from 'axios'
import { defineComponent } from 'vue'
import * as spinners from 'epic-spinners'

import ListHeader from '@/components/lists/ListHeader.vue'

export default defineComponent({
  name: 'PoliciesTable',
  components: {
    ...spinners,
    ListHeader
  },
  data() {
    return {
      selectedHookId: null,
      showDeleteModal: false,
    }
  },
  computed: {
    columns() {
      return [
        { key: 'name', label: this.$t('pages.configuration.common.name') },
        { key: 'value', label: this.$t('pages.configuration.externalHook.value') },
        { key: 'id', label: this.$t('pages.configuration.common.actions') }
      ]
    },
    hookList() {
      return this.$store.state.resources.externalHookList
    },
    selectedHook() {
      return this.hookList.find(({ id }) => id == this.selectedHookId)
    },
  },
  methods: {
    async testHook(id) {
      try {
        const response = await axios.get(`${this.$store.state.endpoint.api}/api/v1/externalhooks/${id}/test`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        this.$vaToast.init({ title: response.data.state, message: this.$t('pages.configuration.externalHook.tested'), color: 'success' })
      } catch (error) {
        console.error(error)
        this.$vaToast.init({
          title: this.$t('pages.configuration.externalHook.testFailed'),
          message: error?.response?.data?.detail ?? error,
          color: 'danger'
        })
      }
    },
    deleteHook() {
      axios.delete(`${this.$store.state.endpoint.api}/api/v1/externalhooks/${this.selectedHookId}`, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.$store.dispatch("requestExternalHook")
          this.$vaToast.init({ title: response.data.state, message: this.$t('pages.configuration.externalHook.removed'), color: 'success' })
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: this.$t('pages.configuration.externalHook.removeFailed'),
            message: error?.response?.data?.detail ?? error,
            color: 'danger'
          })
        })
    }
  },
  mounted() {
    this.$store.dispatch("requestExternalHook");
  },
})
</script>
<style scoped>
.text-right {
  text-align: right;
  width: 100%;
}
</style>
