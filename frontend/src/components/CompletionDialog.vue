<script setup lang="ts">
import { computed, ref } from "vue";

import { api, errorText } from "../api";
import type { Certification } from "../types";

const props = defineProps<{ memberId: number; certifications: Certification[] }>();
const emit = defineEmits<{ saved: [] }>();

const today = () => new Date().toLocaleDateString("sv-SE");
const dialog = ref<HTMLDialogElement | null>(null);
const form = ref({ certification_id: 0, completed_on: today(), manual_expires_on: "", note: "" });
const error = ref("");
const saving = ref(false);

const selected = computed(() => props.certifications.find((c) => c.id === form.value.certification_id));

function open(certificationId?: number): void {
  form.value = {
    certification_id: certificationId ?? props.certifications[0]?.id ?? 0,
    completed_on: today(),
    manual_expires_on: "",
    note: "",
  };
  error.value = "";
  dialog.value?.showModal();
}

/** Saves the completion. The expiry date is only sent for certifications with manual validity. */
async function save(): Promise<void> {
  saving.value = true;
  error.value = "";
  try {
    await api("/api/completions", "POST", {
      member_id: props.memberId,
      certification_id: form.value.certification_id,
      completed_on: form.value.completed_on,
      manual_expires_on: selected.value?.validity_mode === "manual" ? form.value.manual_expires_on : null,
      note: form.value.note,
    });
    dialog.value?.close();
    emit("saved");
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
      <h2>Abschluss eintragen</h2>
      <label>
        Nachweis
        <select v-model.number="form.certification_id" required>
          <option v-for="c in certifications" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </label>
      <div class="form-grid">
        <label>
          Abgeschlossen am
          <input v-model="form.completed_on" type="date" required :max="today()" />
        </label>
        <label v-if="selected?.validity_mode === 'manual'">
          Gültig bis
          <input v-model="form.manual_expires_on" type="date" required :min="form.completed_on" />
        </label>
      </div>
      <label>
        Bemerkung
        <textarea v-model="form.note" maxlength="2000" placeholder="optional"></textarea>
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="row">
        <button type="submit" :disabled="saving || !form.certification_id">Eintragen</button>
        <button type="button" class="secondary" @click="dialog?.close()">Abbrechen</button>
      </div>
    </form>
  </dialog>
</template>
