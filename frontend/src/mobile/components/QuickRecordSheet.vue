<script setup lang="ts">
import { computed, ref } from "vue";

import { api, errorText } from "../../api";
import type { Certification, Member } from "../../types";
import { rememberRecent } from "../readiness";
import { toast } from "../toast";
import BottomSheet from "./BottomSheet.vue";

const props = defineProps<{ certifications: Certification[] }>();
const emit = defineEmits<{ saved: [] }>();

const isoDay = (offset = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString("sv-SE");
};

const sheet = ref<InstanceType<typeof BottomSheet> | null>(null);
const member = ref<Member | null>(null);
const fixedCert = ref(false);
const form = ref({ certification_id: 0, completed_on: isoDay(), manual_expires_on: "", note: "" });
const error = ref("");
const saving = ref(false);

const cert = computed(() => props.certifications.find((c) => c.id === form.value.certification_id));
const needsExpiry = computed(() => cert.value?.validity_mode === "manual");
const dayChoice = computed(() =>
  form.value.completed_on === isoDay() ? "today" : form.value.completed_on === isoDay(-1) ? "yesterday" : "other",
);

/** Opens the sheet for one member. With a certification the choice is fixed, which is the one tap fix from a list. */
function open(m: Member, certificationId?: number): void {
  member.value = m;
  fixedCert.value = certificationId !== undefined;
  form.value = {
    certification_id: certificationId ?? props.certifications[0]?.id ?? 0,
    completed_on: isoDay(),
    manual_expires_on: "",
    note: "",
  };
  error.value = "";
  sheet.value?.open();
}

async function save(): Promise<void> {
  if (!member.value) return;
  saving.value = true;
  error.value = "";
  try {
    await api("/api/completions", "POST", {
      member_id: member.value.id,
      certification_id: form.value.certification_id,
      completed_on: form.value.completed_on,
      manual_expires_on: needsExpiry.value ? form.value.manual_expires_on : null,
      note: form.value.note,
    });
    rememberRecent(form.value.certification_id);
    sheet.value?.close();
    toast(`${cert.value?.name ?? "Abschluss"} für ${member.value.first_name} ${member.value.last_name} eingetragen`);
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
  <BottomSheet
    ref="sheet"
    :title="fixedCert && cert ? cert.name : 'Abschluss eintragen'"
    :subtitle="member ? `${member.first_name} ${member.last_name}` : undefined"
  >
    <form id="quick-record" class="form" @submit.prevent="save">
      <label v-if="!fixedCert">
        Nachweis
        <select v-model.number="form.certification_id" required>
          <option v-for="c in certifications" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </label>
      <fieldset class="plain">
        <legend>Abgeschlossen am</legend>
        <div class="day-chips">
          <button
            type="button"
            class="chip"
            :aria-pressed="dayChoice === 'today'"
            @click="form.completed_on = isoDay()"
          >
            Heute
          </button>
          <button
            type="button"
            class="chip"
            :aria-pressed="dayChoice === 'yesterday'"
            @click="form.completed_on = isoDay(-1)"
          >
            Gestern
          </button>
          <input
            v-model="form.completed_on"
            type="date"
            required
            :max="isoDay()"
            aria-label="Datum"
            class="date"
            :class="{ on: dayChoice === 'other' }"
          />
        </div>
      </fieldset>
      <label v-if="needsExpiry">
        Gültig bis
        <input v-model="form.manual_expires_on" type="date" required :min="form.completed_on" />
      </label>
      <label>
        Bemerkung
        <input v-model="form.note" maxlength="2000" placeholder="Optional, z. B. Ort oder Ausbilder" />
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button type="submit" form="quick-record" class="big" :disabled="saving || !form.certification_id">
        {{ saving ? "Wird eingetragen …" : "Eintragen" }}
      </button>
    </template>
  </BottomSheet>
</template>

<style scoped>
.day-chips {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 0.5rem;
  align-items: center;
}
.date {
  min-width: 0;
}
.date.on {
  border-color: var(--brand);
  box-shadow: inset 0 0 0 1px var(--brand);
}
</style>
