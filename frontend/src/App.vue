<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { logout, session } from "./session";

const route = useRoute();
const router = useRouter();
const showChrome = computed(() => !route.meta.public && session.user !== null);
const isAdmin = computed(() => session.user?.role === "admin");

async function doLogout(): Promise<void> {
  await logout();
  await router.push("/login");
}
</script>

<template>
  <header v-if="showChrome" class="topbar">
    <RouterLink to="/" class="brand">Einsatzbereit</RouterLink>
    <nav class="topnav" aria-label="Hauptnavigation">
      <RouterLink to="/">Offen</RouterLink>
      <RouterLink to="/uebersicht">Übersicht</RouterLink>
      <RouterLink to="/erfassen">Erfassen</RouterLink>
      <RouterLink to="/kameraden">Kameraden</RouterLink>
      <template v-if="isAdmin">
        <span class="sep" aria-hidden="true"></span>
        <RouterLink to="/admin/nachweise">Nachweise</RouterLink>
        <RouterLink to="/admin/funktionen">Funktionen</RouterLink>
        <RouterLink to="/admin/benutzer">Benutzer</RouterLink>
        <RouterLink to="/admin/protokoll">Protokoll</RouterLink>
      </template>
    </nav>
    <div class="account">
      <RouterLink to="/konto" class="who">{{ session.user?.display_name }}</RouterLink>
      <button class="secondary logout" @click="doLogout">Abmelden</button>
    </div>
  </header>

  <main>
    <RouterView v-if="session.ready" />
  </main>

  <nav v-if="showChrome" class="tabbar" aria-label="Hauptnavigation">
    <RouterLink to="/">Offen</RouterLink>
    <RouterLink to="/uebersicht">Übersicht</RouterLink>
    <RouterLink to="/erfassen">Erfassen</RouterLink>
    <RouterLink to="/kameraden">Kameraden</RouterLink>
    <RouterLink to="/konto">Konto</RouterLink>
  </nav>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0 1rem;
  min-height: 3.5rem;
  background: var(--brand);
  color: var(--brand-ink);
  position: sticky;
  top: 0;
  z-index: 10;
  padding-top: env(safe-area-inset-top);
}
.brand {
  font-family: var(--font-cond);
  font-weight: 700;
  font-size: var(--fs-l);
  color: inherit;
  text-decoration: none;
}
.topnav {
  display: flex;
  gap: 0.25rem;
  align-items: stretch;
  flex: 1;
  align-self: stretch;
}
.topnav a,
.who {
  color: rgb(255 255 255 / 0.78);
  text-decoration: none;
  display: flex;
  align-items: center;
  padding: 0 0.6rem;
  font-weight: 500;
  border-bottom: 3px solid transparent;
}
.topnav a.router-link-exact-active,
.topnav a[aria-current="page"] {
  color: #fff;
  border-bottom-color: #fff;
}
.sep {
  width: 1px;
  background: rgb(255 255 255 / 0.25);
  margin: 0.9rem 0.4rem;
}
.account {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.logout {
  min-height: 2.25rem;
  padding: 0.3rem 0.8rem;
}

.tabbar {
  display: none;
}

@media (max-width: 760px) {
  .topnav,
  .account {
    display: none;
  }
  .topbar {
    min-height: 3rem;
  }
  .tabbar {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    position: fixed;
    inset: auto 0 0 0;
    background: var(--surface);
    border-top: 1px solid var(--line);
    padding-bottom: env(safe-area-inset-bottom);
    z-index: 10;
  }
  .tabbar a {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 3.5rem;
    color: var(--muted);
    text-decoration: none;
    font-weight: 600;
    font-size: var(--fs-s);
    border-top: 3px solid transparent;
  }
  .tabbar a.router-link-exact-active {
    color: var(--brand);
    border-top-color: var(--brand);
  }
}
@media (max-width: 760px) and (prefers-color-scheme: dark) {
  .tabbar a.router-link-exact-active {
    color: var(--ink);
    border-top-color: var(--ink);
  }
}
</style>
