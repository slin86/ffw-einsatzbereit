<script setup lang="ts">
import QRCode from "qrcode";
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { api, errorText } from "../api";
import { logout, session } from "../session";
import type { User } from "../types";

const router = useRouter();

const pw = ref({ current_password: "", new_password: "" });
const pwMsg = ref("");
const pwError = ref("");

const setup = ref<{ secret: string; qr: string } | null>(null);
const code = ref("");
const disablePassword = ref("");
const totpError = ref("");

async function changePassword(): Promise<void> {
  pwMsg.value = "";
  pwError.value = "";
  try {
    await api("/api/me/password", "POST", pw.value);
    // All sessions were revoked, including this one.
    await logout();
    await router.push({ path: "/login" });
  } catch (e) {
    pwError.value = errorText(e);
  }
}

async function startSetup(): Promise<void> {
  totpError.value = "";
  try {
    const res = await api<{ secret: string; otpauth_uri: string }>("/api/me/totp/setup", "POST");
    setup.value = { secret: res.secret, qr: await QRCode.toDataURL(res.otpauth_uri, { margin: 1, width: 220 }) };
  } catch (e) {
    totpError.value = errorText(e);
  }
}

async function enable(): Promise<void> {
  totpError.value = "";
  try {
    session.user = await api<User>("/api/me/totp/enable", "POST", { code: code.value });
    setup.value = null;
    code.value = "";
  } catch (e) {
    totpError.value = errorText(e);
  }
}

async function disable(): Promise<void> {
  totpError.value = "";
  try {
    session.user = await api<User>("/api/me/totp/disable", "POST", {
      password: disablePassword.value,
      code: code.value,
    });
    code.value = "";
    disablePassword.value = "";
  } catch (e) {
    totpError.value = errorText(e);
  }
}

async function doLogout(): Promise<void> {
  await logout();
  await router.push("/login");
}
</script>

<template>
  <div class="page page-narrow">
    <h1>Mein Konto</h1>
    <p class="muted">
      {{ session.user?.display_name }} · {{ session.user?.email }} ·
      {{ session.user?.role === "admin" ? "Admin" : "Anwender" }}
    </p>

    <nav v-if="session.user?.role === 'admin'" class="admin-links" aria-label="Verwaltung">
      <h2>Verwaltung</h2>
      <ul class="list">
        <li><RouterLink to="/admin/nachweise" class="list-item">Nachweise</RouterLink></li>
        <li><RouterLink to="/admin/funktionen" class="list-item">Funktionen</RouterLink></li>
        <li><RouterLink to="/admin/benutzer" class="list-item">Benutzer</RouterLink></li>
        <li><RouterLink to="/admin/protokoll" class="list-item">Protokoll</RouterLink></li>
      </ul>
    </nav>

    <section>
      <h2>Zwei-Faktor-Anmeldung</h2>
      <template v-if="session.user?.totp_enabled">
        <p class="notice">Aktiv. Bei der Anmeldung wird ein Code aus deiner Authenticator-App abgefragt.</p>
        <form class="form" @submit.prevent="disable">
          <label>Passwort <input v-model="disablePassword" type="password" autocomplete="current-password" required /></label>
          <label>Aktueller Code <input v-model="code" inputmode="numeric" autocomplete="one-time-code" required /></label>
          <p v-if="totpError" class="error">{{ totpError }}</p>
          <button type="submit" class="danger">Zwei-Faktor ausschalten</button>
        </form>
      </template>
      <template v-else-if="setup">
        <p>Scanne den Code mit einer Authenticator-App (z. B. Aegis, 2FAS, Google Authenticator) und gib den angezeigten Code ein.</p>
        <img :src="setup.qr" alt="QR-Code für die Authenticator-App" width="220" height="220" class="qr" />
        <p class="small muted">Manuelle Eingabe: <code>{{ setup.secret }}</code></p>
        <form class="form" @submit.prevent="enable">
          <label>Code <input v-model="code" inputmode="numeric" autocomplete="one-time-code" required /></label>
          <p v-if="totpError" class="error">{{ totpError }}</p>
          <button type="submit">Zwei-Faktor einschalten</button>
        </form>
      </template>
      <template v-else>
        <p class="muted">Optional. Schützt dein Konto zusätzlich mit einem Code vom Handy.</p>
        <p v-if="totpError" class="error">{{ totpError }}</p>
        <button @click="startSetup">Zwei-Faktor einrichten</button>
      </template>
    </section>

    <section>
      <h2>Passwort ändern</h2>
      <form class="form" @submit.prevent="changePassword">
        <label>Aktuelles Passwort <input v-model="pw.current_password" type="password" autocomplete="current-password" required /></label>
        <label>
          Neues Passwort (mind. 10 Zeichen)
          <input v-model="pw.new_password" type="password" autocomplete="new-password" minlength="10" required />
        </label>
        <p class="small muted">Danach wirst du auf allen Geräten abgemeldet.</p>
        <p v-if="pwError" class="error">{{ pwError }}</p>
        <p v-if="pwMsg" class="notice">{{ pwMsg }}</p>
        <button type="submit">Passwort ändern</button>
      </form>
    </section>

    <section>
      <button class="secondary" @click="doLogout">Abmelden</button>
    </section>
  </div>
</template>

<style scoped>
section,
.admin-links {
  margin-top: 2rem;
}
.qr {
  background: #fff;
  border-radius: var(--radius);
  padding: 0.5rem;
}
code {
  word-break: break-all;
}
</style>
