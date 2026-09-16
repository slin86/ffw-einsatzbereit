<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, errorText } from "../../api";
import { session } from "../../session";
import type { Role, User } from "../../types";

const users = ref<User[]>([]);
const draft = ref({ email: "", display_name: "", role: "user" as Role, password: "" });
const dialog = ref<HTMLDialogElement | null>(null);
const error = ref("");
const listError = ref("");
const notice = ref("");

async function load(): Promise<void> {
  users.value = await api<User[]>("/api/users");
}
onMounted(load);

function open(): void {
  draft.value = { email: "", display_name: "", role: "user", password: "" };
  error.value = "";
  dialog.value?.showModal();
}

async function create(): Promise<void> {
  error.value = "";
  try {
    await api("/api/users", "POST", draft.value);
    dialog.value?.close();
    await load();
  } catch (e) {
    error.value = errorText(e);
  }
}

async function act(fn: () => Promise<unknown>, msg = ""): Promise<void> {
  listError.value = "";
  notice.value = "";
  try {
    await fn();
    notice.value = msg;
    await load();
  } catch (e) {
    listError.value = errorText(e);
  }
}

const setRole = (u: User, role: Role) => act(() => api(`/api/users/${u.id}`, "PATCH", { role }));
const setActive = (u: User, is_active: boolean) =>
  act(() => api(`/api/users/${u.id}`, "PATCH", { is_active }));
const reset2fa = (u: User) =>
  confirm(`Zwei-Faktor für ${u.display_name} zurücksetzen?`) &&
  act(() => api(`/api/users/${u.id}/reset-2fa`, "POST"), "Zwei-Faktor zurückgesetzt.");
const sendReset = (u: User) =>
  act(() => api(`/api/users/${u.id}/send-password-reset`, "POST"), `Link an ${u.email} gesendet.`);
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>Benutzer</h1>
      <button @click="open()">Benutzer anlegen</button>
    </div>
    <p class="lede">
      Benutzer melden sich an und pflegen Kameraden und Abschlüsse. Admins verwalten zusätzlich
      Nachweise, Funktionen und Benutzer. Kameraden selbst brauchen kein Konto.
    </p>
    <p v-if="listError" class="error">{{ listError }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Rolle</th>
            <th>Zwei-Faktor</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>
              <strong>{{ u.display_name }}</strong>
              <div class="small muted">{{ u.email }}</div>
            </td>
            <td>
              <select
                :value="u.role"
                :aria-label="`Rolle von ${u.display_name}`"
                @change="setRole(u, ($event.target as HTMLSelectElement).value as Role)"
              >
                <option value="user">Anwender</option>
                <option value="admin">Admin</option>
              </select>
            </td>
            <td>{{ u.totp_enabled ? "aktiv" : "aus" }}</td>
            <td>{{ u.is_active ? "aktiv" : "gesperrt" }}</td>
            <td class="actions">
              <button class="link" @click="sendReset(u)">Passwort-Link senden</button>
              <button v-if="u.totp_enabled" class="link" @click="reset2fa(u)">2FA zurücksetzen</button>
              <button v-if="u.id !== session.user?.id" class="link" @click="setActive(u, !u.is_active)">
                {{ u.is_active ? "Sperren" : "Entsperren" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <dialog ref="dialog">
      <form class="dialog-body form" @submit.prevent="create">
        <h2>Benutzer anlegen</h2>
        <label>Name <input v-model="draft.display_name" required maxlength="120" /></label>
        <label>E-Mail <input v-model="draft.email" type="email" required autocomplete="off" /></label>
        <label>
          Rolle
          <select v-model="draft.role">
            <option value="user">Anwender</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label>
          Startpasswort (mind. 10 Zeichen)
          <input v-model="draft.password" type="password" minlength="10" required autocomplete="new-password" />
        </label>
        <p class="small muted">Gib das Startpasswort persönlich weiter oder sende danach einen Passwort-Link.</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="row">
          <button type="submit">Anlegen</button>
          <button type="button" class="secondary" @click="dialog?.close()">Abbrechen</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.actions {
  text-align: right;
}
.actions button {
  white-space: nowrap;
}
select {
  min-width: 8rem;
}
</style>
