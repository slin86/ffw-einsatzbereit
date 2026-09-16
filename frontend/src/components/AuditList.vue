<script setup lang="ts">
import { ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { api, errorText } from "../api";
import { actionText, changeLines, ENTITY_LABEL, type AuditEntry, type AuditPage } from "../auditText";
import { formatDateTime } from "../labels";

/** Paged change log. `source` is the API path without paging parameters. */
const props = defineProps<{ source: string; showEntity?: boolean }>();

const entries = ref<AuditEntry[]>([]);
const nextBefore = ref<number | null>(null);
const loading = ref(false);
const error = ref("");

async function fetchPage(beforeId: number | null): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const sep = props.source.includes("?") ? "&" : "?";
    const page = await api<AuditPage>(beforeId === null ? props.source : `${props.source}${sep}before_id=${beforeId}`);
    entries.value = beforeId === null ? page.entries : [...entries.value, ...page.entries];
    nextBefore.value = page.next_before_id;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.source,
  () => fetchPage(null),
  { immediate: true },
);

defineExpose({ reload: () => fetchPage(null) });
</script>

<template>
  <div>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="!loading && entries.length === 0 && !error" class="muted">Keine Änderungen gefunden.</p>
    <ol v-if="entries.length" class="list log">
      <li v-for="e in entries" :key="e.id" class="entry" :class="e.action">
        <div class="head">
          <strong>{{ actionText(e) }}</strong>
          <span class="muted small">{{ formatDateTime(e.at) }} · {{ e.user_name }}</span>
        </div>
        <div v-if="showEntity" class="small">
          <span class="tag">{{ ENTITY_LABEL[e.entity_type] }}</span>
          <RouterLink v-if="e.member_id !== null" :to="`/kameraden/${e.member_id}`">{{ e.entity_label }}</RouterLink>
          <template v-else>{{ e.entity_label }}</template>
        </div>
        <ul class="changes small">
          <li v-for="line in changeLines(e)" :key="line.field">{{ line.text }}</li>
        </ul>
      </li>
    </ol>
    <button v-if="nextBefore !== null" class="secondary more" :disabled="loading" @click="fetchPage(nextBefore)">
      Ältere Einträge laden
    </button>
  </div>
</template>

<style scoped>
.entry {
  padding: 0.75rem 1rem;
  border-left: 4px solid var(--line);
  display: grid;
  gap: 0.2rem;
}
.entry.create {
  border-left-color: var(--ok);
}
.entry.delete {
  border-left-color: var(--bad);
}
.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.25rem 1rem;
}
.tag {
  margin-right: 0.4rem;
}
.changes {
  margin: 0.2rem 0 0;
  padding-left: 1.1rem;
  color: var(--muted);
  overflow-wrap: anywhere;
}
.more {
  margin-top: 0.75rem;
}
</style>
