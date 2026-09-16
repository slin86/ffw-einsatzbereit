<script setup lang="ts">
import { computed } from "vue";

import { STATUS_LABEL } from "../labels";
import type { CellStatus } from "../types";

const props = defineProps<{ status: CellStatus; label: string; title?: string; required?: boolean }>();
const tooltip = computed(() => `${props.title ?? props.label}: ${STATUS_LABEL[props.status]}`);
</script>

<template>
  <span class="peg" :class="[status, { optional: required === false }]" :title="tooltip">
    <span class="code">{{ label }}</span>
    <span class="sr-only">{{ STATUS_LABEL[status] }}</span>
  </span>
</template>

<style scoped>
.peg {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.6rem;
  height: 1.7rem;
  padding: 0 0.35rem;
  border-radius: 4px;
  font-family: var(--font-cond);
  font-weight: 600;
  font-size: 0.85rem;
  line-height: 1;
  border: 2px solid transparent;
  white-space: nowrap;
}
.valid {
  background: var(--ok);
  color: #fff;
}
.expiring {
  background: var(--warn);
  color: #2a1f00;
}
.expired {
  background: var(--bad);
  color: #fff;
}
/* Missing = empty socket: same red, but hollow, so it reads differently from "expired". */
.missing {
  background: var(--bad-soft);
  border-color: var(--bad);
  border-style: dashed;
  color: var(--bad-ink);
}
.not_required {
  background: var(--none);
  color: var(--none-ink);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
</style>
