<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { api, errorText } from "../api";
import StatusCounts from "../components/StatusCounts.vue";
import StatusPeg from "../components/StatusPeg.vue";
import { cellHint, formatDate, shortName } from "../labels";
import type { Cell, Certification, Overview } from "../types";

const data = ref<Overview | null>(null);
const error = ref("");

onMounted(async () => {
  try {
    data.value = await api<Overview>("/api/overview");
  } catch (e) {
    error.value = errorText(e);
  }
});

const certById = computed(
  () => new Map<number, Certification>((data.value?.certifications ?? []).map((c) => [c.id, c])),
);

const severity = { missing: 0, expired: 1, expiring: 2, valid: 3, not_required: 4 } as const;

const openRows = computed(() =>
  (data.value?.rows ?? [])
    .filter((r) => r.open_count > 0)
    .map((r) => ({
      ...r,
      open: r.cells
        .filter((c) => c.status === "missing" || c.status === "expired" || c.status === "expiring")
        .sort((a, b) => severity[a.status] - severity[b.status]),
    }))
    // Most urgent first: worst status, then number of open items.
    .sort((a, b) => severity[a.worst_status] - severity[b.worst_status] || b.open_count - a.open_count),
);

const doneCount = computed(() => (data.value?.rows.length ?? 0) - openRows.value.length);

function certLabel(c: Cell): string {
  const cert = certById.value.get(c.certification_id);
  return cert ? shortName(cert.name, cert.short_name) : "?";
}
function certName(c: Cell): string {
  return certById.value.get(c.certification_id)?.name ?? "";
}
</script>

<template>
  <div class="page">
    <h1>Offen</h1>
    <p v-if="data" class="lede">
      Stand {{ formatDate(data.today) }}.
      <template v-if="openRows.length === 0">Alle {{ data.rows.length }} aktiven Kameraden sind vollständig.</template>
      <template v-else>
        {{ openRows.length }} von {{ data.rows.length }} Kameraden haben offene Nachweise, {{ doneCount }} sind vollständig.
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
              <StatusPeg :status="c.status" :label="certLabel(c)" :title="certName(c)" />
              <span class="small">
                <span class="name">{{ certName(c) }}</span>
                <span class="hint">{{ cellHint(c.status, c.expires_on, data!.today) }}</span>
              </span>
            </li>
          </ul>
        </RouterLink>
      </li>
    </ul>

    <div v-else-if="data && data.rows.length === 0" class="panel">
      <p>Noch keine Kameraden erfasst.</p>
      <RouterLink to="/kameraden" class="button">Kameraden anlegen</RouterLink>
    </div>
  </div>
</template>

<style scoped>
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
