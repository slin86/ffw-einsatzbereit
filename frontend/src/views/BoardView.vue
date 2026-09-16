<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { api, download, errorText } from "../api";
import FilterBar from "../components/FilterBar.vue";
import StatusCounts from "../components/StatusCounts.vue";
import StatusPeg from "../components/StatusPeg.vue";
import { useMatrixFilter } from "../filter";
import { cellHint, certShortName, formatDate, STATUS_LABEL } from "../labels";
import type { Certification, Overview, Position } from "../types";

const { filter, update, reset, queryString } = useMatrixFilter();
const data = ref<Overview | null>(null);
const positions = ref<Position[]>([]);
const allCerts = ref<Certification[]>([]);
const error = ref("");
const loading = ref(false);
const exporting = ref("");

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    data.value = await api<Overview>(`/api/overview?${queryString.value}`);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const [p, c] = await Promise.all([api<Position[]>("/api/positions"), api<Certification[]>("/api/certifications")]);
  positions.value = p;
  allCerts.value = c.filter((x) => x.is_active);
});
watch(queryString, load, { immediate: true });

async function exportAs(fmt: "csv" | "xlsx" | "pdf"): Promise<void> {
  exporting.value = fmt;
  try {
    await download(`/api/exports/${fmt}?${queryString.value}`);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    exporting.value = "";
  }
}

const certs = computed(() => data.value?.certifications ?? []);
const certById = computed(() => new Map(certs.value.map((c) => [c.id, c])));
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>Übersicht</h1>
      <div class="row exports">
        <span class="muted small">Export der aktuellen Auswahl:</span>
        <button class="secondary" :disabled="!!exporting" @click="exportAs('csv')">CSV</button>
        <button class="secondary" :disabled="!!exporting" @click="exportAs('xlsx')">Excel</button>
        <button class="secondary" :disabled="!!exporting" @click="exportAs('pdf')">PDF</button>
      </div>
    </div>

    <FilterBar :filter="filter" :positions="positions" :certifications="allCerts" @update="update" @reset="reset" />

    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="data">
      <div class="spread meta">
        <p class="muted small">
          {{ data.rows.length }} Kameraden, Stand {{ formatDate(data.today) }}
          <span v-if="loading"> · wird aktualisiert</span>
        </p>
        <StatusCounts :counts="data.counts" class="counts" />
      </div>

      <p v-if="data.rows.length === 0" class="panel">Keine Kameraden passen zu diesem Filter.</p>

      <div v-else class="table-wrap matrix">
        <table>
          <thead>
            <tr>
              <th class="sticky">Kamerad</th>
              <th v-for="c in certs" :key="c.id" :title="c.name" class="cert-head">
                {{ c.name }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.rows" :key="row.member.id" :class="{ inactive: !row.member.is_active }">
              <th class="sticky" scope="row">
                <RouterLink :to="`/kameraden/${row.member.id}`">
                  {{ row.member.last_name }}, {{ row.member.first_name }}
                </RouterLink>
                <span class="muted small nr">{{ row.member.number }}</span>
              </th>
              <td
                v-for="cell in row.cells"
                :key="cell.certification_id"
                class="cell"
                :class="cell.status"
                :title="STATUS_LABEL[cell.status]"
              >
                {{ cellHint(cell.status, cell.expires_on, data.today) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <ul v-if="data.rows.length" class="list board">
        <li v-for="row in data.rows" :key="row.member.id">
          <RouterLink :to="`/kameraden/${row.member.id}`" class="list-item">
            <div class="who">
              <strong>{{ row.member.last_name }}, {{ row.member.first_name }}</strong>
              <span class="muted small">
                Nr {{ row.member.number }}<template v-if="!row.member.is_active"> · inaktiv</template>
              </span>
            </div>
            <div class="pegs">
              <StatusPeg
                v-for="cell in row.cells"
                :key="cell.certification_id"
                :status="cell.status"
                :required="cell.required"
                :label="certShortName(certById, cell.certification_id)"
                :title="certById.get(cell.certification_id)?.name"
              />
            </div>
          </RouterLink>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.exports {
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}
.meta {
  margin: 1rem 0 0.5rem;
  align-items: center;
}
.meta p {
  margin: 0;
}
.counts {
  flex: 0 1 26rem;
}
.matrix th,
.matrix td {
  white-space: nowrap;
}
.matrix th.cert-head {
  font-size: var(--fs-s);
  min-width: 6.5rem;
  max-width: 8rem;
  white-space: normal;
  hyphens: auto;
  vertical-align: bottom;
  line-height: 1.15;
}
.sticky {
  position: sticky;
  left: 0;
  background: var(--surface);
  z-index: 1;
  font-family: var(--font);
  font-weight: 500;
}
.nr {
  margin-left: 0.4rem;
}
.sticky a {
  color: var(--ink);
  text-decoration: none;
}
.sticky a:hover {
  text-decoration: underline;
}
.cell {
  text-align: center;
  font-size: var(--fs-s);
  border-left: 2px solid var(--surface);
}
.cell.valid {
  background: var(--ok-soft);
  color: var(--ok-ink);
}
.cell.expiring {
  background: var(--warn-soft);
  color: var(--warn-ink);
  font-weight: 600;
}
.cell.expired {
  background: var(--bad-soft);
  color: var(--bad-ink);
  font-weight: 600;
}
.cell.missing {
  background: repeating-linear-gradient(-45deg, var(--bad-soft) 0 6px, var(--surface) 6px 9px);
  color: var(--bad-ink);
  font-weight: 600;
}
.cell.not_required {
  color: var(--none-ink);
}
tr.inactive th,
tr.inactive td {
  opacity: 0.55;
}

.board {
  display: none;
}
.who {
  display: grid;
  flex: 1 1 10rem;
}
.who strong {
  font-family: var(--font-cond);
  font-size: var(--fs-l);
  font-weight: 600;
}
.pegs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  flex: 1 1 100%;
}
.board .list-item {
  flex-wrap: wrap;
}

@media (max-width: 760px) {
  .matrix {
    display: none;
  }
  .board {
    display: block;
  }
  .exports .muted {
    display: none;
  }
}
</style>
