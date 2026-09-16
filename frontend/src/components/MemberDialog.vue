<script setup lang="ts">
import { ref, watch } from "vue";

import { api, errorText } from "../api";
import type { Member, Position } from "../types";

const props = defineProps<{ member: Member | null; positions: Position[] }>();
const emit = defineEmits<{ saved: [member: Member] }>();

const dialog = ref<HTMLDialogElement | null>(null);
const form = ref({ number: "", last_name: "", first_name: "", is_active: true, position_ids: [] as number[] });
const error = ref("");
const saving = ref(false);

function resetForm(): void {
  const m = props.member;
  form.value = m
      ? {
          number: m.number,
          last_name: m.last_name,
          first_name: m.first_name,
          is_active: m.is_active,
          position_ids: m.positions.map((p) => p.id),
        }
      : { number: "", last_name: "", first_name: "", is_active: true, position_ids: [] };
}
watch(() => props.member, resetForm, { immediate: true });

function open(): void {
  resetForm();
  error.value = "";
  dialog.value?.showModal();
}

async function save(): Promise<void> {
  saving.value = true;
  error.value = "";
  try {
    const saved = props.member
      ? await api<Member>(`/api/members/${props.member.id}`, "PUT", form.value)
      : await api<Member>("/api/members", "POST", form.value);
    dialog.value?.close();
    emit("saved", saved);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <dialog ref="dialog">
    <form class="dialog-body form" @submit.prevent="save">
      <h2>{{ member ? "Kamerad bearbeiten" : "Kamerad anlegen" }}</h2>
      <div class="form-grid">
        <label>Nr <input v-model="form.number" required maxlength="32" inputmode="numeric" /></label>
        <label>Name <input v-model="form.last_name" required maxlength="80" autocomplete="off" /></label>
        <label>Vorname <input v-model="form.first_name" required maxlength="80" autocomplete="off" /></label>
      </div>
      <fieldset>
        <legend>Funktionen</legend>
        <p v-if="positions.length === 0" class="muted small">Noch keine Funktionen angelegt.</p>
        <label v-for="p in positions" :key="p.id" class="check">
          <input v-model="form.position_ids" type="checkbox" :value="p.id" />
          {{ p.name }}
          <span class="muted small">({{ p.certifications.length }} Nachweise)</span>
        </label>
      </fieldset>
      <label class="check">
        <input v-model="form.is_active" type="checkbox" />
        Aktiv
      </label>
      <p v-if="!form.is_active" class="muted small">
        Inaktive Kameraden erscheinen nicht mehr in Übersicht und Offen. Ihre Nachweise bleiben erhalten.
      </p>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="row">
        <button type="submit" :disabled="saving">Speichern</button>
        <button type="button" class="secondary" @click="dialog?.close()">Abbrechen</button>
      </div>
    </form>
  </dialog>
</template>
