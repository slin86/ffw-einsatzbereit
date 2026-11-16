<script setup lang="ts" generic="T extends string">
defineProps<{ options: { value: T; label: string; count?: number }[]; modelValue: T; label: string }>();
defineEmits<{ "update:modelValue": [value: T] }>();
</script>

<template>
  <div class="segmented" role="radiogroup" :aria-label="label">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === o.value"
      @click="$emit('update:modelValue', o.value)"
    >
      {{ o.label }}<span v-if="o.count !== undefined" class="count">{{ o.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 2px;
  padding: 3px;
  border-radius: 10px;
  background: var(--seg-track);
}
button {
  min-height: 2.25rem;
  padding: 0.3rem 0.4rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ink);
  font-weight: 500;
  font-size: 0.92rem;
  gap: 0.35rem;
}
button[aria-checked="true"] {
  background: var(--surface);
  font-weight: 600;
  box-shadow: 0 1px 3px rgb(10 20 30 / 0.16);
}
.count {
  font-family: var(--font-cond);
  font-weight: 600;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
</style>
