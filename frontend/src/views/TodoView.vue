<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { api, errorText } from "../api";
import StatusCounts from "../components/StatusCounts.vue";
import StatusPeg from "../components/StatusPeg.vue";
import { EMPTY_FILTER, filterToSearch, parseFilter } from "../filter";
import { cellHint, certShortName, formatDate } from "../labels";
import { buildOpenRows } from "../todo";
import type { Cell, Certification, Overview, Position } from "../types";

const route = useRoute();
const router = useRouter();
const data = ref<Overview | null>(null);
const positions = ref<Position[]>([]);
const error = ref("");

const positionId = computed(() => parseFilter(route.query).position_id);
const position = computed(() => positions.value.find((p) => p.id === positionId.value));

function selectPosition(id: number | null): void {
  void router.replace({ query: id === null ? {} : { position_id: String(id) } });
}

/** Loads the overview for the selected position. Only the position filter applies on this page. */
async function load(): Promise<void> {
  error.value = "";
  try {
    const search = filterToSearch({ ...EMPTY_FILTER, position_id: positionId.value });
    data.value = await api<Overview>(`/api/overview${search ? `?${search}` : ""}`);
  } catch (e) {
    error.value = errorText(e);
  }
}

const chips = ref<HTMLElement | null>(null);

onMounted(async () => {
  try {
    positions.value = await api<Position[]>("/api/positions");
    await nextTick();
    chips.value?.querySelector('[aria-pressed="true"]')?.scrollIntoView({ block: "nearest", inline: "center" });
  } catch (e) {
    error.value = errorText(e);
  }
});
watch(positionId, load, { immediate: true });

const certById = computed(
  () => new Map<number, Certification>((data.value?.certifications ?? []).map((c) => [c.id, c])),
);

const openRows = computed(() => buildOpenRows(data.value?.rows ?? []));
const doneCount = computed(() => (data.value?.rows.length ?? 0) - openRows.value.length);
const scope = computed(() => (position.value ? ` mit Funktion ${position.value.name}` : ""));

function certName(c: Cell): string {
  return certById.value.get(c.certification_id)?.name ?? "";
}
</script>

<template>
  <div class="page">
    <h1>Offen</h1>

    <div v-if="positions.length" ref="chips" class="positions" role="group" aria-label="Nach Funktion filtern">
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

    <p v-if="data" class="lede">
      Stand {{ formatDate(data.today) }}.
      <template v-if="data.rows.length === 0 && position"
        >Kein aktiver Kamerad hat die Funktion {{ position.name }}.</template
      >
      <template v-else-if="openRows.length === 0">
        Alle {{ data.rows.length }} aktiven Kameraden{{ scope }} sind vollständig.
      </template>
      <template v-else>
        {{ openRows.length }} von {{ data.rows.length }} Kameraden{{ scope }} haben offene Nachweise,
        {{ doneCount }} sind vollständig.
      </template>
    </p>
    <p v-if="error" class="error">{{ error }}</p>

    <StatusCounts v-if="data" :counts="data.counts" class="counts" />

    <ul v-if="openRows.length" class="list todo">
      <li v-for="row in openRows" :key="row.member.id" :class="row.worst_status">
        <RouterLink :to="`/kameraden/${row.member.id}`" class="list-item">
          <div class="who">
            <strong>{{ row.member.last_name }}, {{ row.member.first_name }}</strong>
            <span class="muted small">Nr {{ row.member.number }}</span>
          </div>
          <ul class="items">
            <li v-for="c in row.open" :key="c.certification_id">
              <StatusPeg :status="c.status" :label="certShortName(certById, c.certification_id)" :title="certName(c)" />
              <span class="small">
                <span class="name">{{ certName(c) }}</span>
                <span class="hint">{{ cellHint(c.status, c.expires_on, data!.today) }}</span>
              </span>
            </li>
          </ul>
        </RouterLink>
      </li>
    </ul>

    <div v-else-if="data && data.rows.length === 0 && !position" class="panel">
      <p>Noch keine Kameraden erfasst.</p>
      <RouterLink to="/kameraden" class="button">Kameraden anlegen</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.positions {
  display: flex;
  gap: 0.4rem;
  overflow-x: auto;
  margin: 0 -1rem 0.75rem;
  padding: 0 1rem 0.25rem;
  scrollbar-width: none;
}
@media (min-width: 761px) {
  .positions {
    flex-wrap: wrap;
    margin: 0 0 0.75rem;
    padding: 0;
  }
}
.chip {
  flex-shrink: 0;
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  min-height: 2.25rem;
  padding: 0.25rem 0.9rem;
  font-weight: 500;
}
.chip[aria-pressed="true"] {
  background: var(--brand);
  border-color: var(--brand);
  color: var(--brand-ink);
}
.counts {
  margin: 1rem 0 1.5rem;
}
.todo > li {
  border-left: 6px solid var(--line);
}
.todo > li.missing,
.todo > li.expired {
  border-left-color: var(--bad);
}
.todo > li.expiring {
  border-left-color: var(--warn);
}
.list-item {
  align-items: flex-start;
  flex-wrap: wrap;
}
.who {
  display: grid;
  min-width: 12rem;
  flex: 1 1 12rem;
}
.who strong {
  font-family: var(--font-cond);
  font-size: var(--fs-l);
  font-weight: 600;
}
.items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
  flex: 2 1 18rem;
}
.items li {
  display: flex;
  gap: 0.6rem;
  align-items: center;
}
.items .name {
  margin-right: 0.4rem;
}
.hint {
  color: var(--muted);
}
</style>
