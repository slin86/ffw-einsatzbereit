<script setup lang="ts">
import { computed, ref } from "vue";

import { api, errorText } from "../api";
import type { Member } from "../types";

const emit = defineEmits<{ deleted: [count: number] }>();

const CONFIRM_WORD = "löschen";

const dialog = ref<HTMLDialogElement | null>(null);
const members = ref<Member[]>([]);
const confirmation = ref("");
const error = ref("");
const busy = ref(false);

const confirmed = computed(() => confirmation.value.trim().toLowerCase() === CONFIRM_WORD);

function open(selection: Member[]): void {
  members.value = selection;
  confirmation.value = "";
  error.value = "";
  dialog.value?.showModal();
}

async function remove(): Promise<void> {
  if (!confirmed.value) return;
  busy.value = true;
  error.value = "";
  try {
    const ids = members.value.map((m) => m.id);
    const res =
      ids.length === 1
        ? await api<{ deleted: number }>(`/api/members/${ids[0]}`, "DELETE")
        : await api<{ deleted: number }>("/api/members/delete", "POST", { member_ids: ids });
    dialog.value?.close();
    emit("deleted", res.deleted);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    busy.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <dialog ref="dialog">
    <form class="dialog-body form" @submit.prevent="remove">
      <h2>{{ members.length === 1 ? "Kamerad löschen" : `${members.length} Kameraden löschen` }}</h2>
      <p>
        Das entfernt
        {{ members.length === 1 ? "den Kameraden" : "die Kameraden" }} samt allen Abschlüssen und den zugehörigen
        Protokolleinträgen. Das lässt sich nicht rückgängig machen.
      </p>
      <ul class="names">
        <li v-for="m in members" :key="m.id">
          {{ m.last_name }}, {{ m.first_name }} <span class="muted small">Nr {{ m.number }}</span>
        </li>
      </ul>
      <p class="muted small">Soll die Historie erhalten bleiben, setze den Kameraden stattdessen auf inaktiv.</p>
      <label>
        Tippe „{{ CONFIRM_WORD }}“ zum Bestätigen
        <input v-model="confirmation" type="text" autocomplete="off" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="row">
        <button type="submit" class="danger" :disabled="!confirmed || busy">Endgültig löschen</button>
        <button type="button" class="secondary" @click="dialog?.close()">Abbrechen</button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.names {
  margin: 0;
  padding-left: 1.2rem;
  max-height: 12rem;
  overflow-y: auto;
}
</style>
