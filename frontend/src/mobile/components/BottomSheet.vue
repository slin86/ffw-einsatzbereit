<script setup lang="ts">
import { ref } from "vue";

import MIcon from "./MIcon.vue";

defineProps<{ title?: string; subtitle?: string }>();
const emit = defineEmits<{ closed: [] }>();

const dialog = ref<HTMLDialogElement | null>(null);
const drag = ref(0);
let startY: number | null = null;

function open(): void {
  drag.value = 0;
  dialog.value?.showModal();
}

function close(): void {
  dialog.value?.close();
}

function onDown(e: PointerEvent): void {
  if ((e.target as Element).closest("button")) return;
  startY = e.clientY;
  (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
}

function onMove(e: PointerEvent): void {
  if (startY !== null) drag.value = Math.max(0, e.clientY - startY);
}

/** Closes the sheet when it was pulled down far enough, otherwise it snaps back. */
function onUp(): void {
  if (drag.value > 90) close();
  drag.value = 0;
  startY = null;
}

/** A tap on the dimmed backdrop closes the sheet. */
function onClick(e: MouseEvent): void {
  if (e.target === dialog.value) close();
}

defineExpose({ open, close });
</script>

<template>
  <dialog
    ref="dialog"
    class="sheet"
    :style="drag ? { transform: `translateY(${drag}px)`, transition: 'none' } : undefined"
    @click="onClick"
    @close="emit('closed')"
  >
    <div class="sheet-inner">
      <header class="sheet-head" @pointerdown="onDown" @pointermove="onMove" @pointerup="onUp" @pointercancel="onUp">
        <span class="grip" aria-hidden="true"></span>
        <div v-if="title" class="titles">
          <h2>{{ title }}</h2>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <button type="button" class="icon-btn close" aria-label="Schließen" @click="close">
          <MIcon name="close" :size="20" />
        </button>
      </header>
      <div class="sheet-body">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="sheet-foot">
        <slot name="footer" />
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.sheet-inner {
  display: flex;
  flex-direction: column;
  max-height: inherit;
}
.sheet-head {
  position: relative;
  padding: 1.4rem 3.5rem 0.5rem 1.25rem;
  touch-action: none;
  cursor: grab;
}
.grip {
  position: absolute;
  top: 0.5rem;
  left: 50%;
  translate: -50% 0;
  width: 2.5rem;
  height: 0.3rem;
  border-radius: 999px;
  background: var(--line);
}
.titles h2 {
  margin: 0;
  font-size: 1.5rem;
}
.titles p {
  margin: 0.15rem 0 0;
  color: var(--muted);
}
.close {
  position: absolute;
  top: 0.9rem;
  right: 0.75rem;
}
.sheet-body {
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0.5rem 1.25rem 1.25rem;
}
.sheet-foot {
  padding: 0.75rem 1.25rem calc(0.75rem + env(safe-area-inset-bottom));
  border-top: 1px solid var(--line);
  display: grid;
  gap: 0.5rem;
}
</style>
