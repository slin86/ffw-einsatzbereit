<script setup lang="ts">
import { ref } from "vue";
import { RouterLink } from "vue-router";

import { api, errorText } from "../api";

const email = ref("");
const sent = ref(false);
const error = ref("");

async function submit(): Promise<void> {
  error.value = "";
  try {
    await api("/api/auth/password-reset/request", "POST", { email: email.value });
    sent.value = true;
  } catch (e) {
    error.value = errorText(e);
  }
}
</script>

<template>
  <div class="page page-narrow">
    <h1>Passwort vergessen</h1>
    <form v-if="!sent" class="form" @submit.prevent="submit">
      <p class="muted">Gib deine E-Mail ein. Du bekommst einen Link, mit dem du ein neues Passwort vergibst.</p>
      <label>E-Mail <input v-model="email" type="email" autocomplete="username" required /></label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">Link senden</button>
    </form>
    <p v-else class="notice">
      Falls die Adresse bei uns registriert ist, ist die Mail unterwegs. Der Link ist eine Stunde gültig.
    </p>
    <p><RouterLink to="/login">Zur Anmeldung</RouterLink></p>
  </div>
</template>
