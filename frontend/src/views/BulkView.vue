<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { api, errorText } from "../api";
import StatusPeg from "../components/StatusPeg.vue";
import { cellHint, shortName } from "../labels";
import type { Certification, Overview } from "../types";

const today = () => new Date().toLocaleDateString("sv-SE");

const certifications = ref<Certification[]>([]);
const form = ref({ certification_id: 0, completed_on: today(), manual_expires_on: "", note: "" });
const overview = ref<Overview | null>(null);
const selected = ref<Set<number>>(new Set());
const onlyRequired = ref(true);
const search = ref("");
const error = ref("");
const notice = ref("");
const saving = ref(false);

onMounted(async () => {
  certifications.value = (await api<Certification[]>("/api/certifications")).filter((c) => c.is_active);
});

const cert = computed(() => certifications.value.find((c) => c.id === form.value.certification_id));

async function loadMembers(): Promise<void> {
  overview.value = null;
  if (!form.value.certification_id) return;
  try {
    overview.value = await api<Overview>(`/api/overview?certification_id=${form.value.certification_id}`);
  } catch (e) {
    error.value = errorText(e);
  }
}

watch(
  () => form.value.certification_id,
  () => {
    selected.value = new Set();
    notice.value = "";
    void loadMembers();
  },
);

const rows = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (overview.value?.rows ?? [])
    .map((r) => ({ member: r.member, cell: r.cells[0] }))
    .filter((r) => r.cell !== undefined)
    .filter((r) => !onlyRequired.value || r.cell!.required || selected.value.has(r.member.id))
    .filter((r) => !q || `${r.member.number} ${r.member.last_name} ${r.member.first_name}`.toLowerCase().includes(q));
});

const allVisibleSelected = computed(
  () => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.member.id)),
);

function toggle(id: number): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

function toggleAllVisible(): void {
  const next = new Set(selected.value);
  const select = !allVisibleSelected.value;
  for (const r of rows.value) {
    if (select) next.add(r.member.id);
    else next.delete(r.member.id);
  }
  selected.value = next;
}

const needsExpiry = computed(() => cert.value?.validity_mode === "manual");
const canSubmit = computed(
  () =>
    !saving.value &&
    selected.value.size > 0 &&
    !!form.value.completed_on &&
    (!needsExpiry.value || !!form.value.manual_expires_on),
);

async function submit(): Promise<void> {
  error.value = "";
  notice.value = "";
  saving.value = true;
  try {
    const res = await api<{ created: number }>("/api/completions/bulk", "POST", {
      certification_id: form.value.certification_id,
      member_ids: [...selected.value],
      completed_on: form.value.completed_on,
      manual_expires_on: needsExpiry.value ? form.value.manual_expires_on : null,
      note: form.value.note,
    });
    const skipped = selected.value.size - res.created;
    notice.value =
      `${cert.value?.name}: für ${res.created} ${res.created === 1 ? "Kamerad" : "Kameraden"} eingetragen.` +
      (skipped > 0 ? ` ${skipped} hatten an diesem Tag schon einen Eintrag.` : "");
    selected.value = new Set();
    await loadMembers();
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="page">
    <h1>Erfassen</h1>
    <p class="lede">Einen Abschluss für mehrere Kameraden auf einmal eintragen, zum Beispiel nach einer Übung.</p>

    <form class="panel form" @submit.prevent="submit">
      <div class="form-grid">
        <label>
          Nachweis
          <select v-model.number="form.certification_id" required>
            <option :value="0" disabled>Bitte wählen</option>
            <option v-for="c in certifications" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label>
          Abgeschlossen am
          <input v-model="form.completed_on" type="date" required :max="today()" />
        </label>
        <label v-if="needsExpiry">
          Gültig bis
          <input v-model="form.manual_expires_on" type="date" required :min="form.completed_on" />
        </label>
      </div>
      <label>
        Bemerkung
        <input v-model="form.note" maxlength="2000" placeholder="optional, z. B. Ort oder Ausbilder" />
      </label>
    </form>

    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section v-if="form.certification_id" class="who">
      <div class="spread">
        <h2>Wer war dabei?</h2>
        <button type="button" class="link" :disabled="rows.length === 0" @click="toggleAllVisible">
          {{ allVisibleSelected ? "Auswahl aufheben" : "Alle angezeigten auswählen" }}
        </button>
      </div>
      <div class="row controls">
        <input v-model="search" type="search" placeholder="Name oder Nr" class="search" />
        <label class="check">
          <input v-model="onlyRequired" type="checkbox" />
          Nur wer den Nachweis braucht
        </label>
      </div>

      <p v-if="!overview" class="muted">Lade Kameraden …</p>
      <p v-else-if="rows.length === 0" class="panel">
        Niemand passt.
        <template v-if="onlyRequired">Blende auch Kameraden ein, die den Nachweis nicht brauchen.</template>
      </p>
      <ul v-else class="list picks">
        <li v-for="r in rows" :key="r.member.id">
          <label class="pick" :class="{ on: selected.has(r.member.id) }">
            <input type="checkbox" :checked="selected.has(r.member.id)" @change="toggle(r.member.id)" />
            <span class="name">
              <strong>{{ r.member.last_name }}, {{ r.member.first_name }}</strong>
              <span class="muted small">Nr {{ r.member.number }}</span>
            </span>
            <span class="state small">
              <span class="hint muted">{{ cellHint(r.cell!.status, r.cell!.expires_on, overview.today) }}</span>
              <StatusPeg
                :status="r.cell!.status"
                :required="r.cell!.required"
                :label="shortName(cert?.name ?? '', cert?.short_name ?? '')"
                :title="cert?.name"
              />
            </span>
          </label>
        </li>
      </ul>
    </section>

    <div v-if="form.certification_id" class="actionbar">
      <span>
        <strong>{{ selected.size }}</strong>
        {{ selected.size === 1 ? "Kamerad" : "Kameraden" }} ausgewählt
      </span>
      <button type="button" :disabled="!canSubmit" @click="submit">
        {{ selected.size > 0 ? `Für ${selected.size} eintragen` : "Eintragen" }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.who {
  margin-top: 1.5rem;
}
.controls {
  margin-bottom: 0.75rem;
  gap: 0.75rem 1.5rem;
}
.search {
  max-width: 22rem;
}
.pick {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.7rem 1rem;
  min-height: 3.5rem;
  cursor: pointer;
  font-size: var(--fs-m);
  font-weight: 400;
}
.pick.on {
  background: var(--ok-soft);
}
.pick input {
  width: 1.4rem;
  min-height: 1.4rem;
  flex-shrink: 0;
}
.name {
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
}
.name strong {
  font-family: var(--font-cond);
  font-size: var(--fs-l);
  font-weight: 600;
}
.state {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}
.actionbar {
  position: sticky;
  bottom: 0;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 -4px 16px rgb(20 30 40 / 0.08);
}
.actionbar button {
  white-space: nowrap;
  flex-shrink: 0;
}
@media (max-width: 760px) {
  .actionbar {
    bottom: calc(3.5rem + env(safe-area-inset-bottom) + 0.5rem);
  }
  .hint {
    display: none;
  }
}
</style>
