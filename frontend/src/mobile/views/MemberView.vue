<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { api, errorText } from "../../api";
import AuditList from "../../components/AuditList.vue";
import DeleteMembersDialog from "../../components/DeleteMembersDialog.vue";
import MemberDialog from "../../components/MemberDialog.vue";
import { formatDate, KIND_LABEL } from "../../labels";
import { session } from "../../session";
import type { Certification, Completion, MemberDetail, Position } from "../../types";
import AppBar from "../components/AppBar.vue";
import BottomSheet from "../components/BottomSheet.vue";
import MIcon from "../components/MIcon.vue";
import PullRefresh from "../components/PullRefresh.vue";
import QuickRecordSheet from "../components/QuickRecordSheet.vue";
import SegmentedControl from "../components/SegmentedControl.vue";
import { dueText, isCritical } from "../readiness";
import { toast } from "../toast";

const props = defineProps<{ id: number }>();
const router = useRouter();

const detail = ref<MemberDetail | null>(null);
const certifications = ref<Certification[]>([]);
const positions = ref<Position[]>([]);
const error = ref("");
const tab = ref<"certs" | "history" | "log">("certs");
const entry = ref<Completion | null>(null);
const confirmDelete = ref(false);

const quick = ref<InstanceType<typeof QuickRecordSheet> | null>(null);
const actions = ref<InstanceType<typeof BottomSheet> | null>(null);
const entrySheet = ref<InstanceType<typeof BottomSheet> | null>(null);
const memberDialog = ref<InstanceType<typeof MemberDialog> | null>(null);
const deleteDialog = ref<InstanceType<typeof DeleteMembersDialog> | null>(null);
const auditList = ref<InstanceType<typeof AuditList> | null>(null);
const isAdmin = computed(() => session.user?.role === "admin");
const today = new Date().toLocaleDateString("sv-SE");

async function load(): Promise<void> {
  error.value = "";
  try {
    detail.value = await api<MemberDetail>(`/api/members/${props.id}`);
    auditList.value?.reload();
  } catch (e) {
    error.value = errorText(e);
  }
}

onMounted(async () => {
  const [c, p] = await Promise.all([
    api<Certification[]>("/api/certifications").catch(() => []),
    api<Position[]>("/api/positions").catch(() => []),
  ]);
  certifications.value = c.filter((x) => x.is_active);
  positions.value = p;
});
watch(() => props.id, load, { immediate: true });

const certName = (id: number) => certifications.value.find((c) => c.id === id)?.name ?? "";
const required = computed(() => detail.value?.cells.filter((c) => c.required) ?? []);
const optional = computed(() => detail.value?.cells.filter((c) => !c.required && c.completed_on) ?? []);
const critical = computed(() => required.value.filter((c) => isCritical(c.status)).length);
const soon = computed(() => required.value.filter((c) => c.status === "expiring").length);

const subtitle = computed(() => {
  const m = detail.value?.member;
  if (!m) return undefined;
  const parts = [`Nr ${m.number}`, ...m.positions.map((p) => p.name)];
  if (!m.is_active) parts.push("inaktiv");
  return parts.join(", ");
});

const banner = computed(() => {
  if (!detail.value) return null;
  if (!detail.value.member.is_active) return { kind: "off", text: "Inaktiv, erscheint nicht in der Lage." };
  if (required.value.length === 0) return { kind: "off", text: "Über die Funktionen ist nichts gefordert." };
  if (critical.value)
    return {
      kind: "critical",
      text: `Nicht einsatzbereit, ${critical.value === 1 ? "1 Nachweis fehlt oder ist" : `${critical.value} Nachweise fehlen oder sind`} abgelaufen.`,
    };
  if (soon.value)
    return {
      kind: "soon",
      text: `Einsatzbereit, ${soon.value === 1 ? "1 Nachweis läuft" : `${soon.value} laufen`} bald ab.`,
    };
  return { kind: "ready", text: "Einsatzbereit, alles gültig." };
});

/** Mirrors the backend rule. Admins may delete every entry, other users only their own. */
function canDelete(h: Completion): boolean {
  return isAdmin.value || h.recorded_by_id === session.user?.id;
}

function openEntry(h: Completion): void {
  entry.value = h;
  confirmDelete.value = false;
  entrySheet.value?.open();
}

async function removeEntry(): Promise<void> {
  if (!entry.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    return;
  }
  try {
    await api(`/api/completions/${entry.value.id}`, "DELETE");
    entrySheet.value?.close();
    toast("Eintrag gelöscht");
    await load();
  } catch (e) {
    toast(errorText(e), "error");
  }
}

function edit(): void {
  actions.value?.close();
  memberDialog.value?.open();
}

function askDelete(): void {
  actions.value?.close();
  if (detail.value) deleteDialog.value?.open([detail.value.member]);
}

async function onDeleted(): Promise<void> {
  toast("Kamerad gelöscht");
  await router.replace("/kameraden");
}

async function onSaved(): Promise<void> {
  toast("Gespeichert");
  await load();
}
</script>

<template>
  <PullRefresh :refresh="load" />
  <AppBar
    :title="detail ? `${detail.member.first_name} ${detail.member.last_name}` : 'Kamerad'"
    :subtitle="subtitle"
    back-label="Kameraden"
  >
    <template #actions>
      <button v-if="detail" type="button" class="icon-btn" aria-label="Aktionen" @click="actions?.open()">
        <MIcon name="edit" />
      </button>
    </template>
    <p v-if="banner" class="banner" :class="banner.kind">{{ banner.text }}</p>
    <button v-if="detail" type="button" class="big record" @click="quick?.open(detail.member)">
      <MIcon name="plus" :size="20" /> Abschluss eintragen
    </button>
  </AppBar>

  <p v-if="error" class="error pad" role="alert">{{ error }}</p>

  <div v-if="detail" class="section">
    <SegmentedControl
      v-model="tab"
      label="Ansicht"
      :options="[
        { value: 'certs', label: 'Nachweise' },
        { value: 'history', label: 'Verlauf', count: detail.history.length },
        { value: 'log', label: 'Änderungen' },
      ]"
    />

    <template v-if="tab === 'certs'">
      <p class="group-label">Gefordert über die Funktionen</p>
      <p v-if="required.length === 0" class="empty small-empty">Keine Nachweise gefordert.</p>
      <ul v-else class="group">
        <li v-for="c in required" :key="c.certification_id">
          <button type="button" class="cell" @click="quick?.open(detail.member, c.certification_id)">
            <span class="mark" :class="c.status" aria-hidden="true"></span>
            <span class="cell-main">
              <strong>{{ certName(c.certification_id) }}</strong>
              <span class="cell-sub" :class="c.status">{{ dueText(c, today) }}</span>
            </span>
            <span class="cell-end add">Eintragen</span>
          </button>
        </li>
      </ul>
      <template v-if="optional.length">
        <p class="group-label">Weitere Nachweise</p>
        <ul class="group">
          <li v-for="c in optional" :key="c.certification_id">
            <button type="button" class="cell" @click="quick?.open(detail.member, c.certification_id)">
              <span class="cell-main">
                <strong>{{ certName(c.certification_id) }}</strong>
                <span class="cell-sub">
                  Zuletzt {{ formatDate(c.completed_on)
                  }}<template v-if="c.expires_on">, gültig bis {{ formatDate(c.expires_on) }}</template>
                </span>
              </span>
            </button>
          </li>
        </ul>
      </template>
    </template>

    <template v-else-if="tab === 'history'">
      <p v-if="detail.history.length === 0" class="empty">
        <strong>Noch nichts eingetragen</strong>
        Abschlüsse erscheinen hier mit Datum und wer sie eingetragen hat.
      </p>
      <ol v-else class="timeline">
        <li v-for="h in detail.history" :key="h.id">
          <button type="button" class="cell" @click="openEntry(h)">
            <span class="cell-main">
              <strong>{{ h.certification_name }}</strong>
              <span class="cell-sub">
                {{ formatDate(h.completed_on) }},
                {{ h.expires_on ? `gültig bis ${formatDate(h.expires_on)}` : "unbefristet" }}
              </span>
              <span v-if="h.note" class="note">{{ h.note }}</span>
            </span>
            <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
          </button>
        </li>
      </ol>
    </template>

    <div v-else class="log">
      <AuditList ref="auditList" :source="`/api/members/${detail.member.id}/audit`" />
    </div>
  </div>

  <template v-if="detail">
    <QuickRecordSheet ref="quick" :certifications="certifications" @saved="load" />

    <BottomSheet ref="actions" :title="`${detail.member.first_name} ${detail.member.last_name}`">
      <ul class="group sheet-group">
        <li>
          <button type="button" class="cell" @click="edit">
            <span class="cell-icon"><MIcon name="edit" :size="18" /></span>
            <span class="cell-main"
              ><strong>Bearbeiten</strong><span class="cell-sub">Name, Funktionen, aktiv</span></span
            >
          </button>
        </li>
        <li v-if="isAdmin">
          <button type="button" class="cell danger-text" @click="askDelete">
            <span class="cell-icon del"><MIcon name="trash" :size="18" /></span>
            <span class="cell-main"><strong>Löschen</strong><span class="cell-sub">Mit allen Abschlüssen</span></span>
          </button>
        </li>
      </ul>
    </BottomSheet>

    <BottomSheet
      ref="entrySheet"
      :title="entry?.certification_name"
      :subtitle="entry ? formatDate(entry.completed_on) : ''"
    >
      <dl v-if="entry" class="facts">
        <div>
          <dt>Gültig bis</dt>
          <dd>{{ entry.expires_on ? formatDate(entry.expires_on) : "Unbefristet" }}</dd>
        </div>
        <div>
          <dt>Art</dt>
          <dd>{{ KIND_LABEL[certifications.find((c) => c.id === entry!.certification_id)?.kind ?? "test"] }}</dd>
        </div>
        <div>
          <dt>Eingetragen</dt>
          <dd>{{ entry.recorded_by ?? "Unbekannt" }}, {{ formatDate(entry.recorded_at) }}</dd>
        </div>
        <div v-if="entry.note">
          <dt>Bemerkung</dt>
          <dd class="note">{{ entry.note }}</dd>
        </div>
      </dl>
      <template #footer>
        <button v-if="entry && canDelete(entry)" type="button" class="danger big" @click="removeEntry">
          {{ confirmDelete ? "Wirklich löschen" : "Eintrag löschen" }}
        </button>
      </template>
    </BottomSheet>

    <MemberDialog ref="memberDialog" :member="detail.member" :positions="positions" @saved="onSaved" />
    <DeleteMembersDialog ref="deleteDialog" @deleted="onDeleted" />
  </template>
</template>

<style scoped>
.banner {
  margin: 0.75rem 0 0;
  padding: 0.7rem 0.9rem;
  border-radius: 12px;
  font-weight: 500;
  background: var(--ok-soft);
  color: var(--ok-ink);
}
.banner.soon {
  background: var(--warn-soft);
  color: var(--warn-ink);
}
.banner.critical {
  background: var(--bad-soft);
  color: var(--bad-ink);
}
.banner.off {
  background: var(--none);
  color: var(--none-ink);
}
.record {
  margin-top: 0.75rem;
}
.pad {
  margin: 0.5rem var(--pad);
}
.section {
  margin-top: 0.75rem;
}
.mark {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 3px;
  flex-shrink: 0;
  background: var(--ok);
}
.mark.expiring {
  background: var(--warn);
}
.mark.expired {
  background: var(--bad);
}
.mark.missing {
  background: transparent;
  box-shadow: inset 0 0 0 2px var(--bad);
}
.cell-sub.missing,
.cell-sub.expired {
  color: var(--bad-ink);
}
.cell-sub.expiring {
  color: var(--warn-ink);
}
.add {
  color: var(--focus);
  font-weight: 600;
  font-size: 0.9rem;
}
.small-empty {
  padding: 1rem;
}
.timeline {
  list-style: none;
  margin: 0.9rem 0 0;
  padding: 0;
  background: var(--surface);
  border-radius: var(--r-group);
  overflow: hidden;
}
.timeline > li + li {
  border-top: 1px solid var(--line);
}
.note {
  white-space: pre-line;
  font-size: 0.9rem;
  margin-top: 0.15rem;
}
.log {
  margin-top: 0.9rem;
}
.log :deep(.list) {
  border: none;
  border-radius: var(--r-group);
}
.sheet-group {
  border: 1px solid var(--line);
}
.cell-icon.del {
  background: var(--bad);
}
.facts {
  margin: 0;
  display: grid;
  gap: 0.75rem;
}
.facts div {
  display: grid;
  gap: 0.1rem;
}
.facts dt {
  color: var(--muted);
  font-size: 0.88rem;
}
.facts dd {
  margin: 0;
  font-weight: 500;
}
</style>
