<template>
  <va-select label="Virtual Machines" v-model="virtualMachineSelection" :options="selectData"
    :loading="this.loadingVMs">
    <template #prependInner>
      <va-icon name="today" size="small" color="primary" />
    </template>
  </va-select>
</template>
<script>
import { defineComponent } from 'vue'
import axios from 'axios'

export default defineComponent({
  name: 'VirtualMachineList',
  props: [],
  data() {
    return {
      loadingVMs: false,
      selectedVM: null,
      vmInfo: []
    }
  },
  watch: {
    virtualMachine: function () {
      this.requestVirtualMachineList()
    }
  },
  mounted() {
    this.requestVirtualMachineList()
  },
  computed: {
    selectData() {
      if (this.vmInfo) {
        const result = this.vmInfo.map(x => ({
          text: x.name,
          value: x.path
        }))
        return result.sort().reverse()
      }
      return [];
    },
  },
  methods: {
    getVirtualMachineList(paths) {
      if (paths.length > 0) {
        console.log("Success")
        this.vmInfo = paths;
        this.loadingVMs = false;
      } else {
        console.log("No vm folders found");
      }
    },
    requestVirtualMachineList() {
      const urlToCall = `${this.$store.state.endpoint.api}/api/v1/virtualmachinespaths`;
      axios.get(urlToCall, { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.$store.state.token}` } })
        .then(response => {
          this.loadingVMs = true
          this.getVirtualMachineList(response.data.paths)
        })
        .catch(error => {
          console.error(error)
          this.$vaToast.init({
            title: "Unexpected error",
            message: error,
            color: "danger"
          })
        })
    },
  }
})
</script>