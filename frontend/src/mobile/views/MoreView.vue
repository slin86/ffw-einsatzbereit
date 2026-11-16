<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRouter } from "vue-router";

import LayoutSwitch from "../../components/LayoutSwitch.vue";
import { logout, session } from "../../session";
import AppBar from "../components/AppBar.vue";
import MIcon, { type IconName } from "../components/MIcon.vue";

const router = useRouter();
const user = computed(() => session.user);
const isAdmin = computed(() => user.value?.role === "admin");

const userInitials = computed(() =>
  (user.value?.display_name ?? "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase(),
);

const ADMIN: { to: string; label: string; hint: string; icon: IconName }[] = [
  { to: "/admin/nachweise", label: "Nachweise", hint: "Lehrgänge, Übungen, Gültigkeit", icon: "badge" },
  { to: "/admin/funktionen", label: "Funktionen", hint: "Was jede Funktion braucht", icon: "list" },
  { to: "/admin/benutzer", label: "Benutzer", hint: "Zugänge und Rollen", icon: "key" },
  { to: "/admin/protokoll", label: "Protokoll", hint: "Wer hat was geändert", icon: "history" },
];

async function doLogout(): Promise<void> {
  await logout();
  await router.push("/login");
}
</script>

<template>
  <AppBar title="Mehr" no-back />

  <div class="section first">
    <RouterLink to="/konto" class="profile">
      <span class="me">{{ userInitials }}</span>
      <span class="cell-main">
        <strong>{{ user?.display_name }}</strong>
        <span class="cell-sub">{{ user?.role === "admin" ? "Admin" : "Anwender" }}, {{ user?.username }}</span>
      </span>
      <MIcon name="chevron" :size="18" />
    </RouterLink>

    <p class="group-label">Konto</p>
    <ul class="group">
      <li>
        <RouterLink to="/konto" class="cell">
          <span class="cell-icon"><MIcon name="shield" :size="18" /></span>
          <span class="cell-main">
            <strong>Passwort und Zwei-Faktor</strong>
            <span class="cell-sub">{{ user?.totp_enabled ? "Zwei-Faktor ist an" : "Zwei-Faktor ist aus" }}</span>
          </span>
          <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
        </RouterLink>
      </li>
    </ul>

    <template v-if="isAdmin">
      <p class="group-label">Verwaltung</p>
      <ul class="group">
        <li v-for="a in ADMIN" :key="a.to">
          <RouterLink :to="a.to" class="cell">
            <span class="cell-icon"><MIcon :name="a.icon" :size="18" /></span>
            <span class="cell-main">
              <strong>{{ a.label }}</strong>
              <span class="cell-sub">{{ a.hint }}</span>
            </span>
            <span class="cell-end"><MIcon name="chevron" :size="18" /></span>
          </RouterLink>
        </li>
      </ul>
    </template>

    <p class="group-label">Ansicht</p>
    <div class="layout">
      <LayoutSwitch />
      <p class="cell-sub">Die Desktop-Ansicht zeigt die volle Tabelle und den Export mit allen Filtern.</p>
    </div>

    <ul class="group logout">
      <li>
        <button type="button" class="cell danger-text" @click="doLogout">
          <span class="cell-icon off"><MIcon name="logout" :size="18" /></span>
          <span class="cell-main"><strong>Abmelden</strong></span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.first {
  margin-top: 0.5rem;
}
.profile {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.9rem 1rem;
  background: var(--surface);
  border-radius: var(--r-group);
  color: var(--ink);
  text-decoration: none;
}
.profile > .micon {
  color: var(--muted);
}
.profile strong {
  font-family: var(--font-cond);
  font-size: 1.35rem;
  font-weight: 600;
}
.me {
  display: grid;
  place-items: center;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  font-family: var(--font-cond);
  font-weight: 700;
  font-size: 1.25rem;
  flex-shrink: 0;
}
.layout {
  display: grid;
  gap: 0.5rem;
  padding: 0.85rem 1rem;
  background: var(--surface);
  border-radius: var(--r-group);
}
.layout .cell-sub {
  margin: 0;
}
.logout {
  margin-top: 1.5rem;
}
.cell-icon.off {
  background: var(--bad);
}
</style>
