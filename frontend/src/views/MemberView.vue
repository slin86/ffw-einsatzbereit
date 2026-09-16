<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { api, errorText } from "../api";
import AuditList from "../components/AuditList.vue";
import CompletionDialog from "../components/CompletionDialog.vue";
import MemberDialog from "../components/MemberDialog.vue";
import StatusPeg from "../components/StatusPeg.vue";
import { cellHint, formatDate, KIND_LABEL, shortName, STATUS_LABEL } from "../labels";
import { session } from "../session";
import type { Certification, Completion, MemberDetail, Position } from "../types";

const props = defineProps<{ id: number }>();

const detail = ref<MemberDetail | null>(null);
const certifications = ref<Certification[]>([]);
const positions = ref<Position[]>([]);
const error = ref("");
const memberDialog = ref<InstanceType<typeof MemberDialog> | null>(null);
const completionDialog = ref<InstanceType<typeof CompletionDialog> | null>(null);
const auditList = ref<InstanceType<typeof AuditList> | null>(null);
const showAudit = ref(false);

async function reloadAll(): Promise<void> {
  await load();
  auditList.value?.reload();
}
const today = new Date().toLocaleDateString("sv-SE");

async function load(): Promise<void> {
  try {
    detail.value = await api<MemberDetail>(`/api/members/${props.id}`);
  } catch (e) {
    error.value = errorText(e);
  }
}

onMounted(async () => {
  const [c, p] = await Promise.all([
    api<Certification[]>("/api/certifications"),
    api<Position[]>("/api/positions"),
  ]);
  certifications.value = c.filter((x) => x.is_active);
  positions.value = p;
});
watch(() => props.id, load, { immediate: true });

const certById = computed(() => new Map(certifications.value.map((c) => [c.id, c])));
function pegLabel(id: number): string {
  const c = certById.value.get(id);
  return c ? shortName(c.name, c.short_name) : "?";
}

const required = computed(() => detail.value?.cells.filter((c) => c.required) ?? []);
const optional = computed(() => detail.value?.cells.filter((c) => !c.required && c.completed_on) ?? []);

function canDelete(entry: Completion): boolean {
  return session.user?.role === "admin" || entry.recorded_by_id === session.user?.id;
}

async function remove(entry: Completion): Promise<void> {
  if (!confirm(`Eintrag „${entry.certification_name}“ vom ${formatDate(entry.completed_on)} löschen?`)) return;
  try {
    await api(`/api/completions/${entry.id}`, "DELETE");
    await reloadAll();
  } catch (e) {
    error.value = errorText(e);
  }
}
</script>

<template>
  <div class="page">
    <RouterLink to="/kameraden" class="back small">Alle Kameraden</RouterLink>
    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="detail">
      <div class="spread head">
        <div>
          <h1>{{ detail.member.first_name }} {{ detail.member.last_name }}</h1>
          <p class="row muted">
            Nr {{ detail.member.number }}
            <span v-if="!detail.member.is_active" class="tag">inaktiv</span>
            <span v-for="p in detail.member.positions" :key="p.id" class="tag">{{ p.name }}</span>
            <span v-if="detail.member.positions.length === 0">Keine Funktion zugeordnet</span>
          </p>
        </div>
        <div class="row">
          <button @click="completionDialog?.open()">Abschluss eintragen</button>
          <button class="secondary" @click="memberDialog?.open()">Bearbeiten</button>
        </div>
      </div>

      <section>
        <h2>Geforderte Nachweise</h2>
        <p v-if="required.length === 0" class="muted">
          Über die Funktionen dieses Kameraden sind keine Nachweise gefordert.
        </p>
        <ul v-else class="list">
          <li v-for="cell in required" :key="cell.certification_id" class="list-item status-row">
            <StatusPeg
              :status="cell.status"
              :label="pegLabel(cell.certification_id)"
            />
            <div class="grow">
              <strong>{{ certById.get(cell.certification_id)?.name }}</strong>
              <div class="small muted">
                {{ STATUS_LABEL[cell.status] }}
                <template v-if="cell.completed_on"> · zuletzt {{ formatDate(cell.completed_on) }}</template>
                <template v-if="cell.status !== 'missing'"> · {{ cellHint(cell.status, cell.expires_on, today) }}</template>
              </div>
            </div>
            <button class="secondary" @click="completionDialog?.open(cell.certification_id)">Eintragen</button>
          </li>
        </ul>
      </section>

      <section v-if="optional.length">
        <h2>Weitere Nachweise</h2>
        <ul class="list">
          <li v-for="cell in optional" :key="cell.certification_id" class="list-item status-row">
            <div class="grow">
              <strong>{{ certById.get(cell.certification_id)?.name }}</strong>
              <div class="small muted">
                zuletzt {{ formatDate(cell.completed_on) }}
                <template v-if="cell.expires_on"> · gültig bis {{ formatDate(cell.expires_on) }}</template>
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section>
        <h2>Verlauf</h2>
        <p v-if="detail.history.length === 0" class="muted">Noch keine Abschlüsse eingetragen.</p>
        <ul v-else class="list">
          <li v-for="h in detail.history" :key="h.id" class="list-item history">
            <div class="grow">
              <strong>{{ h.certification_name }}</strong>
              <div class="small">
                {{ formatDate(h.completed_on) }} ·
                {{ h.expires_on ? `gültig bis ${formatDate(h.expires_on)}` : "unbefristet" }}
              </div>
              <div v-if="h.note" class="small note">{{ h.note }}</div>
              <div class="small muted">
                {{ KIND_LABEL[certById.get(h.certification_id)?.kind ?? "test"] }} · eingetragen von
                {{ h.recorded_by ?? "unbekannt" }} am {{ formatDate(h.recorded_at) }}
              </div>
            </div>
            <button v-if="canDelete(h)" class="link" @click="remove(h)">Löschen</button>
          </li>
        </ul>
      </section>

      <section>
        <details class="audit" @toggle="showAudit = ($event.target as HTMLDetailsElement).open">
          <summary><h2>Änderungen</h2></summary>
          <AuditList v-if="showAudit" ref="auditList" :source="`/api/members/${detail.member.id}/audit`" />
        </details>
      </section>

      <MemberDialog ref="memberDialog" :member="detail.member" :positions="positions" @saved="reloadAll" />
      <CompletionDialog
        ref="completionDialog"
        :member-id="detail.member.id"
        :certifications="certifications"
        @saved="reloadAll"
      />
    </template>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 0.75rem;
}
.head {
  align-items: flex-start;
  margin-bottom: 1rem;
}
.head h1 {
  margin-bottom: 0.25rem;
}
section {
  margin-top: 2rem;
}
.grow {
  flex: 1 1 auto;
  min-width: 0;
}
.status-row button {
  min-height: 2.25rem;
  padding: 0.3rem 0.7rem;
  flex-shrink: 0;
}
.audit summary {
  cursor: pointer;
  list-style-position: outside;
  margin-left: 1rem;
}
.audit summary h2 {
  display: inline;
}
.history {
  align-items: flex-start;
}
.note {
  white-space: pre-line;
  margin: 0.15rem 0;
}
</style>
