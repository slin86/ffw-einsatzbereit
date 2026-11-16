<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

import { buzz } from "../toast";

const props = defineProps<{ refresh: () => Promise<unknown> }>();

const THRESHOLD = 70;
const pull = ref(0);
const busy = ref(false);
let startY: number | null = null;
let armed = false;

function onStart(e: TouchEvent): void {
  if (busy.value || window.scrollY > 0 || document.querySelector("dialog[open]")) return;
  startY = e.touches[0]!.clientY;
}

/** Follows the finger with resistance, so the indicator moves slower than the finger. */
function onMove(e: TouchEvent): void {
  if (startY === null) return;
  const dy = e.touches[0]!.clientY - startY;
  if (dy <= 0 || window.scrollY > 0) {
    pull.value = 0;
    return;
  }
  pull.value = Math.min(110, dy * 0.45);
  if (pull.value >= THRESHOLD && !armed) {
    armed = true;
    buzz(8);
  } else if (pull.value < THRESHOLD) armed = false;
}

async function onEnd(): Promise<void> {
  if (startY === null) return;
  startY = null;
  armed = false;
  if (pull.value < THRESHOLD) {
    pull.value = 0;
    return;
  }
  busy.value = true;
  pull.value = 48;
  try {
    await props.refresh();
  } finally {
    busy.value = false;
    pull.value = 0;
  }
}

onMounted(() => {
  window.addEventListener("touchstart", onStart, { passive: true });
  window.addEventListener("touchmove", onMove, { passive: true });
  window.addEventListener("touchend", onEnd);
});
onBeforeUnmount(() => {
  window.removeEventListener("touchstart", onStart);
  window.removeEventListener("touchmove", onMove);
  window.removeEventListener("touchend", onEnd);
});
</script>

<template>
  <div
    class="ptr"
    :class="{ busy, ready: pull >= THRESHOLD }"
    :style="{ height: `${pull}px` }"
    role="status"
    :aria-label="busy ? 'Wird aktualisiert' : undefined"
  >
    <span
      class="spinner"
      :style="{ transform: `rotate(${pull * 4}deg)`, opacity: Math.min(1, pull / THRESHOLD) }"
    ></span>
  </div>
</template>

<style scoped>
.ptr {
  display: grid;
  place-items: center;
  overflow: hidden;
  transition: height 0.2s;
}
.spinner {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  border: 2.5px solid var(--line);
  border-top-color: var(--brand);
}
.ready .spinner {
  border-top-color: var(--ok);
}
.busy .spinner {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
