<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { api, errorText } from "../../api";
import { EMPTY_FILTER, filterToSearch, parseFilter } from "../../filter";
import { KIND_LABEL } from "../../labels";
import type { Overview, Position } from "../../types";
import AppBar from "../components/AppBar.vue";
import ExportSheet from "../components/ExportSheet.vue";
import MIcon from "../components/MIcon.vue";
import PullRefresh from "../components/PullRefresh.vue";
import { certStats, type CertStat } from "../readiness";

const route = useRoute();
const router = useRouter();
const data = ref<Overview | null>(null);
const positions = ref<Position[]>([]);
const error = ref("");
const q = ref("");
const exporter = ref<InstanceType<typeof ExportSheet> | null>(null);

const positionId = computed(() => parseFilter(route.query).position_id);
const position = computed(() => positions.value.find((p) => p.id === positionId.value));
const search = computed(() => filterToSearch({ ...EMPTY_FILTER, position_id: positionId.value }));

async function load(): Promise<void> {
  error.value = "";
  try {
    data.value = await api<Overview>(`/api/overview${search.value ? `?${search.value}` : ""}`);
  } catch (e) {
    error.value = errorText(e);
  }
}
onMounted(async () => {
  positions.value = await api<Position[]>("/api/positions").catch(() => []);
});
watch(search, load, { immediate: true });

function selectPosition(id: number | null): void {
  void router.replace({ query: id === null ? {} : { position_id: String(id) } });
}

const stats = computed(() => {
  const needle = q.value.trim().toLowerCase();
  return certStats(data.value ?? { certifications: [], rows: [] }).filter(
    (s) =>
      !needle ||
      s.certification.name.toLowerCase().includes(needle) ||
      s.certification.short_name.toLowerCase().includes(needle),
  );
});
const needed = computed(() => stats.value.filter((s) => s.required > 0));
const unused = computed(() => stats.value.filter((s) => s.required === 0));

function summary(s: CertStat): string {
  const open = s.missing + s.expired;
  if (open && s.expiring) return `${open} offen, ${s.expiring} bald fällig`;
  if (open) return `${open} von ${s.required} offen`;
  if (s.expiring) return `${s.expiring} bald fällig`;
  return `Alle ${s.required} gültig`;
}

function link(id: number) {
  return { path: `/uebersicht/${id}`, query: route.query };
}
</script>

<template>
  <PullRefresh :refresh="load" />
  <AppBar title="Nachweise" subtitle="Wer hat welchen Nachweis, je Lehrgang und Übung.">
    <template #actions>
      <button type="button" class="icon-btn" aria-label="Übersicht teilen" @click="exporter?.open()">
        <MIcon name="share" />
      </button>
    </template>
    <label class="search-field">
      <MIcon name="search" :size="18" />
      <input v-model="q" type="search" placeholder="Nachweis suchen" aria-label="Nachweis suchen" />
    </label>
  </AppBar>

  <div v-if="positions.length" class="chip-row" role="group" aria-label="Nach Funktion filtern">
    <button type="button" class="chip" :aria-pressed="positionId === null" @click="selectPosition(null)">Alle</button>
    <button
      v-for="p in positions"
      :key="p.id"
      type="button"
      class="chip"
      :aria-pressed="positionId === p.id"
      @click="selectPosition(p.id)"
    >
      {{ p.name }}
    </button>
  </div>

  <div class="section">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="!data">
      <div v-for="i in 5" :key="i" class="skeleton"></div>
    </template>
    <template v-else>
      <ul v-if="needed.length" class="group">
        <li v-for="s in needed" :key="s.certification.id">
          <RouterLink :to="link(s.certification.id)" class="cell stat">
            <span class="cell-main">
              <strong>{{ s.certification.name }}</strong>
              <span class="bar" aria-hidden="true">
                <span class="valid" :style="{ flexGrow: s.valid }"></span>
                <span class="expiring" :style="{ flexGrow: s.expiring }"></span>
                <span class="expired" :style="{ flexGrow: s.expired }"></span>
                <span class="missing" :style="{ flexGrow: s.missing }"></span>
              </span>
              <span class="cell-sub" :class="{ alert: s.missing + s.expired > 0 }">{{ summary(s) }}</span>
            </span>
            <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
          </RouterLink>
        </li>
      </ul>
      <p v-else-if="stats.length === 0" class="empty">
        <strong>Kein Nachweis gefunden</strong>
        {{ q ? `Nichts passt zu „${q}“.` : "Im Katalog sind noch keine Nachweise angelegt." }}
      </p>

      <template v-if="unused.length">
        <p class="group-label">
          {{ position ? `Für ${position.name} nicht gefordert` : "Für niemanden gefordert" }}
        </p>
        <ul class="group">
          <li v-for="s in unused" :key="s.certification.id">
            <RouterLink :to="link(s.certification.id)" class="cell">
              <span class="cell-main">
                <strong>{{ s.certification.name }}</strong>
                <span class="cell-sub">{{ KIND_LABEL[s.certification.kind] }}</span>
              </span>
              <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
            </RouterLink>
          </li>
        </ul>
      </template>
    </template>
  </div>

  <ExportSheet
    ref="exporter"
    :query="search"
    :description="position ? `Übersicht, Funktion ${position.name}` : 'Komplette Übersicht'"
  />
</template>

<style scoped>
.search-field {
  margin-top: 0.75rem;
}
.chip-row {
  margin-top: 0.25rem;
}
.section {
  margin-top: 1rem;
}
.stat .cell-main {
  gap: 0.3rem;
}
.bar {
  display: flex;
  gap: 2px;
  height: 0.45rem;
  border-radius: 999px;
  overflow: hidden;
  background: var(--line);
}
.bar span {
  flex-basis: 0;
}
.bar .valid {
  background: var(--ok);
}
.bar .expiring {
  background: var(--warn);
}
.bar .expired {
  background: var(--bad);
}
.bar .missing {
  background: repeating-linear-gradient(-45deg, var(--bad) 0 3px, var(--bad-soft) 3px 6px);
}
.alert {
  color: var(--bad-ink);
}
</style>
