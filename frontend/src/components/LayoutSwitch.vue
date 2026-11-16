<script setup lang="ts">
import { ref } from "vue";

import { type LayoutChoice, readLayoutChoice, writeLayoutChoice } from "../layout";

const choice = ref<LayoutChoice>(readLayoutChoice());

const OPTIONS: { value: LayoutChoice; label: string }[] = [
  { value: "auto", label: "Automatisch" },
  { value: "mobile", label: "Handy" },
  { value: "desktop", label: "Desktop" },
];

/** Stores the choice and reloads, because the layout is chosen once when the app starts. */
function pick(value: LayoutChoice): void {
  if (value === choice.value) return;
  choice.value = value;
  writeLayoutChoice(value);
  window.location.reload();
}
</script>

<template>
  <div class="layout-switch" role="radiogroup" aria-label="Ansicht">
    <button
      v-for="o in OPTIONS"
      :key="o.value"
      type="button"
      role="radio"
      class="secondary"
      :aria-checked="choice === o.value"
      @click="pick(o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<style scoped>
.layout-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem;
}
.layout-switch button[aria-checked="true"] {
  background: var(--brand);
  border-color: var(--brand);
  color: var(--brand-ink);
}
</style>
