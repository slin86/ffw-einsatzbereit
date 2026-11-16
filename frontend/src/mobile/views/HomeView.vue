<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { api, errorText } from "../../api";
import { EMPTY_FILTER, filterToSearch, parseFilter } from "../../filter";
import { formatDate } from "../../labels";
import { buildOpenRows } from "../../todo";
import type { Overview, Position } from "../../types";
import AppBar from "../components/AppBar.vue";
import ExportSheet from "../components/ExportSheet.vue";
import MIcon from "../components/MIcon.vue";
import PegBoard from "../components/PegBoard.vue";
import PullRefresh from "../components/PullRefresh.vue";
import QuickRecordSheet from "../components/QuickRecordSheet.vue";
import SegmentedControl from "../components/SegmentedControl.vue";
import { dueText, readiness, segmentCounts, segmentRows, type Segment } from "../readiness";

const route = useRoute();
const router = useRouter();
const data = ref<Overview | null>(null);
const positions = ref<Position[]>([]);
const error = ref("");
const segment = ref<Segment>("critical");
const showAll = ref(false);
const quick = ref<InstanceType<typeof QuickRecordSheet> | null>(null);
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
  try {
    positions.value = await api<Position[]>("/api/positions");
  } catch (e) {
    error.value = errorText(e);
  }
});
watch(search, load, { immediate: true });

function selectPosition(id: number | null): void {
  showAll.value = false;
  void router.replace({ query: id === null ? {} : { position_id: String(id) } });
}

const stats = computed(() => readiness(data.value?.rows ?? []));
const openRows = computed(() => buildOpenRows(data.value?.rows ?? []));
const counts = computed(() => segmentCounts(openRows.value));

/** Opens on the most urgent segment that has entries, so the first screen always shows work. */
watch(counts, (c) => {
  if (c[segment.value] === 0) segment.value = c.critical ? "critical" : c.soon ? "soon" : "all";
});

const visible = computed(() => segmentRows(openRows.value, segment.value));
const LIMIT = 8;
const shown = computed(() => (showAll.value ? visible.value : visible.value.slice(0, LIMIT)));
const certName = (id: number) => data.value?.certifications.find((c) => c.id === id)?.name ?? "";
const activeCerts = computed(() => (data.value?.certifications ?? []).filter((c) => c.is_active));

const headline = computed(() => {
  const s = stats.value;
  if (!data.value) return "";
  if (s.total === 0) return position.value ? `Niemand mit Funktion ${position.value.name}` : "Noch keine Kameraden";
  if (s.critical === 0) return `Alle ${s.total} einsatzbereit`;
  return `${s.ready} von ${s.total} einsatzbereit`;
});
const subline = computed(() => {
  const s = stats.value;
  const parts: string[] = [];
  if (s.critical) parts.push(`${s.critical} mit fehlenden oder abgelaufenen Nachweisen`);
  if (s.soon) parts.push(`${s.soon} bald fällig`);
  return parts.join(", ");
});
const exportQuery = computed(() => filterToSearch({ ...EMPTY_FILTER, position_id: positionId.value, only_open: true }));
</script>

<template>
  <PullRefresh :refresh="load" />
  <AppBar title="Lage" :subtitle="data ? `Stand ${formatDate(data.today)}` : undefined">
    <template #actions>
      <button type="button" class="icon-btn" aria-label="Offene Punkte teilen" @click="exporter?.open()">
        <MIcon name="share" />
      </button>
    </template>
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

  <section class="hero">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <h2 class="headline" :class="{ calm: data && stats.critical === 0 }">{{ headline || " " }}</h2>
    <p class="subline">{{ subline || (data ? "Keine offenen Punkte." : " ") }}</p>
    <PegBoard :rows="data?.rows ?? null" />
  </section>

  <section v-if="data && openRows.length" class="section">
    <div class="section-head">
      <h2>Zu erledigen</h2>
    </div>
    <SegmentedControl
      v-model="segment"
      label="Offene Punkte filtern"
      :options="[
        { value: 'critical', label: 'Dringend', count: counts.critical },
        { value: 'soon', label: 'Bald fällig', count: counts.soon },
        { value: 'all', label: 'Alle', count: counts.all },
      ]"
    />

    <p v-if="visible.length === 0" class="empty">
      <strong>{{ segment === "critical" ? "Nichts Dringendes" : "Nichts bald fällig" }}</strong>
      Schau unter „Alle“ nach den übrigen Punkten.
    </p>

    <ul v-else class="todo">
      <li v-for="row in shown" :key="row.member.id" class="card">
        <RouterLink :to="`/kameraden/${row.member.id}`" class="who">
          <span>
            <strong>{{ row.member.last_name }}, {{ row.member.first_name }}</strong>
            <span class="nr">Nr {{ row.member.number }}</span>
          </span>
          <MIcon name="chevron" :size="18" />
        </RouterLink>
        <ul class="items">
          <li v-for="c in row.open" :key="c.certification_id" :class="c.status">
            <span class="mark" aria-hidden="true"></span>
            <span class="what">
              <span class="name">{{ certName(c.certification_id) }}</span>
              <span class="due">{{ dueText(c, data.today) }}</span>
            </span>
            <button
              type="button"
              class="secondary fix"
              :aria-label="`${certName(c.certification_id)} für ${row.member.first_name} ${row.member.last_name} eintragen`"
              @click="quick?.open(row.member, c.certification_id)"
            >
              Eintragen
            </button>
          </li>
        </ul>
      </li>
    </ul>
    <button v-if="!showAll && visible.length > LIMIT" type="button" class="secondary big more" @click="showAll = true">
      Alle {{ visible.length }} anzeigen
    </button>
  </section>

  <section v-else-if="data && data.rows.length === 0 && !position" class="section">
    <div class="empty">
      <strong>Noch keine Kameraden</strong>
      Lege die Mannschaft an, dann zeigt die Lage, wer einsatzbereit ist.
      <RouterLink to="/kameraden" class="button">Kameraden anlegen</RouterLink>
    </div>
  </section>

  <QuickRecordSheet ref="quick" :certifications="activeCerts" @saved="load" />
  <ExportSheet
    ref="exporter"
    :query="exportQuery"
    :description="position ? `Offene Punkte, Funktion ${position.name}` : 'Alle offenen Punkte'"
  />
</template>

<style scoped>
.chip-row {
  margin-bottom: 0.25rem;
}
.hero {
  margin: 0.75rem var(--pad) 0;
  padding: 1.1rem 1.1rem 1.2rem;
  background: var(--surface);
  border-radius: 18px;
}
.headline {
  font-size: 2rem;
  line-height: 1.05;
  margin: 0;
  color: var(--bad-ink);
}
.headline.calm {
  color: var(--ok-ink);
}
.subline {
  margin: 0.3rem 0 1rem;
  color: var(--muted);
  font-size: 0.95rem;
}
.hero .error {
  margin-bottom: 0.75rem;
}
.section .segmented {
  margin-bottom: 0.75rem;
}
.todo {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.6rem;
}
.card {
  background: var(--surface);
  border-radius: var(--r-group);
  overflow: hidden;
}
.who {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 0.9rem 0.35rem 1rem;
  color: var(--ink);
  text-decoration: none;
}
.who > span {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-width: 0;
}
.who strong {
  font-family: var(--font-cond);
  font-size: 1.25rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.who .micon {
  color: var(--muted);
}
.nr {
  color: var(--muted);
  font-size: 0.85rem;
  white-space: nowrap;
}
.items {
  list-style: none;
  margin: 0;
  padding: 0 0 0.35rem;
}
.items li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.45rem 0.75rem 0.45rem 1rem;
}
.mark {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 3px;
  flex-shrink: 0;
  background: var(--bad);
}
.missing .mark {
  background: transparent;
  box-shadow: inset 0 0 0 2px var(--bad);
}
.expiring .mark {
  background: var(--warn);
}
.what {
  display: grid;
  flex: 1;
  min-width: 0;
  line-height: 1.25;
}
.name {
  font-weight: 500;
}
.due {
  font-size: 0.88rem;
  color: var(--bad-ink);
}
.expiring .due {
  color: var(--warn-ink);
}
.fix {
  min-height: 2.4rem;
  padding: 0.3rem 0.85rem;
  border-radius: 999px;
  font-size: 0.9rem;
  flex-shrink: 0;
}
.more {
  margin-top: 0.75rem;
}
</style>
