<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import type { MatrixRow } from "../../types";
import { initials, memberState, type MemberState } from "../readiness";

const props = defineProps<{ rows: MatrixRow[] | null }>();

const ORDER: Record<MemberState, number> = { ready: 0, soon: 1, critical: 2 };
const LABEL: Record<MemberState, string> = {
  ready: "einsatzbereit",
  soon: "einsatzbereit, bald fällig",
  critical: "nicht einsatzbereit",
};

/** Ready members first, so the board reads like a filling bar and every peg still stands for one person. */
const pegs = computed(() =>
  (props.rows ?? [])
    .map((r) => ({ row: r, state: memberState(r) }))
    .sort(
      (a, b) => ORDER[a.state] - ORDER[b.state] || a.row.member.last_name.localeCompare(b.row.member.last_name, "de"),
    ),
);
</script>

<template>
  <div v-if="rows === null" class="board loading" aria-hidden="true">
    <span v-for="i in 30" :key="i" class="peg"></span>
  </div>
  <ul v-else class="board" aria-label="Stärke nach Kamerad">
    <li v-for="p in pegs" :key="p.row.member.id">
      <RouterLink
        :to="`/kameraden/${p.row.member.id}`"
        class="peg"
        :class="p.state"
        :aria-label="`${p.row.member.first_name} ${p.row.member.last_name}, ${LABEL[p.state]}`"
      >
        {{ initials(p.row.member) }}
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.board {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(2.15rem, 1fr));
  gap: 5px;
}
.peg {
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  border-radius: 5px;
  font-family: var(--font-cond);
  font-weight: 600;
  font-size: 0.8rem;
  letter-spacing: 0.02em;
  text-decoration: none;
  color: #fff;
  background: var(--ok);
  box-shadow: inset 0 -3px 0 rgb(0 0 0 / 0.18);
  transition: transform 0.12s;
}
.peg:active {
  transform: scale(0.9);
}
.peg.soon {
  background: var(--warn);
  color: #2a1f00;
}
.peg.critical {
  background: transparent;
  color: var(--bad-ink);
  box-shadow: inset 0 0 0 2px var(--bad);
}
.loading .peg {
  background: var(--line);
  box-shadow: none;
  animation: pulse 1.2s ease-in-out infinite alternate;
}
@keyframes pulse {
  to {
    opacity: 0.45;
  }
}
</style>
