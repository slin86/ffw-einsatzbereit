<script setup lang="ts">
import { computed } from "vue";

import { PAGE_SIZES, pageRange } from "../paging";

const props = defineProps<{ total: number; page: number; count: number; size: number }>();
const emit = defineEmits<{ "update:page": [page: number]; "update:size": [size: number] }>();

const range = computed(() => pageRange(props.page, props.total, props.size));
const visible = computed(() => props.total > Math.min(...PAGE_SIZES.filter((s) => s > 0)));

function onSize(event: Event): void {
  emit("update:size", Number((event.target as HTMLSelectElement).value));
}
</script>

<template>
  <nav v-if="visible" class="pager" aria-label="Seiten">
    <label class="size">
      Pro Seite
      <select :value="size" @change="onSize">
        <option v-for="s in PAGE_SIZES" :key="s" :value="s">{{ s === 0 ? "Alle" : s }}</option>
      </select>
    </label>
    <span class="range muted small" role="status">{{ range[0] }}–{{ range[1] }} von {{ total }}</span>
    <div v-if="count > 1" class="row steps">
      <button type="button" class="secondary" :disabled="page <= 1" @click="emit('update:page', page - 1)">
        Zurück
      </button>
      <span class="small">Seite {{ page }} von {{ count }}</span>
      <button type="button" class="secondary" :disabled="page >= count" @click="emit('update:page', page + 1)">
        Weiter
      </button>
    </div>
  </nav>
</template>

<style scoped>
.pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  margin-top: 1rem;
}
.size {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.size select {
  width: auto;
}
.steps {
  gap: 0.75rem;
}
</style>
