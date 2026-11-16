<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { api, errorText } from "../../api";
import { EMPTY_FILTER, filterToSearch, parseFilter } from "../../filter";
import { KIND_LABEL, STATUS_LABEL } from "../../labels";
import type { CellStatus, Overview } from "../../types";
import AppBar from "../components/AppBar.vue";
import ExportSheet from "../components/ExportSheet.vue";
import MIcon from "../components/MIcon.vue";
import PullRefresh from "../components/PullRefresh.vue";
import { dueText, groupByStatus, isCritical, validityText } from "../readiness";

const props = defineProps<{ id: number }>();
const route = useRoute();
const router = useRouter();
const data = ref<Overview | null>(null);
const error = ref("");
const selecting = ref(false);
const selected = ref<Set<number>>(new Set());
const exporter = ref<InstanceType<typeof ExportSheet> | null>(null);

const positionId = computed(() => parseFilter(route.query).position_id);
const query = computed(() =>
  filterToSearch({ ...EMPTY_FILTER, certification_id: props.id, position_id: positionId.value }),
);

async function load(): Promise<void> {
  error.value = "";
  try {
    data.value = await api<Overview>(`/api/overview?${query.value}`);
  } catch (e) {
    error.value = errorText(e);
  }
}
watch(query, load, { immediate: true });

const cert = computed(() => data.value?.certifications.find((c) => c.id === props.id));
const groups = computed(() => (data.value ? groupByStatus(data.value, props.id) : []));
const openIds = computed(() =>
  groups.value
    .filter((g) => g.status !== "valid" && g.status !== "not_required")
    .flatMap((g) => g.entries.map((e) => e.member.id)),
);
const subtitle = computed(() =>
  cert.value ? `${KIND_LABEL[cert.value.kind]}, ${validityText(cert.value)}` : undefined,
);

const GROUP_TITLE: Record<CellStatus, string> = {
  missing: "Fehlt",
  expired: "Abgelaufen",
  expiring: "Läuft bald ab",
  valid: "Gültig",
  not_required: "Nicht gefordert",
};

function toggle(id: number): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

function startSelecting(preset: number[] = []): void {
  selected.value = new Set(preset);
  selecting.value = true;
}

function stopSelecting(): void {
  selecting.value = false;
  selected.value = new Set();
}

/** Hands the selection over to the record flow, which then only asks for the date. */
function record(ids: number[]): void {
  void router.push({
    path: "/erfassen",
    query: { nachweis: String(props.id), ...(ids.length ? { kameraden: ids.join(",") } : {}) },
  });
}
</script>

<template>
  <PullRefresh :refresh="load" />
  <AppBar :title="cert?.name ?? 'Nachweis'" :subtitle="subtitle" back-label="Nachweise">
    <template #actions>
      <button v-if="!selecting" type="button" class="icon-btn" aria-label="Liste teilen" @click="exporter?.open()">
        <MIcon name="share" />
      </button>
      <button v-if="data && !selecting" type="button" class="link select" @click="startSelecting()">Auswählen</button>
      <button v-if="selecting" type="button" class="link select" @click="stopSelecting">Fertig</button>
    </template>
    <p v-if="cert?.description" class="desc">{{ cert.description }}</p>
    <button v-if="data && !selecting" type="button" class="big record" @click="record([])">
      <MIcon name="plus" :size="20" /> Abschluss für mehrere erfassen
    </button>
  </AppBar>

  <div class="section">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="!data">
      <div v-for="i in 4" :key="i" class="skeleton"></div>
    </template>
    <p v-else-if="groups.length === 0" class="empty">
      <strong>Niemand in dieser Auswahl</strong>
      Für diese Funktion gibt es keine aktiven Kameraden.
    </p>

    <template v-for="g in groups" :key="g.status">
      <details v-if="g.status === 'not_required'" class="more">
        <summary class="group-label">{{ GROUP_TITLE[g.status] }} ({{ g.entries.length }})</summary>
        <ul class="group">
          <li v-for="e in g.entries" :key="e.member.id">
            <RouterLink :to="`/kameraden/${e.member.id}`" class="cell">
              <span class="cell-main">
                <strong>{{ e.member.last_name }}, {{ e.member.first_name }}</strong>
                <span class="cell-sub">{{ dueText(e.cell, data!.today) }}</span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </details>
      <template v-else>
        <div class="group-head">
          <p class="group-label" :class="g.status">
            <span class="dot" aria-hidden="true"></span>{{ GROUP_TITLE[g.status] }} ({{ g.entries.length }})
          </p>
          <button
            v-if="selecting && g.status !== 'valid'"
            type="button"
            class="link"
            @click="g.entries.forEach((e) => selected.has(e.member.id) || toggle(e.member.id))"
          >
            Alle wählen
          </button>
        </div>
        <ul class="group">
          <li v-for="e in g.entries" :key="e.member.id">
            <button
              v-if="selecting"
              type="button"
              class="cell"
              role="checkbox"
              :aria-checked="selected.has(e.member.id)"
              @click="toggle(e.member.id)"
            >
              <span class="tick" :class="{ on: selected.has(e.member.id) }"><MIcon name="check" :size="16" /></span>
              <span class="cell-main">
                <strong>{{ e.member.last_name }}, {{ e.member.first_name }}</strong>
                <span class="cell-sub" :class="{ bad: isCritical(e.cell.status) }">{{
                  dueText(e.cell, data!.today)
                }}</span>
              </span>
            </button>
            <RouterLink v-else :to="`/kameraden/${e.member.id}`" class="cell">
              <span class="cell-main">
                <strong>{{ e.member.last_name }}, {{ e.member.first_name }}</strong>
                <span class="cell-sub" :class="{ bad: isCritical(e.cell.status), warn: e.cell.status === 'expiring' }">
                  {{ dueText(e.cell, data!.today) }}
                </span>
              </span>
              <span class="cell-end">
                <span class="sr-only">{{ STATUS_LABEL[e.cell.status] }}</span>
                <MIcon name="chevron" :size="18" />
              </span>
            </RouterLink>
          </li>
        </ul>
      </template>
    </template>

    <button
      v-if="data && !selecting && openIds.length"
      type="button"
      class="secondary big gap"
      @click="startSelecting(openIds)"
    >
      Alle {{ openIds.length }} Offenen auswählen
    </button>
  </div>

  <div v-if="selecting" class="selectbar">
    <span>
      <strong>{{ selected.size }}</strong> ausgewählt
    </span>
    <button type="button" :disabled="selected.size === 0" @click="record([...selected])">Erfassen</button>
  </div>

  <ExportSheet ref="exporter" :query="query" :description="cert?.name ?? ''" />
</template>

<style scoped>
.select {
  font-weight: 600;
  padding: 0.5rem 0.6rem;
  min-height: 2.75rem;
}
.desc {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}
.record {
  margin-top: 1rem;
}
.section {
  margin-top: 0.5rem;
}
.group-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.group-label .dot {
  display: inline-block;
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 2px;
  margin-right: 0.45rem;
  background: var(--ok);
}
.group-label.expiring .dot {
  background: var(--warn);
}
.group-label.expired .dot {
  background: var(--bad);
}
.group-label.missing .dot {
  background: transparent;
  box-shadow: inset 0 0 0 2px var(--bad);
}
.bad {
  color: var(--bad-ink);
}
.warn {
  color: var(--warn-ink);
}
.more summary {
  cursor: pointer;
}
.tick {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  border: 2px solid var(--line);
  color: transparent;
  flex-shrink: 0;
}
.tick.on {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.gap {
  margin-top: 1.25rem;
}
.selectbar {
  position: fixed;
  left: 0.75rem;
  right: 0.75rem;
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 0.6rem);
  z-index: 25;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.6rem 0.6rem 1.1rem;
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 8px 28px rgb(10 20 30 / 0.22);
}
.selectbar button {
  border-radius: 12px;
  min-width: 8rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
</style>
