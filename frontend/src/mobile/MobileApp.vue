<script setup lang="ts">
import "./mobile.css";

import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { session } from "../session";
import MIcon, { type IconName } from "./components/MIcon.vue";
import { dismiss, toasts } from "./toast";

const route = useRoute();
const router = useRouter();

const signedIn = computed(() => !route.meta.public && session.user !== null);
const showTabs = computed(() => signedIn.value && !route.meta.immersive);
const showBackBar = computed(() => signedIn.value && route.meta.reused);

const TABS: { tab: "lage" | "nachweise" | "kameraden" | "mehr"; to: string; label: string; icon: IconName }[] = [
  { tab: "lage", to: "/", label: "Lage", icon: "board" },
  { tab: "nachweise", to: "/uebersicht", label: "Nachweise", icon: "badge" },
  { tab: "kameraden", to: "/kameraden", label: "Kameraden", icon: "people" },
  { tab: "mehr", to: "/mehr", label: "Mehr", icon: "more" },
];

function goBack(): void {
  if (window.history.state?.back) router.back();
  else void router.push(route.meta.back ?? "/");
}

/** A second tap on the active tab scrolls to the top, like in native apps. */
function onTab(tab: string): void {
  if (route.meta.tab === tab) window.scrollTo({ top: 0, behavior: "smooth" });
}
</script>

<template>
  <div class="m-app" :class="{ 'has-tabs': showTabs }">
    <header v-if="showBackBar" class="backbar">
      <button type="button" class="icon-btn back" @click="goBack">
        <MIcon name="back" />
        <span>{{ route.meta.back === "/mehr" ? "Mehr" : "Zurück" }}</span>
      </button>
    </header>

    <main :class="{ reused: route.meta.reused }">
      <RouterView v-if="session.ready" v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>

    <nav v-if="showTabs" class="tabbar" aria-label="Hauptnavigation">
      <RouterLink
        v-for="t in TABS.slice(0, 2)"
        :key="t.tab"
        :to="t.to"
        class="tab"
        :class="{ active: route.meta.tab === t.tab }"
        :aria-current="route.meta.tab === t.tab ? 'page' : undefined"
        @click="onTab(t.tab)"
      >
        <MIcon :name="t.icon" />
        <span>{{ t.label }}</span>
      </RouterLink>
      <RouterLink to="/erfassen" class="tab record" aria-label="Erfassen">
        <span class="record-btn"><MIcon name="plus" :size="28" /></span>
        <span>Erfassen</span>
      </RouterLink>
      <RouterLink
        v-for="t in TABS.slice(2)"
        :key="t.tab"
        :to="t.to"
        class="tab"
        :class="{ active: route.meta.tab === t.tab }"
        :aria-current="route.meta.tab === t.tab ? 'page' : undefined"
        @click="onTab(t.tab)"
      >
        <MIcon :name="t.icon" />
        <span>{{ t.label }}</span>
      </RouterLink>
    </nav>

    <div class="toasts" aria-live="polite">
      <TransitionGroup name="toast">
        <button v-for="t in toasts" :key="t.id" type="button" class="toast" :class="t.kind" @click="dismiss(t.id)">
          <MIcon :name="t.kind === 'ok' ? 'check' : 'close'" :size="18" />
          <span>{{ t.text }}</span>
        </button>
      </TransitionGroup>
    </div>
  </div>
</template>
