<template>
  <div class="documentation">
    <section class="hero">
      <div class="hero__text">
        <h1>{{ $t('pages.documentation.heroTitle') }}</h1>
        <p>{{ $t('pages.documentation.heroSubtitle') }}</p>
      </div>
      <va-input v-model="search" class="hero__search" :placeholder="$t('pages.documentation.search')" clearable
        bordered>
        <template #prependInner>
          <va-icon name="search" />
        </template>
      </va-input>
    </section>

    <div class="quick" v-if="!search">
      <a v-for="card in quickCards" :key="card.id" class="quick__card" :href="`#${card.id}`"
        @click.prevent="goTo(card.id)">
        <va-icon :name="card.icon" :color="card.color" size="large" />
        <div>
          <b>{{ card.title }}</b>
          <span>{{ card.summary }}</span>
        </div>
      </a>
    </div>

    <div class="layout">
      <nav class="toc">
        <p class="toc__title">{{ $t('pages.documentation.onThisPage') }}</p>
        <ul class="toc__list">
          <li v-for="section in visibleSections" :key="section.id">
            <a :href="`#${section.id}`" :class="{ active: section.id === current }"
              @click.prevent="goTo(section.id)">
              <va-icon :name="section.icon" size="small" />
              <span>{{ section.title }}</span>
            </a>
          </li>
        </ul>
        <p v-if="visibleSections.length === 0" class="toc__empty">{{ $t('pages.documentation.nothingFound') }}</p>
      </nav>

      <div class="content">
        <article v-for="(section, number) in visibleSections" :key="section.id" :id="section.id"
          class="section" :data-section="section.id">
          <header class="section__header">
            <span class="section__icon"><va-icon :name="section.icon" /></span>
            <div>
              <h2>{{ section.title }}</h2>
              <p v-if="section.summary">{{ section.summary }}</p>
            </div>
          </header>

          <div class="figures" v-if="section.figures.length">
            <figure v-for="figure in section.figures" :key="figure.name" v-show="!missing[figure.src]">
              <div class="window" @click="zoom = figure">
                <div class="window__bar"><i /><i /><i /></div>
                <img :src="figure.src" :alt="figure.caption" loading="lazy"
                  @error="missing[figure.src] = true" />
              </div>
              <figcaption>{{ figure.caption }}</figcaption>
            </figure>
          </div>

          <template v-for="(block, index) in section.blocks" :key="index">
            <h3 v-if="block.h">{{ block.h }}</h3>
            <p v-else-if="block.p" v-html="block.p" />
            <ul v-else-if="block.ul" class="bullets">
              <li v-for="(item, i) in block.ul" :key="i" v-html="item" />
            </ul>
            <ol v-else-if="block.ol" class="steps">
              <li v-for="(item, i) in block.ol" :key="i"><span v-html="item" /></li>
            </ol>
            <div v-else-if="block.code" class="code">
              <button type="button" class="code__copy" @click="copy(block.code, `${section.id}-${index}`)">
                <va-icon :name="copied === `${section.id}-${index}` ? 'check' : 'content_copy'" size="small" />
                {{ copied === `${section.id}-${index}` ? $t('pages.documentation.copied') : $t('pages.documentation.copy') }}
              </button>
              <pre>{{ block.code }}</pre>
            </div>
            <div v-else-if="block.note" class="callout" :class="`callout--${block.kind || 'info'}`">
              <va-icon :name="icons[block.kind || 'info']" />
              <span v-html="block.note" />
            </div>
            <div v-else-if="block.table" class="table-wrapper">
              <table>
                <thead>
                  <tr><th v-for="(heading, i) in block.table.head" :key="i">{{ heading }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, r) in block.table.rows" :key="r">
                    <td v-for="(cell, c) in row" :key="c" v-html="cell" />
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <footer class="section__footer" v-if="number < visibleSections.length - 1">
            <a :href="`#${visibleSections[number + 1].id}`" @click.prevent="goTo(visibleSections[number + 1].id)">
              {{ $t('pages.documentation.next') }}: {{ visibleSections[number + 1].title }}
              <va-icon name="arrow_forward" size="small" />
            </a>
          </footer>
        </article>
      </div>
    </div>

    <va-modal :model-value="!!zoom" @update:model-value="zoom = null" hide-default-actions size="large"
      close-button>
      <img v-if="zoom" :src="zoom.src" :alt="zoom.caption" class="zoomed" />
      <p v-if="zoom" class="zoomed__caption">{{ zoom.caption }}</p>
    </va-modal>
  </div>
</template>

<script>
import { defineComponent } from "vue";
import contentEn from "./content";
import contentFr from "./content.fr";
import meta, { quickStart } from "./meta";

// Text of a section, without the tags, to search in.
function plain(section) {
  return JSON.stringify(section).replace(/<[^>]+>/g, " ").toLowerCase();
}

export default defineComponent({
  name: "Documentation",
  data() {
    return {
      search: "",
      current: contentEn[0].id,
      copied: null,
      zoom: null,
      // Screenshots that do not exist are hidden.
      missing: {},
      icons: { info: "info", warning: "warning", danger: "error" },
      observer: null,
    };
  },
  computed: {
    language() {
      return this.$i18n.locale === "fr" ? "fr" : "en";
    },
    sections() {
      const content = this.language === "fr" ? contentFr : contentEn;
      return content.map((section) => {
        const extra = meta[section.id] || { icon: "article", summary: {}, figures: [] };
        return {
          ...section,
          icon: extra.icon,
          summary: extra.summary[this.language],
          figures: extra.figures.map((figure) => ({
            name: figure.name,
            caption: figure.caption[this.language],
            src: `${process.env.BASE_URL || "/"}docs/${this.language}/${figure.name}.png`,
          })),
          text: plain(section),
        };
      });
    },
    visibleSections() {
      const words = (this.search || "").toLowerCase().split(/\s+/).filter(Boolean);
      return this.sections.filter((section) => words.every((word) => section.text.includes(word)));
    },
    quickCards() {
      return quickStart.map((card) => {
        const section = this.sections.find((item) => item.id === card.id);
        return { ...card, title: section.title, summary: section.summary };
      });
    },
  },
  watch: {
    visibleSections() {
      this.$nextTick(this.observe);
    },
  },
  methods: {
    goTo(id) {
      this.current = id;
      const element = document.getElementById(id);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    },
    async copy(text, key) {
      try {
        await navigator.clipboard.writeText(text);
        this.copied = key;
        setTimeout(() => {
          if (this.copied === key) this.copied = null;
        }, 1500);
      } catch {
        // The text can still be selected by hand.
      }
    },
    // The section that is being read is highlighted in the summary.
    observe() {
      if (this.observer) this.observer.disconnect();
      if (typeof IntersectionObserver === "undefined") return;
      this.observer = new IntersectionObserver((entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (visible.length) {
          this.current = visible[0].target.dataset.section;
        }
      }, { rootMargin: "-10% 0px -75% 0px" });
      document.querySelectorAll(".documentation .section").forEach((element) => this.observer.observe(element));
    },
  },
  mounted() {
    this.observe();
  },
  beforeUnmount() {
    if (this.observer) this.observer.disconnect();
  },
});
</script>

<style scoped>
.documentation {
  --doc-radius: 12px;
  --doc-border: color-mix(in srgb, var(--va-primary) 14%, transparent);
}

/* Welcome area */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1.5rem;
  padding: 2rem 2.25rem;
  margin-bottom: 1rem;
  border-radius: var(--doc-radius);
  color: #fff;
  background: linear-gradient(120deg, var(--va-primary), color-mix(in srgb, var(--va-primary) 55%, #1b2a4a));
}

.hero h1 {
  margin: 0 0 0.4rem;
  font-size: 2rem;
  line-height: 1.15;
}

.hero p {
  margin: 0;
  max-width: 34rem;
  opacity: 0.9;
}

.hero__search {
  flex: 0 1 24rem;
  min-width: 15rem;
  --va-input-wrapper-background: #fff;
}

.quick {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.quick__card {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1rem 1.1rem;
  border-radius: var(--doc-radius);
  border: 1px solid var(--doc-border);
  background: var(--va-white);
  color: inherit;
  text-decoration: none;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.quick__card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
}

.quick__card b {
  display: block;
}

.quick__card span {
  font-size: 0.85rem;
  opacity: 0.75;
}

/* Summary and content */
.layout {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
}

.toc {
  position: sticky;
  top: 1rem;
  flex: 0 0 16rem;
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
  padding: 1rem;
  border-radius: var(--doc-radius);
  border: 1px solid var(--doc-border);
  background: var(--va-white);
}

.toc__title {
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.6;
}

.toc__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.toc__list a {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  color: inherit;
  text-decoration: none;
  font-size: 0.92rem;
  border-left: 3px solid transparent;
}

.toc__list a:hover {
  background: color-mix(in srgb, var(--va-primary) 8%, transparent);
}

.toc__list a.active {
  color: var(--va-primary);
  font-weight: 600;
  border-left-color: var(--va-primary);
  background: color-mix(in srgb, var(--va-primary) 10%, transparent);
}

.toc__empty {
  margin: 0;
}

.content {
  flex: 1;
  min-width: 0;
}

.section {
  margin-bottom: 1.25rem;
  padding: 1.75rem 2rem;
  border-radius: var(--doc-radius);
  border: 1px solid var(--doc-border);
  background: var(--va-white);
  scroll-margin-top: 1rem;
}

.section__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--doc-border);
}

.section__header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.section__header p {
  margin: 0.15rem 0 0;
  opacity: 0.7;
}

.section__icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, var(--va-primary), color-mix(in srgb, var(--va-primary) 60%, #1b2a4a));
}

.section h3 {
  margin: 1.6rem 0 0.6rem;
  font-size: 1.1rem;
}

.section p {
  margin: 0.6rem 0;
  line-height: 1.6;
}

/* Lists */
.bullets {
  margin: 0.5rem 0 1rem;
  padding-left: 1.4rem;
}

.bullets li {
  margin-bottom: 0.4rem;
  line-height: 1.55;
}

.steps {
  list-style: none;
  counter-reset: step;
  margin: 0.75rem 0 1.25rem;
  padding: 0;
}

.steps li {
  counter-increment: step;
  display: flex;
  gap: 0.9rem;
  align-items: flex-start;
  margin-bottom: 0.6rem;
  padding: 0.7rem 0.9rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--va-primary) 5%, transparent);
  line-height: 1.55;
}

.steps li::before {
  content: counter(step);
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  background: var(--va-primary);
}

/* Callouts */
.callout {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin: 1rem 0;
  padding: 0.9rem 1.1rem;
  border-radius: 10px;
  border-left: 4px solid var(--callout, var(--va-info));
  background: color-mix(in srgb, var(--callout, var(--va-info)) 10%, transparent);
  line-height: 1.55;
}

.callout .va-icon {
  color: var(--callout, var(--va-info));
}

.callout--warning {
  --callout: var(--va-warning);
}

.callout--danger {
  --callout: var(--va-danger);
}

/* Code */
.code {
  position: relative;
  margin: 0.8rem 0;
}

.code pre {
  margin: 0;
  padding: 1rem 1.2rem;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 0.85rem;
  color: #e6edf7;
  background: #17202e;
}

.code__copy {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 6px;
  color: #e6edf7;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.75rem;
  cursor: pointer;
}

.code__copy:hover {
  background: rgba(255, 255, 255, 0.18);
}

:deep(code) {
  padding: 0.1rem 0.4rem;
  border-radius: 5px;
  font-size: 0.86em;
  background: color-mix(in srgb, var(--va-primary) 10%, transparent);
}

/* Tables */
.table-wrapper {
  overflow-x: auto;
  margin: 0.9rem 0;
  border-radius: 10px;
  border: 1px solid var(--doc-border);
}

.table-wrapper table {
  width: 100%;
  border-collapse: collapse;
}

.table-wrapper th {
  text-align: left;
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: color-mix(in srgb, var(--va-primary) 10%, transparent);
}

.table-wrapper th,
.table-wrapper td {
  padding: 0.65rem 0.9rem;
  vertical-align: top;
  line-height: 1.5;
}

.table-wrapper tbody tr:nth-child(even) {
  background: color-mix(in srgb, var(--va-primary) 4%, transparent);
}

.table-wrapper td:first-child {
  font-weight: 600;
  white-space: nowrap;
}

/* Screenshots */
.figures {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: 1.1rem;
  margin: 0 0 1.25rem;
}

.figures figure {
  margin: 0;
}

.figures figcaption {
  margin-top: 0.4rem;
  font-size: 0.82rem;
  text-align: center;
  opacity: 0.7;
}

.window {
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid var(--doc-border);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
  cursor: zoom-in;
  transition: transform 0.15s ease;
}

.window:hover {
  transform: scale(1.01);
}

.window__bar {
  display: flex;
  gap: 0.35rem;
  padding: 0.45rem 0.7rem;
  background: color-mix(in srgb, var(--va-primary) 12%, #dfe5ee);
}

.window__bar i {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.25);
}

.window img {
  display: block;
  width: 100%;
  height: auto;
}

.zoomed {
  display: block;
  max-width: 100%;
  margin: 0 auto;
}

.zoomed__caption {
  margin: 0.6rem 0 0;
  text-align: center;
  opacity: 0.75;
}

.section__footer {
  margin-top: 1.5rem;
  padding-top: 1rem;
  text-align: right;
  border-top: 1px solid var(--doc-border);
}

.section__footer a {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--va-primary);
  text-decoration: none;
  font-weight: 600;
}

@media (max-width: 960px) {
  .layout {
    flex-direction: column;
  }

  .toc {
    position: static;
    flex-basis: auto;
    width: 100%;
    max-height: none;
  }

  .section {
    padding: 1.25rem 1.1rem;
  }

  .hero {
    padding: 1.4rem 1.2rem;
  }
}
</style>
