<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { api, errorText } from "../api";

const route = useRoute();
const token = computed(() => (typeof route.query.token === "string" ? route.query.token : ""));
const password = ref("");
const repeat = ref("");
const done = ref(false);
const error = ref("");

async function submit(): Promise<void> {
  error.value = "";
  if (password.value !== repeat.value) {
    error.value = "Die Passwörter stimmen nicht überein.";
    return;
  }
  try {
    await api("/api/auth/password-reset/confirm", "POST", { token: token.value, new_password: password.value });
    done.value = true;
  } catch (e) {
    error.value = errorText(e);
  }
}
</script>

<template>
  <div class="page page-narrow">
    <h1>Neues Passwort</h1>
    <p v-if="!token" class="error">Der Link ist unvollständig. Fordere einen neuen an.</p>
    <form v-else-if="!done" class="form" @submit.prevent="submit">
      <label>
        Neues Passwort (mind. 10 Zeichen)
        <input v-model="password" type="password" autocomplete="new-password" minlength="10" required />
      </label>
      <label>
        Wiederholen
        <input v-model="repeat" type="password" autocomplete="new-password" minlength="10" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">Passwort speichern</button>
    </form>
    <p v-else class="notice">Passwort gespeichert. Du kannst dich jetzt anmelden.</p>
    <p><RouterLink to="/login">Zur Anmeldung</RouterLink></p>
  </div>
</template>
