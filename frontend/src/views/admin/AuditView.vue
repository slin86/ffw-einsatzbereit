<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { ENTITY_LABEL, type AuditEntityType } from "../../auditText";
import AuditList from "../../components/AuditList.vue";

const entityType = ref<AuditEntityType | "">("");
const search = ref("");
const debounced = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
watch(search, (v) => {
  clearTimeout(timer);
  timer = setTimeout(() => (debounced.value = v.trim()), 300);
});

const types = Object.keys(ENTITY_LABEL) as AuditEntityType[];

const source = computed(() => {
  const params = new URLSearchParams({ limit: "50" });
  if (entityType.value) params.set("entity_type", entityType.value);
  if (debounced.value) params.set("q", debounced.value);
  return `/api/audit?${params.toString()}`;
});
</script>

<template>
  <div class="page">
    <h1>Protokoll</h1>
    <p class="lede">Wer hat wann was geändert. Neueste Einträge zuerst.</p>
    <div class="panel form-grid filters">
      <label>
        Bereich
        <select v-model="entityType">
          <option value="">Alle Bereiche</option>
          <option v-for="t in types" :key="t" :value="t">{{ ENTITY_LABEL[t] }}</option>
        </select>
      </label>
      <label>
        Suche
        <input v-model="search" type="search" placeholder="Kamerad, Nachweis oder Benutzer" />
      </label>
    </div>
    <AuditList :source="source" show-entity />
  </div>
</template>

<style scoped>
.filters {
  margin-bottom: 1rem;
}
</style>
