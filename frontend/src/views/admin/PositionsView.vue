<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, errorText } from "../../api";
import type { Certification, Position } from "../../types";

const items = ref<Position[]>([]);
const certs = ref<Certification[]>([]);
const editing = ref<number | null>(null);
const draft = ref({ name: "", description: "", certification_ids: [] as number[] });
const dialog = ref<HTMLDialogElement | null>(null);
const error = ref("");

async function load(): Promise<void> {
  [items.value, certs.value] = await Promise.all([
    api<Position[]>("/api/positions"),
    api<Certification[]>("/api/certifications"),
  ]);
}
onMounted(load);

function open(item?: Position): void {
  editing.value = item?.id ?? null;
  draft.value = item
    ? { name: item.name, description: item.description, certification_ids: item.certifications.map((c) => c.id) }
    : { name: "", description: "", certification_ids: [] };
  error.value = "";
  dialog.value?.showModal();
}

async function save(): Promise<void> {
  error.value = "";
  try {
    if (editing.value) await api(`/api/positions/${editing.value}`, "PUT", draft.value);
    else await api("/api/positions", "POST", draft.value);
    dialog.value?.close();
    await load();
  } catch (e) {
    error.value = errorText(e);
  }
}

async function remove(item: Position): Promise<void> {
  if (!confirm(`Funktion „${item.name}“ löschen? Kameraden verlieren diese Zuordnung.`)) return;
  await api(`/api/positions/${item.id}`, "DELETE");
  await load();
}
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>Funktionen</h1>
      <button @click="open()">Funktion anlegen</button>
    </div>
    <p class="lede">
      Eine Funktion (z. B. AGT, Maschinist) bestimmt, welche Nachweise ein Kamerad braucht.
      Für alle geltende Nachweise legst du am besten eine Funktion „Grundausbildung“ an.
    </p>

    <ul class="list">
      <li v-for="p in items" :key="p.id" class="list-item item">
        <div class="grow">
          <strong>{{ p.name }}</strong>
          <div v-if="p.description" class="small muted">{{ p.description }}</div>
          <div class="tags">
            <span v-for="c in p.certifications" :key="c.id" class="tag">{{ c.name }}</span>
            <span v-if="p.certifications.length === 0" class="small muted">Keine Nachweise zugeordnet</span>
          </div>
        </div>
        <div class="row">
          <button class="link" @click="open(p)">Bearbeiten</button>
          <button class="link" @click="remove(p)">Löschen</button>
        </div>
      </li>
      <li v-if="items.length === 0" class="list-item muted">Noch keine Funktionen angelegt.</li>
    </ul>

    <dialog ref="dialog">
      <form class="dialog-body form" @submit.prevent="save">
        <h2>{{ editing ? "Funktion bearbeiten" : "Funktion anlegen" }}</h2>
        <label>Name <input v-model="draft.name" required maxlength="80" /></label>
        <label>Beschreibung <input v-model="draft.description" /></label>
        <fieldset>
          <legend>Geforderte Nachweise</legend>
          <label v-for="c in certs" :key="c.id" class="check">
            <input v-model="draft.certification_ids" type="checkbox" :value="c.id" />
            {{ c.name }}
            <span v-if="!c.is_active" class="tag">inaktiv</span>
          </label>
          <p v-if="certs.length === 0" class="small muted">Lege zuerst Nachweise an.</p>
        </fieldset>
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
.item {
  flex-wrap: wrap;
  align-items: flex-start;
}
.grow {
  flex: 1 1 16rem;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.4rem;
}
</style>
