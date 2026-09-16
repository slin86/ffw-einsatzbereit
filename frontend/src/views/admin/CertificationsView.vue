<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, errorText } from "../../api";
import { KIND_LABEL, VALIDITY_LABEL } from "../../labels";
import type { Certification, CertificationKind, ValidityMode } from "../../types";

type Draft = Omit<Certification, "id">;

const empty = (): Draft => ({
  name: "",
  short_name: "",
  kind: "seminar",
  description: "",
  validity_mode: "fixed_duration",
  validity_months: 12,
  warn_days: 60,
  sort_order: 0,
  is_active: true,
});

const items = ref<Certification[]>([]);
const editing = ref<number | null>(null);
const draft = ref<Draft>(empty());
const dialog = ref<HTMLDialogElement | null>(null);
const error = ref("");
const listError = ref("");

const kinds = Object.keys(KIND_LABEL) as CertificationKind[];
const modes = Object.keys(VALIDITY_LABEL) as ValidityMode[];

async function load(): Promise<void> {
  items.value = await api<Certification[]>("/api/certifications");
}
onMounted(load);

function open(item?: Certification): void {
  editing.value = item?.id ?? null;
  draft.value = item ? { ...item } : { ...empty(), sort_order: items.value.length + 1 };
  error.value = "";
  dialog.value?.showModal();
}

function needsMonths(): boolean {
  return draft.value.validity_mode === "fixed_duration" || draft.value.validity_mode === "end_of_year";
}

async function save(): Promise<void> {
  error.value = "";
  const body = { ...draft.value, validity_months: needsMonths() ? draft.value.validity_months : null };
  try {
    if (editing.value) await api(`/api/certifications/${editing.value}`, "PUT", body);
    else await api("/api/certifications", "POST", body);
    dialog.value?.close();
    await load();
  } catch (e) {
    error.value = errorText(e);
  }
}

async function remove(item: Certification): Promise<void> {
  if (!confirm(`Nachweis „${item.name}“ löschen?`)) return;
  listError.value = "";
  try {
    await api(`/api/certifications/${item.id}`, "DELETE");
    await load();
  } catch (e) {
    listError.value = errorText(e);
  }
}

function validityText(c: Certification): string {
  if (c.validity_mode === "fixed_duration") return `${c.validity_months} Monate`;
  if (c.validity_mode === "end_of_year") return `${c.validity_months} Monate, bis Jahresende`;
  return VALIDITY_LABEL[c.validity_mode];
}
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>Nachweise</h1>
      <button @click="open()">Nachweis anlegen</button>
    </div>
    <p class="lede">Seminare, Übungen, Tests und Weiterbildungen. Welche davon ein Kamerad braucht, legst du über die Funktionen fest.</p>
    <p v-if="listError" class="error">{{ listError }}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Kürzel</th>
            <th>Art</th>
            <th>Gültigkeit</th>
            <th>Warnung</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id" :class="{ inactive: !c.is_active }">
            <td>
              <strong>{{ c.name }}</strong>
              <span v-if="!c.is_active" class="tag">inaktiv</span>
            </td>
            <td>{{ c.short_name || "–" }}</td>
            <td>{{ KIND_LABEL[c.kind] }}</td>
            <td>{{ validityText(c) }}</td>
            <td>{{ c.validity_mode === "unlimited" ? "–" : `${c.warn_days} Tage vorher` }}</td>
            <td class="actions">
              <button class="link" @click="open(c)">Bearbeiten</button>
              <button class="link" @click="remove(c)">Löschen</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="6" class="muted">Noch keine Nachweise angelegt.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <dialog ref="dialog">
      <form class="dialog-body form" @submit.prevent="save">
        <h2>{{ editing ? "Nachweis bearbeiten" : "Nachweis anlegen" }}</h2>
        <div class="form-grid">
          <label>Name <input v-model="draft.name" required maxlength="120" /></label>
          <label>
            Kürzel für die Übersicht
            <input v-model="draft.short_name" maxlength="12" placeholder="z. B. AGT-Ü" />
          </label>
          <label>
            Art
            <select v-model="draft.kind">
              <option v-for="k in kinds" :key="k" :value="k">{{ KIND_LABEL[k] }}</option>
            </select>
          </label>
        </div>
        <label>
          Gültigkeit
          <select v-model="draft.validity_mode">
            <option v-for="m in modes" :key="m" :value="m">{{ VALIDITY_LABEL[m] }}</option>
          </select>
        </label>
        <div class="form-grid">
          <label v-if="needsMonths()">
            Dauer in Monaten
            <input v-model.number="draft.validity_months" type="number" min="1" max="240" required />
          </label>
          <label v-if="draft.validity_mode !== 'unlimited'">
            Warnen ab (Tage vor Ablauf)
            <input v-model.number="draft.warn_days" type="number" min="0" max="730" required />
          </label>
          <label>
            Reihenfolge
            <input v-model.number="draft.sort_order" type="number" />
          </label>
        </div>
        <p class="small muted">
          <template v-if="draft.validity_mode === 'fixed_duration'">
            Beispiel: Abschluss am 10.03.2026 bei 12 Monaten ist gültig bis 09.03.2027.
          </template>
          <template v-else-if="draft.validity_mode === 'end_of_year'">
            Beispiel: Abschluss am 10.03.2026 bei 12 Monaten ist gültig bis 31.12.2027.
          </template>
          <template v-else-if="draft.validity_mode === 'manual'">
            Beim Eintragen eines Abschlusses wird das Ablaufdatum abgefragt.
          </template>
        </p>
        <label>Beschreibung <textarea v-model="draft.description"></textarea></label>
        <label class="check"><input v-model="draft.is_active" type="checkbox" /> Aktiv</label>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="row">
          <button type="submit">Speichern</button>
          <button type="button" class="secondary" @click="dialog?.close()">Abbrechen</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.actions {
  white-space: nowrap;
  text-align: right;
}
tr.inactive td {
  color: var(--muted);
}
</style>
