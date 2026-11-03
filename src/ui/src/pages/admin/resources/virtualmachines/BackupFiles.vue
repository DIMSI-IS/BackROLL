<template>
  <va-card>
    <va-card-title>
      <div class="header">
        <h1>{{ $t('pages.resources.files.title') }}</h1>
        <va-button icon="clear" color="info" @click="close">{{ $t('pages.resources.files.close') }}</va-button>
      </div>
    </va-card-title>
    <va-card-content>
      <p class="mb-3 info">
        {{ $t('pages.resources.files.backup') }} <b>{{ backup }}</b>. {{ $t('pages.resources.files.tempCopy') }}
      </p>

      <div v-if="state === 'extracting' || state === 'starting'" class="flex-center ma-3 column">
        <spring-spinner :animation-duration="2000" :size="40" color="#2c82e0" />
        <p class="mt-3">
          {{ state === 'extracting'
            ? $t('pages.resources.files.extracting')
            : $t('pages.resources.files.starting') }}
        </p>
      </div>

      <va-alert v-else-if="state === 'error'" color="danger" border="top">
        {{ error }}
      </va-alert>

      <div v-else-if="state === 'choose_filesystem'">
        <p class="mb-3">{{ $t('pages.resources.files.noOs') }}</p>
        <div class="choice">
          <va-select v-model="selectedFilesystem" :label="$t('pages.resources.files.filesystem')" :options="filesystemOptions" value-by="value"
            text-by="text" />
          <va-button :disabled="!selectedFilesystem" @click="chooseFilesystem">{{ $t('pages.resources.files.open') }}</va-button>
        </div>
      </div>

      <div v-else-if="state === 'ready'">
        <div class="breadcrumb mb-3">
          <va-button size="small" flat icon="home" @click="open('/')" />
          <template v-for="(part, index) in parts" :key="index">
            <span>/</span>
            <va-button size="small" flat @click="open(pathOf(index))">{{ part }}</va-button>
          </template>
          <va-button class="ml-3" size="small" flat icon="download" @click="download(path)"
            :disabled="path === '/'">
            {{ $t('pages.resources.files.downloadFolder') }}
          </va-button>
        </div>

        <va-data-table :no-data-html="$t('pages.common.noItems')" :items="entries" :columns="columns" :loading="listing">
          <template #cell(name)="{ rowIndex }">
            <span class="entry" @click="enter(entries[rowIndex])">
              <va-icon :name="icons[entries[rowIndex].type] || 'insert_drive_file'" size="small" />
              {{ entries[rowIndex].name }}
            </span>
          </template>
          <template #cell(size)="{ rowIndex }">
            {{ entries[rowIndex].type === 'file' ? humanSize(entries[rowIndex].size) : '' }}
          </template>
          <template #cell(modified)="{ rowIndex }">
            {{ new Date(entries[rowIndex].modified * 1000).toLocaleString() }}
          </template>
          <template #cell(actions)="{ rowIndex }">
            <va-button size="small" icon="download" :disabled="!['file', 'directory'].includes(entries[rowIndex].type)"
              @click="download(childPath(entries[rowIndex]))">
              {{ entries[rowIndex].type === 'directory' ? $t('pages.resources.files.folderTar') : $t('pages.resources.files.download') }}
            </va-button>
          </template>
        </va-data-table>
      </div>
    </va-card-content>
  </va-card>
</template>

<script>
import { defineComponent } from "vue";
import * as spinners from "epic-spinners";
import axios from "axios";

export default defineComponent({
  name: "BackupFiles",
  components: { ...spinners },
  data() {
    return {
      state: "extracting",
      error: null,
      sessionId: null,
      filesystems: [],
      selectedFilesystem: null,
      path: "/",
      entries: [],
      listing: false,
      stopped: false,
      icons: { directory: "folder", file: "insert_drive_file", link: "link" },
    };
  },
  computed: {
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.files.colName") },
        { key: "size", label: this.$t("pages.resources.files.colSize") },
        { key: "modified", label: this.$t("pages.resources.files.colModified") },
        { key: "actions", label: this.$t("pages.resources.files.colActions") },
      ];
    },
    columns() {
      return [
        { key: "name", label: this.$t("pages.resources.files.colName") },
        { key: "size", label: this.$t("pages.resources.files.colSize") },
        { key: "modified", label: this.$t("pages.resources.files.colModified") },
        { key: "actions", label: this.$t("pages.resources.files.colActions") },
      ];
    },
    vmId() {
      return this.$route.params.id;
    },
    backup() {
      return this.$route.params.backup;
    },
    api() {
      return `${this.$store.state.endpoint.api}/api/v1`;
    },
    headers() {
      return { Authorization: `Bearer ${this.$store.state.token}` };
    },
    parts() {
      return this.path.split("/").filter(Boolean);
    },
    filesystemOptions() {
      return this.filesystems.map((fs) => ({ value: fs.device, text: `${fs.device} (${fs.type})` }));
    },
  },
  methods: {
    wait(milliseconds) {
      return new Promise((resolve) => setTimeout(resolve, milliseconds));
    },
    fail(message, error) {
      console.error(error);
      this.state = "error";
      this.error = error?.response?.data?.detail ?? message;
    },
    humanSize(bytes) {
      const units = ["B", "KiB", "MiB", "GiB", "TiB"];
      let unit = 0;
      while (bytes >= 1024 && unit < units.length - 1) {
        bytes /= 1024;
        unit++;
      }
      return `${unit === 0 ? bytes : bytes.toFixed(1)} ${units[unit]}`;
    },
    pathOf(index) {
      return "/" + this.parts.slice(0, index + 1).join("/");
    },
    childPath(entry) {
      return (this.path === "/" ? "" : this.path) + "/" + entry.name;
    },
    async start() {
      try {
        const { data } = await axios.post(
          `${this.api}/virtualmachines/${this.vmId}/backups/${this.backup}/files`,
          {},
          { headers: this.headers }
        );
        this.sessionId = data.session_id;
        this.$router.replace({ query: { session: data.session_id } });
        await this.waitForTask(data.Location);
        await this.waitForSession();
      } catch (error) {
        this.fail(this.$t('pages.resources.files.openBackupFailed'), error);
      }
    },
    async waitForTask(location) {
      while (!this.stopped) {
        const { data } = await axios.get(`${this.$store.state.endpoint.api}${location}`, { headers: this.headers });
        if (data.state === "SUCCESS") return;
        if (data.state === "FAILURE") {
          throw new Error(data.info || this.$t('pages.resources.files.extractionFailed'));
        }
        await this.wait(2000);
      }
    },
    async waitForSession() {
      while (!this.stopped) {
        const { data } = await axios.get(`${this.api}/file-browser/${this.sessionId}`, { headers: this.headers });
        this.filesystems = data.filesystems;
        if (data.state === "ready") {
          this.state = "ready";
          return this.open("/");
        }
        if (data.state === "choose_filesystem") {
          this.state = "choose_filesystem";
          this.selectedFilesystem = data.filesystems[0]?.device ?? null;
          return;
        }
        if (data.state === "error") {
          this.fail(data.error || this.$t('pages.resources.files.readDiskFailed'), null);
          return;
        }
        this.state = data.state === "extracting" ? "extracting" : "starting";
        await this.wait(2000);
      }
    },
    async chooseFilesystem() {
      try {
        await axios.post(`${this.api}/file-browser/${this.sessionId}/filesystem`,
          { device: this.selectedFilesystem }, { headers: this.headers });
        this.state = "ready";
        await this.open("/");
      } catch (error) {
        this.fail(this.$t('pages.resources.files.openFsFailed'), error);
      }
    },
    async open(path) {
      this.listing = true;
      try {
        const { data } = await axios.get(`${this.api}/file-browser/${this.sessionId}/files`, {
          params: { path },
          headers: this.headers,
        });
        this.path = path;
        this.entries = data.entries;
      } catch (error) {
        this.$vaToast.init({
          title: this.$t('pages.resources.files.openFolderFailed'),
          message: error?.response?.data?.detail ?? error,
          color: "danger",
        });
      } finally {
        this.listing = false;
      }
    },
    enter(entry) {
      if (entry.type === "directory") this.open(this.childPath(entry));
    },
    async download(path) {
      try {
        const { data } = await axios.get(`${this.api}/file-browser/${this.sessionId}/download`, {
          params: { path },
          headers: this.headers,
          responseType: "blob",
        });
        const name = path.split("/").filter(Boolean).pop() || "disk";
        const entry = this.entries.find((e) => this.childPath(e) === path);
        const isDirectory = path === this.path || entry?.type === "directory";
        const link = document.createElement("a");
        link.href = URL.createObjectURL(data);
        link.download = isDirectory ? `${name}.tar` : name;
        link.click();
        URL.revokeObjectURL(link.href);
      } catch (error) {
        this.$vaToast.init({ title: this.$t('pages.resources.files.downloadFailedTitle'), message: this.$t('pages.resources.files.downloadFailed'), color: "danger" });
      }
    },
    async release() {
      this.stopped = true;
      if (this.sessionId) {
        try {
          await axios.delete(`${this.api}/file-browser/${this.sessionId}`, { headers: this.headers });
        } catch (error) {
          // The session may already be expired.
        }
        this.sessionId = null;
      }
    },
    async close() {
      await this.release();
      this.$router.push(`/resources/virtualmachines/${this.vmId}`);
    },
  },
  mounted() {
    const resumed = this.$route.query.session;
    if (resumed) {
      this.sessionId = resumed;
      this.waitForSession().catch((error) => this.fail(this.$t('pages.resources.files.sessionExpired'), error));
    } else {
      this.start();
    }
  },
  beforeUnmount() {
    this.release();
  },
});
</script>

<style scoped>
.header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
}

.column {
  flex-direction: column;
}

.choice {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
}

.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.entry {
  cursor: pointer;
}

.info {
  color: var(--va-gray);
}
</style>
