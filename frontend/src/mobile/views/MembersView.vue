<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { api, errorText } from "../../api";
import DeleteMembersDialog from "../../components/DeleteMembersDialog.vue";
import MemberDialog from "../../components/MemberDialog.vue";
import { session } from "../../session";
import type { Member, Overview, Position } from "../../types";
import AppBar from "../components/AppBar.vue";
import MIcon from "../components/MIcon.vue";
import PullRefresh from "../components/PullRefresh.vue";
import { groupByLetter, initials, memberState, type MemberState } from "../readiness";
import { toast } from "../toast";

const router = useRouter();
const members = ref<Member[] | null>(null);
const states = ref<Map<number, MemberState>>(new Map());
const positions = ref<Position[]>([]);
const q = ref("");
const positionId = ref<number | null>(null);
const showInactive = ref(false);
const error = ref("");
const selecting = ref(false);
const selected = ref<Set<number>>(new Set());
const dialog = ref<InstanceType<typeof MemberDialog> | null>(null);
const deleteDialog = ref<InstanceType<typeof DeleteMembersDialog> | null>(null);
const isAdmin = computed(() => session.user?.role === "admin");

async function load(): Promise<void> {
  error.value = "";
  try {
    const [m, o] = await Promise.all([
      api<Member[]>("/api/members?include_inactive=true"),
      api<Overview>("/api/overview?include_inactive=true"),
    ]);
    members.value = m;
    states.value = new Map(o.rows.map((r) => [r.member.id, memberState(r)]));
  } catch (e) {
    error.value = errorText(e);
  }
}
onMounted(async () => {
  await load();
  positions.value = await api<Position[]>("/api/positions").catch(() => []);
});

const activeCount = computed(() => (members.value ?? []).filter((m) => m.is_active).length);
const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase();
  return (members.value ?? []).filter(
    (m) =>
      (showInactive.value || m.is_active) &&
      (positionId.value === null || m.positions.some((p) => p.id === positionId.value)) &&
      (!needle || `${m.number} ${m.last_name} ${m.first_name}`.toLowerCase().includes(needle)),
  );
});
const groups = computed(() => groupByLetter(filtered.value.map((m) => ({ member: m }))));

const STATE_LABEL: Record<MemberState, string> = {
  ready: "einsatzbereit",
  soon: "bald fällig",
  critical: "nicht einsatzbereit",
};

function jump(letter: string): void {
  document.getElementById(`letter-${letter}`)?.scrollIntoView({ block: "start" });
}

function toggle(id: number): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

function stopSelecting(): void {
  selecting.value = false;
  selected.value = new Set();
}

function onSaved(m: Member): void {
  toast(`${m.first_name} ${m.last_name} angelegt`);
  void router.push(`/kameraden/${m.id}`);
}

async function onDeleted(n: number): Promise<void> {
  toast(n === 1 ? "1 Kamerad gelöscht" : `${n} Kameraden gelöscht`);
  stopSelecting();
  await load();
}
</script>

<template>
  <PullRefresh :refresh="load" />
  <AppBar title="Kameraden" :subtitle="members ? `${activeCount} aktiv` : undefined">
    <template #actions>
      <template v-if="!selecting">
        <button v-if="isAdmin && members?.length" type="button" class="link select" @click="selecting = true">
          Auswählen
        </button>
        <button type="button" class="icon-btn" aria-label="Kamerad anlegen" @click="dialog?.open()">
          <MIcon name="plus" />
        </button>
      </template>
      <button v-else type="button" class="link select" @click="stopSelecting">Fertig</button>
    </template>
    <label class="search-field">
      <MIcon name="search" :size="18" />
      <input v-model="q" type="search" placeholder="Name oder Nr" aria-label="Kamerad suchen" />
    </label>
  </AppBar>

  <div class="chip-row" role="group" aria-label="Filter">
    <button type="button" class="chip" :aria-pressed="positionId === null" @click="positionId = null">Alle</button>
    <button
      v-for="p in positions"
      :key="p.id"
      type="button"
      class="chip"
      :aria-pressed="positionId === p.id"
      @click="positionId = positionId === p.id ? null : p.id"
    >
      {{ p.name }}
    </button>
    <button type="button" class="chip" :aria-pressed="showInactive" @click="showInactive = !showInactive">
      Inaktive
    </button>
  </div>

  <div class="section list-wrap">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="!members">
      <div v-for="i in 7" :key="i" class="skeleton"></div>
    </template>
    <div v-else-if="members.length === 0" class="empty">
      <strong>Noch keine Kameraden</strong>
      Lege den ersten an. Die Nummer wird automatisch vergeben.
      <button type="button" @click="dialog?.open()">Kamerad anlegen</button>
    </div>
    <p v-else-if="groups.length === 0" class="empty">
      <strong>Niemand gefunden</strong>
      {{ q ? `Niemand passt zu „${q}“.` : "Niemand passt zu diesem Filter." }}
    </p>

    <section v-for="g in groups" :id="`letter-${g.letter}`" :key="g.letter" class="letter">
      <h2 class="letter-head">{{ g.letter }}</h2>
      <ul class="group">
        <li v-for="{ member: m } in g.items" :key="m.id">
          <button
            v-if="selecting"
            type="button"
            class="cell"
            role="checkbox"
            :aria-checked="selected.has(m.id)"
            @click="toggle(m.id)"
          >
            <span class="tick" :class="{ on: selected.has(m.id) }"><MIcon name="check" :size="16" /></span>
            <span class="cell-main">
              <strong>{{ m.last_name }}, {{ m.first_name }}</strong>
              <span class="cell-sub">Nr {{ m.number }}</span>
            </span>
          </button>
          <RouterLink v-else :to="`/kameraden/${m.id}`" class="cell" :class="{ inactive: !m.is_active }">
            <span
              class="avatar"
              :class="m.is_active ? (states.get(m.id) ?? 'ready') : 'off'"
              :title="m.is_active ? STATE_LABEL[states.get(m.id) ?? 'ready'] : 'inaktiv'"
              >{{ initials(m) }}</span
            >
            <span class="cell-main">
              <strong>{{ m.last_name }}, {{ m.first_name }}</strong>
              <span class="cell-sub">
                <template v-if="!m.is_active">Inaktiv</template>
                <template v-else-if="m.positions.length">{{ m.positions.map((p) => p.name).join(", ") }}</template>
                <template v-else>Keine Funktion</template>
              </span>
              <span class="sr-only">{{ m.is_active ? STATE_LABEL[states.get(m.id) ?? "ready"] : "" }}</span>
            </span>
            <span class="cell-end nr">{{ m.number }}</span>
          </RouterLink>
        </li>
      </ul>
    </section>

    <nav v-if="groups.length > 6 && !q" class="index" aria-label="Zum Buchstaben springen">
      <button v-for="g in groups" :key="g.letter" type="button" @click="jump(g.letter)">{{ g.letter }}</button>
    </nav>
  </div>

  <div v-if="selecting" class="selectbar">
    <span
      ><strong>{{ selected.size }}</strong> ausgewählt</span
    >
    <button
      type="button"
      class="danger"
      :disabled="selected.size === 0"
      @click="deleteDialog?.open((members ?? []).filter((m) => selected.has(m.id)))"
    >
      Löschen
    </button>
  </div>

  <MemberDialog ref="dialog" :member="null" :positions="positions" @saved="onSaved" />
  <DeleteMembersDialog ref="deleteDialog" @deleted="onDeleted" />
</template>

<style scoped>
.select {
  font-weight: 600;
  padding: 0.5rem 0.6rem;
  min-height: 2.75rem;
}
.search-field {
  margin-top: 0.75rem;
}
.list-wrap {
  margin-top: 0.75rem;
  padding-right: 1.9rem;
  position: relative;
}
.letter {
  scroll-margin-top: calc(3.5rem + env(safe-area-inset-top));
}
.letter-head {
  position: sticky;
  top: calc(3.25rem + env(safe-area-inset-top));
  z-index: 2;
  margin: 0;
  padding: 0.6rem 0.25rem 0.3rem;
  font-size: 1.05rem;
  color: var(--muted);
  background: var(--paper);
}
.avatar {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-family: var(--font-cond);
  font-weight: 600;
  font-size: 0.95rem;
  flex-shrink: 0;
  background: var(--ok-soft);
  color: var(--ok-ink);
  box-shadow: inset 0 0 0 2.5px var(--ok);
}
.avatar.soon {
  background: var(--warn-soft);
  color: var(--warn-ink);
  box-shadow: inset 0 0 0 2.5px var(--warn);
}
.avatar.critical {
  background: var(--bad-soft);
  color: var(--bad-ink);
  box-shadow: inset 0 0 0 2.5px var(--bad);
}
.avatar.off {
  background: var(--none);
  color: var(--none-ink);
  box-shadow: none;
}
.inactive strong {
  color: var(--muted);
}
.nr {
  font-variant-numeric: tabular-nums;
  font-size: 0.9rem;
}
.index {
  position: fixed;
  right: 0.15rem;
  top: 50%;
  translate: 0 -45%;
  z-index: 15;
  display: grid;
}
.index button {
  min-height: 1.15rem;
  min-width: 1.6rem;
  padding: 0;
  border: none;
  background: none;
  color: var(--focus);
  font-size: 0.7rem;
  font-weight: 700;
}
.tick {
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  border: 2px solid var(--line);
  color: transparent;
  flex-shrink: 0;
}
.tick.on {
  background: var(--bad);
  border-color: var(--bad);
  color: #fff;
}
.selectbar {
  position: fixed;
  left: 0.75rem;
  right: 0.75rem;
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 0.6rem);
  z-index: 25;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.6rem 0.6rem 1.1rem;
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 8px 28px rgb(10 20 30 / 0.22);
}
.selectbar button {
  border-radius: 12px;
  min-width: 7rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
</style>
