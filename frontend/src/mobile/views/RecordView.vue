<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api, errorText } from "../../api";
import { formatDate, KIND_LABEL } from "../../labels";
import type { Certification, Overview } from "../../types";
import MIcon from "../components/MIcon.vue";
import { dueText, isCritical, parseIds, readRecent, rememberRecent, splitRecent } from "../readiness";
import { buzz } from "../toast";

const route = useRoute();
const router = useRouter();

const isoDay = (offset = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString("sv-SE");
};

const certifications = ref<Certification[]>([]);
const certQuery = ref("");
const form = ref({ certification_id: 0, completed_on: isoDay(), manual_expires_on: "", note: "" });
const overview = ref<Overview | null>(null);
const selected = ref<Set<number>>(new Set());
const onlyRequired = ref(true);
const memberQuery = ref("");
const error = ref("");
const saving = ref(false);
const result = ref<{ created: number; skipped: number; cert: string } | null>(null);

const cert = computed(() => certifications.value.find((c) => c.id === form.value.certification_id));
const needsExpiry = computed(() => cert.value?.validity_mode === "manual");

/** The step comes from the URL, so the back button of the phone goes one step back. Steps without data fall back. */
const step = computed(() => {
  const requested = Number(route.query.schritt) || 1;
  if (result.value) return 4;
  if (!form.value.certification_id) return 1;
  if (selected.value.size === 0) return Math.min(requested, 2);
  return Math.min(requested, 3);
});

function goStep(n: number): void {
  void router.push({ query: { schritt: String(n) } });
}

/** Goes one step back. Inside the flow this uses the history, after a jump into the flow it replaces the step. */
function stepBack(): void {
  const prev: unknown = window.history.state?.back;
  if (typeof prev === "string" && prev.startsWith("/erfassen")) router.back();
  else void router.replace({ query: { schritt: String(step.value - 1) } });
}

const before: unknown = window.history.state?.back;
const entry = typeof before === "string" && !before.startsWith("/erfassen") ? before : "/";

function close(): void {
  void router.push(entry);
}

onMounted(async () => {
  try {
    certifications.value = (await api<Certification[]>("/api/certifications")).filter((c) => c.is_active);
  } catch (e) {
    error.value = errorText(e);
  }
  const presetCert = parseIds(route.query.nachweis)[0];
  if (presetCert && certifications.value.some((c) => c.id === presetCert)) {
    form.value.certification_id = presetCert;
    const ids = parseIds(route.query.kameraden);
    selected.value = new Set(ids);
    void router.replace({ query: { schritt: ids.length ? "3" : "2" } });
  } else if (route.query.schritt) {
    void router.replace({ query: {} });
  }
});

async function loadMembers(): Promise<void> {
  overview.value = null;
  if (!form.value.certification_id) return;
  try {
    overview.value = await api<Overview>(`/api/overview?certification_id=${form.value.certification_id}`);
  } catch (e) {
    error.value = errorText(e);
  }
}
watch(() => form.value.certification_id, loadMembers);

const certLists = computed(() => {
  const q = certQuery.value.trim().toLowerCase();
  const all = certifications.value.filter(
    (c) => !q || c.name.toLowerCase().includes(q) || c.short_name.toLowerCase().includes(q),
  );
  return q ? { recent: [], rest: all } : splitRecent(all, readRecent());
});

function pickCert(id: number): void {
  if (id !== form.value.certification_id) {
    selected.value = new Set();
    form.value.manual_expires_on = "";
  }
  form.value.certification_id = id;
  memberQuery.value = "";
  goStep(2);
}

const rows = computed(() => {
  const q = memberQuery.value.trim().toLowerCase();
  return (overview.value?.rows ?? [])
    .map((r) => ({ member: r.member, cell: r.cells[0]! }))
    .filter((r) => r.cell !== undefined)
    .filter((r) => !onlyRequired.value || r.cell.required || selected.value.has(r.member.id))
    .filter((r) => !q || `${r.member.number} ${r.member.last_name} ${r.member.first_name}`.toLowerCase().includes(q))
    .sort(
      (a, b) =>
        a.member.last_name.localeCompare(b.member.last_name, "de") ||
        a.member.first_name.localeCompare(b.member.first_name, "de"),
    );
});
const allShownSelected = computed(
  () => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.member.id)),
);
const hiddenCount = computed(() => (overview.value?.rows.length ?? 0) - rows.value.length);

function toggle(id: number): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
  buzz(6);
}

function toggleAll(): void {
  const next = new Set(selected.value);
  const select = !allShownSelected.value;
  for (const r of rows.value) {
    if (select) next.add(r.member.id);
    else next.delete(r.member.id);
  }
  selected.value = next;
}

const selectedNames = computed(() =>
  (overview.value?.rows ?? [])
    .filter((r) => selected.value.has(r.member.id))
    .map((r) => `${r.member.first_name} ${r.member.last_name}`),
);
const dayChoice = computed(() =>
  form.value.completed_on === isoDay() ? "today" : form.value.completed_on === isoDay(-1) ? "yesterday" : "other",
);
const canSubmit = computed(
  () =>
    !saving.value &&
    selected.value.size > 0 &&
    !!form.value.completed_on &&
    (!needsExpiry.value || !!form.value.manual_expires_on),
);
const people = (n: number) => (n === 1 ? "1 Kameraden" : `${n} Kameraden`);

async function submit(): Promise<void> {
  error.value = "";
  saving.value = true;
  try {
    const res = await api<{ created: number }>("/api/completions/bulk", "POST", {
      certification_id: form.value.certification_id,
      member_ids: [...selected.value],
      completed_on: form.value.completed_on,
      manual_expires_on: needsExpiry.value ? form.value.manual_expires_on : null,
      note: form.value.note,
    });
    rememberRecent(form.value.certification_id);
    result.value = { created: res.created, skipped: selected.value.size - res.created, cert: cert.value?.name ?? "" };
    buzz(20);
    void router.replace({ query: { schritt: "4" } });
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}

/** Starts over for the next exercise, the date and the note of the last one are kept. */
function again(): void {
  result.value = null;
  selected.value = new Set();
  form.value.certification_id = 0;
  void router.replace({ query: {} });
}

const TITLES = ["Was wurde gemacht?", "Wer war dabei?", "Wann war das?"];
</script>

<template>
  <div class="record">
    <header class="top">
      <button v-if="step > 1 && step < 4" type="button" class="icon-btn" aria-label="Schritt zurück" @click="stepBack">
        <MIcon name="back" />
      </button>
      <span v-else class="spacer"></span>
      <div class="progress" :aria-label="step < 4 ? `Schritt ${step} von 3` : 'Fertig'">
        <span v-for="n in 3" :key="n" :class="{ done: n < step || step === 4, now: n === step }"></span>
      </div>
      <button type="button" class="icon-btn" aria-label="Erfassen schließen" @click="close">
        <MIcon name="close" />
      </button>
    </header>

    <p v-if="error" class="error pad" role="alert">{{ error }}</p>

    <!-- Step 1: certification -->
    <section v-if="step === 1" class="step">
      <h1>{{ TITLES[0] }}</h1>
      <label class="search-field">
        <MIcon name="search" :size="18" />
        <input v-model="certQuery" type="search" placeholder="Lehrgang, Übung oder Test" aria-label="Nachweis suchen" />
      </label>
      <template v-if="certLists.recent.length">
        <p class="group-label">Zuletzt erfasst</p>
        <ul class="group">
          <li v-for="c in certLists.recent" :key="c.id">
            <button type="button" class="cell" @click="pickCert(c.id)">
              <span class="cell-icon"><MIcon name="history" :size="18" /></span>
              <span class="cell-main">
                <strong>{{ c.name }}</strong>
                <span class="cell-sub">{{ KIND_LABEL[c.kind] }}</span>
              </span>
              <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
            </button>
          </li>
        </ul>
      </template>
      <p v-if="certLists.recent.length" class="group-label">Alle Nachweise</p>
      <ul v-if="certLists.rest.length" class="group" :class="{ gap: !certLists.recent.length }">
        <li v-for="c in certLists.rest" :key="c.id">
          <button type="button" class="cell" @click="pickCert(c.id)">
            <span class="cell-main">
              <strong>{{ c.name }}</strong>
              <span class="cell-sub">{{ KIND_LABEL[c.kind] }}</span>
            </span>
            <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
          </button>
        </li>
      </ul>
      <p v-else-if="!certLists.recent.length" class="empty">
        <strong>Nichts gefunden</strong>
        {{ certifications.length ? `Kein Nachweis passt zu „${certQuery}“.` : "Lade Nachweise …" }}
      </p>
    </section>

    <!-- Step 2: members -->
    <section v-else-if="step === 2" class="step">
      <h1>{{ TITLES[1] }}</h1>
      <p class="context">{{ cert?.name }}</p>
      <div class="tools">
        <label class="search-field">
          <MIcon name="search" :size="18" />
          <input v-model="memberQuery" type="search" placeholder="Name oder Nr" aria-label="Kamerad suchen" />
        </label>
        <div class="tool-row">
          <button type="button" class="chip" :aria-pressed="onlyRequired" @click="onlyRequired = !onlyRequired">
            Nur wer ihn braucht
          </button>
          <button type="button" class="link" :disabled="rows.length === 0" @click="toggleAll">
            {{ allShownSelected ? "Keinen wählen" : "Alle wählen" }}
          </button>
        </div>
      </div>
      <template v-if="!overview">
        <div v-for="i in 6" :key="i" class="skeleton"></div>
      </template>
      <p v-else-if="rows.length === 0" class="empty">
        <strong>Niemand passt</strong>
        <template v-if="onlyRequired && hiddenCount">
          {{ hiddenCount }} weitere brauchen diesen Nachweis nicht.
          <button type="button" class="secondary" @click="onlyRequired = false">Alle Kameraden zeigen</button>
        </template>
      </p>
      <ul v-else class="group picks">
        <li v-for="r in rows" :key="r.member.id">
          <button
            type="button"
            class="cell"
            role="checkbox"
            :aria-checked="selected.has(r.member.id)"
            @click="toggle(r.member.id)"
          >
            <span class="tick" :class="{ on: selected.has(r.member.id) }"><MIcon name="check" :size="16" /></span>
            <span class="cell-main">
              <strong>{{ r.member.last_name }}, {{ r.member.first_name }}</strong>
              <span class="cell-sub" :class="{ bad: isCritical(r.cell.status) }">
                {{ r.cell.required ? dueText(r.cell, overview.today) : "Nicht gefordert" }}
              </span>
            </span>
            <span class="cell-end nr">{{ r.member.number }}</span>
          </button>
        </li>
      </ul>
      <div class="footer">
        <button type="button" class="big" :disabled="selected.size === 0" @click="goStep(3)">
          {{ selected.size ? `Weiter mit ${people(selected.size)}` : "Kameraden auswählen" }}
        </button>
      </div>
    </section>

    <!-- Step 3: date -->
    <section v-else-if="step === 3" class="step">
      <h1>{{ TITLES[2] }}</h1>
      <p class="context">{{ cert?.name }} für {{ people(selected.size) }}</p>
      <form id="record-form" class="form" @submit.prevent="submit">
        <div class="days" role="group" aria-label="Abgeschlossen am">
          <button type="button" class="day" :aria-pressed="dayChoice === 'today'" @click="form.completed_on = isoDay()">
            <strong>Heute</strong><span>{{ formatDate(isoDay()) }}</span>
          </button>
          <button
            type="button"
            class="day"
            :aria-pressed="dayChoice === 'yesterday'"
            @click="form.completed_on = isoDay(-1)"
          >
            <strong>Gestern</strong><span>{{ formatDate(isoDay(-1)) }}</span>
          </button>
          <label class="day" :class="{ on: dayChoice === 'other' }">
            <strong>Anderes Datum</strong>
            <input v-model="form.completed_on" type="date" required :max="isoDay()" aria-label="Datum wählen" />
          </label>
        </div>
        <label v-if="needsExpiry">
          Gültig bis
          <input v-model="form.manual_expires_on" type="date" required :min="form.completed_on" />
        </label>
        <label>
          Bemerkung
          <input v-model="form.note" maxlength="2000" placeholder="Optional, z. B. Ort oder Ausbilder" />
        </label>
      </form>
      <details class="who">
        <summary>{{ people(selected.size) }} ausgewählt</summary>
        <p>{{ selectedNames.join(", ") }}</p>
        <button type="button" class="link" @click="stepBack">Auswahl ändern</button>
      </details>
      <div class="footer">
        <button type="submit" form="record-form" class="big" :disabled="!canSubmit">
          {{ saving ? "Wird eingetragen …" : `Für ${people(selected.size)} eintragen` }}
        </button>
      </div>
    </section>

    <!-- Done -->
    <section v-else class="step finished">
      <div class="seal" aria-hidden="true"><MIcon name="check" :size="44" /></div>
      <h1>{{ result?.created ? "Eingetragen" : "Schon eingetragen" }}</h1>
      <p v-if="result?.created" class="context">
        {{ result.cert }} für {{ people(result.created) }}, abgeschlossen am {{ formatDate(form.completed_on) }}.
      </p>
      <p v-if="result && result.skipped" class="muted">
        {{ result.skipped === 1 ? "1 Kamerad hatte" : `${result.skipped} Kameraden hatten` }} an diesem Tag schon einen
        Eintrag.
      </p>
      <div class="done-actions">
        <button type="button" class="big" @click="again">Weiteren Abschluss erfassen</button>
        <button type="button" class="secondary big" @click="router.push('/')">Zur Lage</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.record {
  min-height: 100dvh;
  padding-bottom: 7rem;
}
.top {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: 2.75rem 1fr 2.75rem;
  align-items: center;
  gap: 0.75rem;
  padding: calc(env(safe-area-inset-top) + 0.25rem) 0.5rem 0.25rem;
  background: color-mix(in srgb, var(--paper) 88%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.progress {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 5px;
}
.progress span {
  height: 5px;
  border-radius: 999px;
  background: var(--line);
  transition: background 0.25s;
}
.progress .done,
.progress .now {
  background: var(--brand);
}
@media (prefers-color-scheme: dark) {
  .progress .done,
  .progress .now {
    background: #8fb6e6;
  }
}
.pad {
  margin: 0.5rem var(--pad);
}
.step {
  padding: 0.75rem var(--pad) 0;
}
.step h1 {
  font-size: 2.2rem;
  margin: 0.25rem 0 0.25rem;
}
.context {
  margin: 0 0 1rem;
  color: var(--muted);
  font-size: 1.02rem;
}
.step > .search-field {
  margin: 0.75rem 0 0.25rem;
}
.gap {
  margin-top: 1rem;
}
.tools {
  position: sticky;
  top: calc(env(safe-area-inset-top) + 2.9rem);
  z-index: 5;
  padding: 0.25rem 0 0.6rem;
  background: var(--paper);
}
.tool-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.6rem;
}
.tool-row .link {
  font-weight: 600;
}
.tick {
  display: grid;
  place-items: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  border: 2px solid var(--line);
  color: transparent;
  flex-shrink: 0;
  transition:
    background 0.12s,
    border-color 0.12s;
}
.tick.on {
  background: var(--ok);
  border-color: var(--ok);
  color: #fff;
}
.picks .cell[aria-checked="true"] {
  background: color-mix(in srgb, var(--ok-soft) 55%, transparent);
}
.bad {
  color: var(--bad-ink);
}
.nr {
  font-variant-numeric: tabular-nums;
  font-size: 0.9rem;
}
.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 25;
  padding: 0.75rem var(--pad) calc(0.75rem + env(safe-area-inset-bottom));
  background: linear-gradient(to top, var(--paper) 70%, transparent);
}
.days {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}
.day {
  display: grid;
  gap: 0.15rem;
  justify-items: start;
  align-content: center;
  min-height: 4.5rem;
  padding: 0.7rem 0.9rem;
  border-radius: 14px;
  border: 2px solid transparent;
  background: var(--surface);
  color: var(--ink);
  font-weight: 400;
  text-align: left;
  font-size: var(--fs-m);
}
.day strong {
  font-family: var(--font-cond);
  font-size: 1.25rem;
  font-weight: 600;
}
.day span {
  color: var(--muted);
  font-size: 0.9rem;
}
.day[aria-pressed="true"],
.day.on {
  border-color: var(--brand);
}
label.day {
  grid-column: 1 / -1;
}
label.day input {
  margin-top: 0.25rem;
}
.who {
  margin-top: 1.25rem;
  background: var(--surface);
  border-radius: var(--r-group);
  padding: 0.85rem 1rem;
}
.who summary {
  font-weight: 600;
  cursor: pointer;
}
.who p {
  margin: 0.5rem 0;
  color: var(--muted);
}
.finished {
  text-align: center;
  padding-top: 15vh;
}
.seal {
  display: grid;
  place-items: center;
  width: 5.5rem;
  height: 5.5rem;
  margin: 0 auto 1.25rem;
  border-radius: 1.6rem;
  background: var(--ok);
  color: #fff;
  animation: pop 0.45s cubic-bezier(0.2, 1.4, 0.4, 1);
}
@keyframes pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
}
.done-actions {
  display: grid;
  gap: 0.6rem;
  margin-top: 2rem;
}
</style>
