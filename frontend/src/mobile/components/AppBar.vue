<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import MIcon from "./MIcon.vue";

const props = defineProps<{ title: string; subtitle?: string; back?: string; noBack?: boolean; backLabel?: string }>();

const route = useRoute();
const router = useRouter();
const heading = ref<HTMLElement | null>(null);
const compact = ref(false);
let observer: IntersectionObserver | null = null;

onMounted(() => {
  if (!heading.value || typeof IntersectionObserver === "undefined") return;
  observer = new IntersectionObserver(([e]) => (compact.value = !e!.isIntersecting), {
    rootMargin: "-56px 0px 0px 0px",
  });
  observer.observe(heading.value);
});
onBeforeUnmount(() => observer?.disconnect());

const backTarget = () => (props.noBack ? undefined : (props.back ?? route.meta.back));

/** Goes back in the history when the user came from inside the app, otherwise to the parent page. */
function goBack(): void {
  if (window.history.state?.back) router.back();
  else void router.push(backTarget() ?? "/");
}
</script>

<template>
  <header class="appbar" :class="{ compact }">
    <button v-if="backTarget()" type="button" class="icon-btn back" @click="goBack">
      <MIcon name="back" />
      <span>{{ backLabel ?? "Zurück" }}</span>
    </button>
    <span class="bar-title" :aria-hidden="!compact">{{ title }}</span>
    <div class="actions"><slot name="actions" /></div>
  </header>
  <div class="large-title">
    <h1 ref="heading">{{ title }}</h1>
    <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    <slot />
  </div>
</template>

<style scoped>
.appbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  min-height: calc(3.25rem + env(safe-area-inset-top));
  padding: env(safe-area-inset-top) 0.5rem 0;
  background: color-mix(in srgb, var(--paper) 86%, transparent);
  backdrop-filter: saturate(1.6) blur(14px);
  -webkit-backdrop-filter: saturate(1.6) blur(14px);
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}
.appbar.compact {
  border-bottom-color: var(--line);
}
.back {
  grid-column: 1;
  justify-self: start;
  gap: 0.1rem;
  padding-right: 0.6rem;
  color: var(--focus);
  font-weight: 500;
  width: auto;
}
.back span {
  max-width: 8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-title {
  grid-column: 2;
  font-family: var(--font-cond);
  font-weight: 700;
  font-size: 1.15rem;
  opacity: 0;
  transform: translateY(4px);
  transition:
    opacity 0.2s,
    transform 0.2s;
  max-width: 55vw;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compact .bar-title {
  opacity: 1;
  transform: none;
}
.actions {
  grid-column: 3;
  justify-self: end;
  display: flex;
  gap: 0.25rem;
}
.large-title {
  padding: 0.25rem 1.25rem 0.75rem;
}
.large-title h1 {
  font-size: 2.35rem;
  margin: 0;
  letter-spacing: -0.01em;
}
.subtitle {
  margin: 0.2rem 0 0;
  color: var(--muted);
}
</style>
