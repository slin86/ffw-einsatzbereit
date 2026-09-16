<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { errorText } from "../api";
import { safeNext } from "../guard";
import { login, loginMfa } from "../session";

const route = useRoute();
const router = useRouter();
const email = ref("");
const password = ref("");
const code = ref("");
const mfaToken = ref<string | null>(null);
const error = ref("");
const busy = ref(false);

async function submit(): Promise<void> {
  busy.value = true;
  error.value = "";
  try {
    if (mfaToken.value) {
      await loginMfa(mfaToken.value, code.value);
    } else {
      mfaToken.value = await login(email.value, password.value);
      if (mfaToken.value) return;
    }
    await router.replace(safeNext(route.query.next));
  } catch (e) {
    error.value = errorText(e);
    if (mfaToken.value) code.value = "";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login">
    <div class="board" aria-hidden="true">
      <span v-for="i in 24" :key="i" :class="`p${(i * 7) % 11}`"></span>
    </div>
    <form class="panel form" @submit.prevent="submit">
      <h1>Einsatzbereit</h1>
      <p class="muted">Nachweise der Kameraden im Blick.</p>

      <template v-if="!mfaToken">
        <label>E-Mail <input v-model="email" type="email" autocomplete="username" required /></label>
        <label>
          Passwort
          <input v-model="password" type="password" autocomplete="current-password" required />
        </label>
      </template>
      <label v-else>
        Code aus der Authenticator-App
        <input
          v-model="code"
          inputmode="numeric"
          autocomplete="one-time-code"
          pattern="[0-9]{6,8}"
          required
          autofocus
        />
      </label>

      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="busy">{{ mfaToken ? "Bestätigen" : "Anmelden" }}</button>
      <button v-if="mfaToken" type="button" class="link" @click="mfaToken = null">Zurück</button>
      <RouterLink v-else to="/passwort-vergessen" class="small">Passwort vergessen?</RouterLink>
    </form>
  </div>
</template>

<style scoped>
.login {
  min-height: 100dvh;
  display: grid;
  place-content: center;
  gap: 1.5rem;
  padding: 1.5rem;
  background: var(--brand);
}
.panel {
  width: min(24rem, calc(100vw - 3rem));
  padding: 1.5rem;
}
.panel h1 {
  margin: 0;
}
.panel p {
  margin: 0;
}
.board {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 5px;
  width: min(24rem, calc(100vw - 3rem));
}
.board span {
  height: 14px;
  border-radius: 3px;
  background: var(--ok);
  opacity: 0.9;
}
.board .p3 {
  background: var(--warn);
}
.board .p8 {
  background: var(--bad);
}
.board .p5 {
  background: rgb(255 255 255 / 0.15);
}
</style>
