<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { api, errorText } from "../api";
import MemberDialog from "../components/MemberDialog.vue";
import type { Member, Position } from "../types";

const router = useRouter();
const members = ref<Member[]>([]);
const positions = ref<Position[]>([]);
const search = ref("");
const includeInactive = ref(false);
const error = ref("");
const dialog = ref<InstanceType<typeof MemberDialog> | null>(null);

async function load(): Promise<void> {
  try {
    members.value = await api<Member[]>(`/api/members?include_inactive=${includeInactive.value}`);
  } catch (e) {
    error.value = errorText(e);
  }
}

onMounted(async () => {
  positions.value = await api<Position[]>("/api/positions");
});
watch(includeInactive, load, { immediate: true });

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return members.value;
  return members.value.filter((m) =>
    `${m.number} ${m.last_name} ${m.first_name}`.toLowerCase().includes(q),
  );
});

function onSaved(m: Member): void {
  void router.push(`/kameraden/${m.id}`);
}
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>Kameraden</h1>
      <button @click="dialog?.open()">Kamerad anlegen</button>
    </div>

    <div class="row controls">
      <input v-model="search" type="search" placeholder="Name oder Nr suchen" class="search" />
      <label class="check">
        <input v-model="includeInactive" type="checkbox" />
        Inaktive einblenden
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <ul v-if="filtered.length" class="list">
      <li v-for="m in filtered" :key="m.id">
        <RouterLink :to="`/kameraden/${m.id}`" class="list-item">
          <span class="nr muted">{{ m.number }}</span>
          <span class="name">
            <strong>{{ m.last_name }}, {{ m.first_name }}</strong>
            <span v-if="!m.is_active" class="tag">inaktiv</span>
          </span>
          <span class="positions">
            <span v-for="p in m.positions" :key="p.id" class="tag">{{ p.name }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
    <p v-else-if="members.length === 0" class="panel">
      Noch keine Kameraden erfasst. Lege den ersten mit „Kamerad anlegen“ an.
    </p>
    <p v-else class="panel">Niemand passt zu „{{ search }}“.</p>

    <MemberDialog ref="dialog" :member="null" :positions="positions" @saved="onSaved" />
  </div>
</template>

<style scoped>
.controls {
  margin-bottom: 1rem;
  gap: 0.75rem 1.5rem;
}
.search {
  max-width: 22rem;
}
.list-item {
  flex-wrap: wrap;
}
.nr {
  width: 3.5rem;
  font-variant-numeric: tabular-nums;
}
.name {
  flex: 1 1 12rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.positions {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}
</style>
