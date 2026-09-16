<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { MatrixFilter } from "../filter";
import { STATUS_LABEL } from "../labels";
import type { CellStatus, Certification, Position } from "../types";

const props = defineProps<{
  filter: MatrixFilter;
  positions: Position[];
  certifications: Certification[];
}>();
const emit = defineEmits<{ update: [patch: Partial<MatrixFilter>]; reset: [] }>();

const statuses: CellStatus[] = ["missing", "expired", "expiring", "valid"];
const search = ref(props.filter.q);
let timer: ReturnType<typeof setTimeout> | undefined;
watch(search, (v) => {
  clearTimeout(timer);
  timer = setTimeout(() => emit("update", { q: v }), 250);
});
watch(
  () => props.filter.q,
  (v) => {
    if (v !== search.value.trim()) search.value = v;
  },
);

function toggleStatus(s: CellStatus): void {
  const set = new Set(props.filter.status);
  if (set.has(s)) set.delete(s);
  else set.add(s);
  emit("update", { status: statuses.filter((x) => set.has(x)) });
}

const expanded = ref(false);
const activeCount = computed(
  () =>
    (props.filter.q.trim() ? 1 : 0) +
    (props.filter.position_id !== null ? 1 : 0) +
    (props.filter.certification_id !== null ? 1 : 0) +
    props.filter.status.length +
    (props.filter.include_inactive ? 1 : 0) +
    (props.filter.only_open ? 1 : 0),
);

function toNum(v: string): number | null {
  return v === "" ? null : Number(v);
}
</script>

<template>
  <div class="filters panel">
    <button
      type="button"
      class="secondary toggle"
      :aria-expanded="expanded"
      aria-controls="filter-body"
      @click="expanded = !expanded"
    >
      Filter<template v-if="activeCount"> ({{ activeCount }} aktiv)</template>
      <span aria-hidden="true">{{ expanded ? "▴" : "▾" }}</span>
    </button>
    <div id="filter-body" class="body" :class="{ open: expanded }">
      <div class="form-grid">
        <label>
          Suche
          <input v-model="search" type="search" placeholder="Name oder Nr" autocomplete="off" />
        </label>
        <label>
          Funktion
          <select
            :value="filter.position_id ?? ''"
            @change="emit('update', { position_id: toNum(($event.target as HTMLSelectElement).value) })"
          >
            <option value="">Alle Funktionen</option>
            <option v-for="p in positions" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </label>
        <label>
          Nachweis
          <select
            :value="filter.certification_id ?? ''"
            @change="emit('update', { certification_id: toNum(($event.target as HTMLSelectElement).value) })"
          >
            <option value="">Alle Nachweise</option>
            <option v-for="c in certifications" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
      </div>

      <div class="chips" role="group" aria-label="Status">
        <button
          v-for="s in statuses"
          :key="s"
          type="button"
          class="chip"
          :class="s"
          :aria-pressed="filter.status.includes(s)"
          @click="toggleStatus(s)"
        >
          {{ STATUS_LABEL[s] }}
        </button>
      </div>

      <div class="row toggles">
        <label class="check">
          <input
            type="checkbox"
            :checked="filter.only_open"
            @change="emit('update', { only_open: ($event.target as HTMLInputElement).checked })"
          />
          Nur Kameraden mit offenen Nachweisen
        </label>
        <label class="check">
          <input
            type="checkbox"
            :checked="filter.include_inactive"
            @change="emit('update', { include_inactive: ($event.target as HTMLInputElement).checked })"
          />
          Inaktive einblenden
        </label>
        <button type="button" class="link" @click="emit('reset')">Filter zurücksetzen</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.body {
  display: grid;
  gap: 0.9rem;
}
.toggle {
  display: none;
  width: 100%;
  justify-content: space-between;
}
@media (max-width: 760px) {
  .filters {
    padding: 0.5rem;
  }
  .toggle {
    display: flex;
    border: none;
  }
  .body:not(.open) {
    display: none;
  }
  .body.open {
    padding: 0.5rem;
  }
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.chip {
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  min-height: 2.25rem;
  padding: 0.25rem 0.9rem 0.25rem 0.6rem;
  font-weight: 500;
}
.chip::before {
  content: "";
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 2px;
  display: inline-block;
}
.chip.valid::before {
  background: var(--ok);
}
.chip.expiring::before {
  background: var(--warn);
}
.chip.expired::before {
  background: var(--bad);
}
.chip.missing::before {
  background: var(--bad-soft);
  box-shadow: inset 0 0 0 2px var(--bad);
}
.chip[aria-pressed="true"] {
  border-color: var(--ink);
  box-shadow: inset 0 0 0 1px var(--ink);
  font-weight: 600;
}
.toggles {
  gap: 0.5rem 1.5rem;
}
</style>
