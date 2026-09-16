<script setup lang="ts">
import { computed } from "vue";

import { STATUS_LABEL } from "../labels";
import type { CellStatus } from "../types";

const props = defineProps<{ counts: Record<CellStatus, number> }>();
const order: CellStatus[] = ["valid", "expiring", "expired", "missing"];
const total = computed(() => order.reduce((sum, s) => sum + props.counts[s], 0));
</script>

<template>
  <div v-if="total > 0" class="counts">
    <div class="bar" role="img" :aria-label="order.map((s) => `${STATUS_LABEL[s]}: ${counts[s]}`).join(', ')">
      <span v-for="s in order" :key="s" :class="s" :style="{ flexGrow: counts[s] }"></span>
    </div>
    <ul class="legend">
      <li v-for="s in order" :key="s">
        <span class="dot" :class="s"></span>
        <strong>{{ counts[s] }}</strong> {{ STATUS_LABEL[s] }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.bar {
  display: flex;
  height: 0.75rem;
  border-radius: 999px;
  overflow: hidden;
  gap: 2px;
  background: var(--line);
}
.bar span {
  flex-basis: 0;
}
.legend {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.25rem;
  font-size: var(--fs-s);
}
.dot {
  display: inline-block;
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 2px;
  margin-right: 0.3rem;
  vertical-align: -1px;
}
.valid {
  background: var(--ok);
}
.expiring {
  background: var(--warn);
}
.expired {
  background: var(--bad);
}
.missing {
  background: var(--bad-soft);
  box-shadow: inset 0 0 0 2px var(--bad);
}
</style>
